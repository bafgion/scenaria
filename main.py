from __future__ import annotations

import sys

from app.qt.app import run_qt_app


def main() -> None:
    if len(sys.argv) > 1:
        from app.cli import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))
    run_qt_app()


if __name__ == "__main__":
    main()
