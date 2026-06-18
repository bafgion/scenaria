"""Catalog tree model (features root, folders, .feature files)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Signal

from app.feature_store import MAX_FEATURES_IN_TREE, get_root, set_root
from app.gherkin_ru import GherkinParseError
from app.run_status_store import domain_from_url, get_run_status


RowKind = Literal["root", "dir", "file"]
EmptyKind = Literal["no_project", "missing", "no_files", "no_match"]


@dataclass
class CatalogNode:
    kind: RowKind
    path: Path
    name: str
    children: list[CatalogNode] = field(default_factory=list)
    step_count: int = 0
    domain: str = ""
    run_success: bool | None = None
    run_at: str = ""
    parse_error: str | None = None

    @property
    def key(self) -> str:
        return str(self.path)


@dataclass(frozen=True)
class FeatureFileMeta:
    step_count: int
    domain: str
    parse_error: str | None = None


_metadata_cache: dict[str, tuple[float, FeatureFileMeta]] = {}


def clear_feature_metadata_cache() -> None:
    _metadata_cache.clear()


def _file_metadata(path: Path) -> FeatureFileMeta:
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        return FeatureFileMeta(0, "", f"не удалось прочитать файл: {exc}")

    key = str(path.resolve())
    cached = _metadata_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        from app.feature_store import load_feature

        loaded = load_feature(path)
    except GherkinParseError as exc:
        meta = FeatureFileMeta(0, "", str(exc))
    except (OSError, ValueError) as exc:
        meta = FeatureFileMeta(0, "", str(exc))
    else:
        steps = loaded.get("steps", []) or []
        start_url = str(loaded.get("startUrl", "") or "")
        if not start_url and steps and steps[0].get("action") == "goto":
            start_url = str(steps[0].get("url", "") or "")
        meta = FeatureFileMeta(len(steps), domain_from_url(start_url), None)

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


def _filter_tree(node: CatalogNode, query: str) -> CatalogNode | None:
    q = query.strip().lower()
    if not q:
        return node

    if node.kind == "file":
        rel = str(node.path).replace("\\", "/").lower()
        if q in node.name.lower() or q in rel:
            return node
        return None

    children: list[CatalogNode] = []
    for child in node.children:
        filtered = _filter_tree(child, q)
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
    query = filter_text.strip()
    tree = _filter_tree(full_tree, query) if query else full_tree
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

    if query and visible_files == 0:
        return CatalogViewState(
            tree=tree,
            empty_title="Ничего не найдено",
            empty_hint=f"Запрос «{query}» не дал результатов.\nОчистите поле поиска.",
            empty_kind="no_match",
            expand_all=True,
        )

    return CatalogViewState(tree=tree, expand_all=bool(query))


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
        parent.children.append(
            CatalogNode(
                "file",
                path,
                path.stem,
                step_count=meta.step_count,
                domain=meta.domain,
                run_success=None if run is None else run.success,
                run_at="" if run is None else run.at,
                parse_error=meta.parse_error,
            )
        )

    return root_node


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
