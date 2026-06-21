"""Catalog tree model (features root, folders, .feature files)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Signal

from app.feature_store import MAX_FEATURES_IN_TREE, get_root, set_root
from app.gherkin_ru import GherkinParseError
from app.run_status_store import domain_from_url, get_run_history, get_run_status


RowKind = Literal["root", "dir", "file"]
EmptyKind = Literal["no_project", "missing", "no_files", "no_match"]


@dataclass
class CatalogNode:
    kind: RowKind
    path: Path
    name: str
    children: list[CatalogNode] = field(default_factory=list)
    step_count: int = 0
    example_count: int = 0
    params_count: int = 0
    domain: str = ""
    run_success: bool | None = None
    run_at: str = ""
    run_duration_ms: int = 0
    run_failed_step: int | None = None
    run_message: str = ""
    run_runner: str = ""
    parse_error: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return str(self.path)


@dataclass(frozen=True)
class FeatureFileMeta:
    step_count: int
    domain: str
    tags: tuple[str, ...] = ()
    parse_error: str | None = None
    example_count: int = 0
    params_count: int = 0


_metadata_cache: dict[str, tuple[float, FeatureFileMeta]] = {}


def clear_feature_metadata_cache() -> None:
    _metadata_cache.clear()


def _file_metadata(path: Path) -> FeatureFileMeta:
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        return FeatureFileMeta(0, "", (), f"не удалось прочитать файл: {exc}")

    key = str(path.resolve())
    cached = _metadata_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        from app.feature_store import load_feature
        from app.gherkin_outline import outline_example_count
        from app.scenario_params import param_case_count

        loaded = load_feature(path)
        example_count = 0
        params_count = 0
        try:
            example_count = outline_example_count(path.read_text(encoding="utf-8"))
        except OSError:
            example_count = 0
        try:
            params_count = param_case_count(path)
        except OSError:
            params_count = 0
    except GherkinParseError as exc:
        meta = FeatureFileMeta(0, "", (), str(exc))
    except (OSError, ValueError) as exc:
        meta = FeatureFileMeta(0, "", (), str(exc))
    else:
        steps = loaded.get("steps", []) or []
        start_url = str(loaded.get("startUrl", "") or "")
        if not start_url and steps and steps[0].get("action") == "goto":
            start_url = str(steps[0].get("url", "") or "")
        meta = FeatureFileMeta(
            len(steps),
            domain_from_url(start_url),
            tuple(str(tag).strip() for tag in (loaded.get("tags", []) or []) if str(tag).strip()),
            None,
            example_count,
            params_count,
        )

    _metadata_cache[key] = (mtime, meta)
    return meta


@dataclass(frozen=True)
class CatalogViewState:
    """Tree data plus an optional empty-state explanation for the sidebar."""

    tree: CatalogNode | None = None
    empty_title: str | None = None
    empty_hint: str | None = None
    empty_kind: EmptyKind | None = None
    expand_all: bool = False

    @property
    def show_empty_message(self) -> bool:
        return bool(self.empty_title)


def count_feature_files(node: CatalogNode | None) -> int:
    if node is None:
        return 0
    count = 1 if node.kind == "file" else 0
    return count + sum(count_feature_files(child) for child in node.children)


def parse_catalog_filter(filter_text: str) -> tuple[str, str]:
    """Split sidebar filter into text query and optional tag (without @)."""
    raw = (filter_text or "").strip()
    if raw.startswith("@"):
        tag = raw[1:].strip().split()[0].lower()
        return "", tag
    lowered = raw.lower()
    if lowered.startswith("tag:"):
        return "", raw.split(":", 1)[1].strip().lower()
    return raw.lower(), ""


def _file_matches_filter(node: CatalogNode, query: str, tag: str) -> bool:
    if tag:
        file_tags = {item.lower() for item in node.tags}
        if tag not in file_tags:
            return False
    if not query:
        return True
    rel = str(node.path).replace("\\", "/").lower()
    return query in node.name.lower() or query in rel


def _filter_tree(node: CatalogNode, query: str, tag: str = "") -> CatalogNode | None:
    if not query and not tag:
        return node

    if node.kind == "file":
        if _file_matches_filter(node, query, tag):
            return node
        return None

    children: list[CatalogNode] = []
    for child in node.children:
        filtered = _filter_tree(child, query, tag)
        if filtered is not None:
            children.append(filtered)

    if node.kind == "root":
        return CatalogNode(
            node.kind,
            node.path,
            node.name,
            children=children,
            step_count=node.step_count,
            domain=node.domain,
            run_success=node.run_success,
            run_at=node.run_at,
            parse_error=node.parse_error,
            tags=node.tags,
        )

    if not children:
        return None

    return CatalogNode(
        node.kind,
        node.path,
        node.name,
        children=children,
        step_count=node.step_count,
        domain=node.domain,
        run_success=node.run_success,
        run_at=node.run_at,
        parse_error=node.parse_error,
        tags=node.tags,
    )


def build_catalog_view_state(root: Path | None, filter_text: str) -> CatalogViewState:
    if root is None:
        return CatalogViewState(
            tree=None,
            empty_title="Проект не открыт",
            empty_hint="Откройте папку с .feature сценариями.\nФайл → Открыть проект…",
            empty_kind="no_project",
        )
    if not root.exists():
        return CatalogViewState(
            tree=None,
            empty_title="Папка не найдена",
            empty_hint=f"Путь недоступен:\n{root}\n\nВыберите другой проект.",
            empty_kind="missing",
        )

    full_tree = build_catalog_tree(root)
    total_files = count_feature_files(full_tree)
    query, tag = parse_catalog_filter(filter_text)
    tree = _filter_tree(full_tree, query, tag) if (query or tag) else full_tree
    visible_files = count_feature_files(tree)

    if total_files == 0:
        return CatalogViewState(
            tree=tree,
            empty_title="Нет сценариев",
            empty_hint=(
                f"В «{root.name}» пока нет .feature файлов.\n"
                "Нажмите + или Файл → Новый сценарий."
            ),
            empty_kind="no_files",
        )

    if (query or tag) and visible_files == 0:
        if tag and not query:
            hint = f"Тег «@{tag}» не найден ни в одном сценарии.\nОчистите поле поиска."
            title = "Нет сценариев с тегом"
        else:
            hint = f"Запрос «{filter_text.strip()}» не дал результатов.\nОчистите поле поиска."
            title = "Ничего не найдено"
        return CatalogViewState(
            tree=tree,
            empty_title=title,
            empty_hint=hint,
            empty_kind="no_match",
            expand_all=True,
        )

    return CatalogViewState(tree=tree, expand_all=bool(query or tag))


def build_catalog_tree(root: Path) -> CatalogNode:
    root_node = CatalogNode("root", root, root.name)
    dir_map: dict[str, CatalogNode] = {"": root_node}

    try:
        feature_paths = sorted(root.rglob("*.feature"), key=lambda p: str(p).lower())
    except OSError:
        feature_paths = []

    for index, path in enumerate(feature_paths):
        if index >= MAX_FEATURES_IN_TREE:
            break

        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        parent = root_node
        prefix_parts: list[str] = []
        for part in rel.parts[:-1]:
            prefix_parts.append(part)
            key = "/".join(prefix_parts)
            if key not in dir_map:
                dir_node = CatalogNode("dir", root / Path(*prefix_parts), part)
                dir_map[key] = dir_node
                parent.children.append(dir_node)
            parent = dir_map[key]

        meta = _file_metadata(path)
        run = get_run_status(path)
        history = get_run_history(path)
        last = history[0] if history else None
        parent.children.append(
            CatalogNode(
                "file",
                path,
                path.stem,
                step_count=meta.step_count,
                example_count=meta.example_count,
                params_count=meta.params_count,
                domain=meta.domain,
                run_success=None if run is None else run.success,
                run_at="" if run is None else run.at,
                run_duration_ms=0 if last is None else last.duration_ms,
                run_failed_step=None if last is None else last.failed_step,
                run_message="" if run is None else run.message,
                run_runner="" if last is None else last.runner,
                parse_error=meta.parse_error,
                tags=meta.tags,
            )
        )

    return root_node


def feature_has_tag(path: Path, tag: str) -> bool:
    """True if *path* contains *tag* (with or without leading @)."""
    normalized = tag.strip().lstrip("@").lower()
    if not normalized:
        return True
    meta = _file_metadata(path)
    return normalized in {item.lower() for item in meta.tags}


def collect_feature_paths_with_tag(root: Path, tag: str) -> list[Path]:
    """All `.feature` files in *root* that contain *tag* (without @)."""
    normalized = tag.strip().lstrip("@").lower()
    if not normalized or not root.is_dir():
        return []
    result: list[Path] = []
    try:
        paths = sorted(root.rglob("*.feature"), key=lambda p: str(p).lower())
    except OSError:
        return []
    for index, path in enumerate(paths):
        if index >= MAX_FEATURES_IN_TREE:
            break
        meta = _file_metadata(path)
        if normalized in {item.lower() for item in meta.tags}:
            result.append(path.resolve())
    return result


def collect_project_tags(root: Path | None) -> list[str]:
    if root is None or not root.is_dir():
        return []
    tags: set[str] = set()
    try:
        paths = root.rglob("*.feature")
    except OSError:
        return []
    for index, path in enumerate(paths):
        if index >= MAX_FEATURES_IN_TREE:
            break
        tags.update(_file_metadata(path).tags)
    return sorted(tags, key=str.lower)


def collect_feature_paths_under(path: Path) -> list[Path]:
    """All `.feature` files under a directory (or the file itself)."""
    resolved = path.resolve()
    if resolved.is_file() and resolved.suffix.lower() == ".feature":
        return [resolved]
    if not resolved.is_dir():
        return []
    try:
        return sorted(resolved.rglob("*.feature"), key=lambda p: str(p).lower())
    except OSError:
        return []


class CatalogModel(QObject):
    """State for the features catalog sidebar."""

    root_changed = Signal(object)  # Path | None
    filter_changed = Signal(str)
    tree_changed = Signal(object)  # CatalogViewState
    feature_selected = Signal(object)  # Path
    directory_selected = Signal(object)  # Path
    run_status_changed = Signal()
    run_selection_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._features_root: Path | None = get_root()
        self._filter = ""
        self._selected_feature: Path | None = None
        self._selected_directory: Path | None = None
        self._collapsed: set[str] = set()
        self._run_selection: set[str] = set()

    @property
    def features_root(self) -> Path | None:
        return self._features_root

    @property
    def filter_text(self) -> str:
        return self._filter

    @property
    def selected_feature(self) -> Path | None:
        return self._selected_feature

    @property
    def selected_directory(self) -> Path | None:
        return self._selected_directory

    @property
    def collapsed_keys(self) -> set[str]:
        return set(self._collapsed)

    @property
    def run_selection_count(self) -> int:
        return len(self._run_selection)

    @property
    def run_selection_keys(self) -> frozenset[str]:
        return frozenset(self._run_selection)

    @property
    def run_selection_paths(self) -> list[Path]:
        return [Path(key) for key in sorted(self._run_selection)]

    def is_in_run_selection(self, path: Path) -> bool:
        return str(path.resolve()) in self._run_selection

    def toggle_run_selection(self, path: Path) -> None:
        key = str(path.resolve())
        if key in self._run_selection:
            self._run_selection.discard(key)
        else:
            self._run_selection.add(key)
        self.run_selection_changed.emit()

    def add_paths_to_run_selection(self, paths: list[Path]) -> None:
        added = False
        for path in paths:
            key = str(path.resolve())
            if key not in self._run_selection:
                self._run_selection.add(key)
                added = True
        if added:
            self.run_selection_changed.emit()

    def remove_paths_from_run_selection(self, paths: list[Path]) -> None:
        removed = False
        for path in paths:
            key = str(path.resolve())
            if key in self._run_selection:
                self._run_selection.discard(key)
                removed = True
        if removed:
            self.run_selection_changed.emit()

    def add_folder_to_run_selection(self, folder: Path) -> None:
        self.add_paths_to_run_selection(collect_feature_paths_under(folder))

    def clear_run_selection(self) -> None:
        if not self._run_selection:
            return
        self._run_selection.clear()
        self.run_selection_changed.emit()

    def set_features_root(self, path: Path | None) -> None:
        resolved = path.resolve() if path else None
        if resolved == self._features_root:
            self.refresh_tree()
            return
        if resolved is not None:
            set_root(resolved)
        clear_feature_metadata_cache()
        self._features_root = resolved
        self._selected_feature = None
        self._selected_directory = resolved
        self._collapsed.clear()
        self._run_selection.clear()
        self.root_changed.emit(resolved)
        self.run_selection_changed.emit()
        self.refresh_tree()

    def set_filter(self, text: str) -> None:
        text = text or ""
        if text == self._filter:
            return
        self._filter = text
        self.filter_changed.emit(text)
        self.refresh_tree()

    def set_collapsed(self, key: str, collapsed: bool) -> None:
        if collapsed:
            self._collapsed.add(key)
        else:
            self._collapsed.discard(key)

    def select_feature(self, path: Path) -> None:
        self._selected_feature = path.resolve()
        self._selected_directory = path.parent.resolve()
        self.feature_selected.emit(self._selected_feature)

    def select_directory(self, path: Path) -> None:
        self._selected_feature = None
        self._selected_directory = path.resolve()
        self.directory_selected.emit(self._selected_directory)

    def refresh_tree(self) -> None:
        state = build_catalog_view_state(self._features_root, self._filter)
        self.tree_changed.emit(state)

    def refresh_run_statuses(self) -> None:
        self.refresh_tree()
        self.run_status_changed.emit()

    def target_directory_for_new_file(self) -> Path | None:
        if self._selected_feature is not None:
            return self._selected_feature.parent
        if self._selected_directory is not None:
            return self._selected_directory
        return self._features_root
