"""Subprocess runner for 1C + Vanessa."""

from __future__ import annotations

import locale
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scenaria_vanessa.exit_codes import describe_exit_code
from scenaria_vanessa.platform_command import PlatformLaunchSpec

LogCallback = Callable[[str], None]
StopCallback = Callable[[], bool]


@dataclass
class ProcessRunResult:
    exit_code: int
    duration_ms: int
    log_path: Path
    stdout: str
    stderr: str
    stopped: bool = False
    timed_out: bool = False

    @property
    def exit_info(self):
        return describe_exit_code(self.exit_code)


def resolve_log_encoding(setting: str) -> str:
    value = (setting or "auto").strip().lower()
    if value in {"", "auto"}:
        preferred = locale.getpreferredencoding(False) or "utf-8"
        return preferred
    return value


class VanessaProcessRunner:
    def __init__(self, *, log_encoding: str = "auto") -> None:
        self._encoding = resolve_log_encoding(log_encoding)

    def run(
        self,
        spec: PlatformLaunchSpec,
        *,
        run_dir: Path,
        on_log: LogCallback | None = None,
        should_stop: StopCallback | None = None,
        timeout_sec: int | None = None,
        dry_run: bool = False,
    ) -> ProcessRunResult:
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / "process.log"
        argv = spec.build_argv()
        command_line = spec.format_command_line()
        if on_log:
            on_log(f"Команда: {command_line}")
        if dry_run:
            log_path.write_text(command_line + "\n", encoding="utf-8")
            return ProcessRunResult(
                exit_code=0,
                duration_ms=0,
                log_path=log_path,
                stdout="",
                stderr="",
            )

        started = time.perf_counter()
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(run_dir),
            text=True,
            encoding=self._encoding,
            errors="replace",
        )
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        stopped = False
        timed_out = False

        def _reader(stream, bucket: list[str], prefix: str) -> None:
            if stream is None:
                return
            for line in stream:
                bucket.append(line)
                if on_log:
                    on_log(f"{prefix}{line.rstrip()}")

        threads = [
            threading.Thread(target=_reader, args=(proc.stdout, stdout_lines, ""), daemon=True),
            threading.Thread(target=_reader, args=(proc.stderr, stderr_lines, "[stderr] "), daemon=True),
        ]
        for thread in threads:
            thread.start()

        deadline = time.perf_counter() + timeout_sec if timeout_sec and timeout_sec > 0 else None
        while proc.poll() is None:
            if should_stop and should_stop():
                stopped = True
                proc.terminate()
                break
            if deadline is not None and time.perf_counter() >= deadline:
                timed_out = True
                proc.kill()
                break
            time.sleep(0.2)

        for thread in threads:
            thread.join(timeout=2)
        try:
            remaining_out, remaining_err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            remaining_out, remaining_err = proc.communicate()
        if remaining_out:
            stdout_lines.append(remaining_out)
        if remaining_err:
            stderr_lines.append(remaining_err)

        exit_code = int(proc.returncode or 0)
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        log_path.write_text(
            "\n".join(
                [
                    command_line,
                    "",
                    stdout,
                    "",
                    "[stderr]",
                    stderr,
                    "",
                    f"exit_code={exit_code}",
                ]
            ),
            encoding="utf-8",
        )
        if timed_out and on_log:
            on_log(f"Процесс остановлен по таймауту ({timeout_sec} с)")
        if stopped and on_log:
            on_log("Процесс остановлен пользователем")
        info = describe_exit_code(exit_code)
        if on_log:
            on_log(f"Код возврата {exit_code}: {info.label}")
        return ProcessRunResult(
            exit_code=exit_code,
            duration_ms=duration_ms,
            log_path=log_path,
            stdout=stdout,
            stderr=stderr,
            stopped=stopped,
            timed_out=timed_out,
        )
