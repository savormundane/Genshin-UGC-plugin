from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from engine.resources.definition_schema_view import read_code_definition
from ugc_file_tools.repo_paths import repo_root


def _default_project_archive_root() -> Path:
    return repo_root() / "assets" / "资源库" / "项目存档"


def resolve_project_archive_path(
    *,
    project_archive: str | None,
    project_id: str | None,
    project_root: str | None,
) -> Path:
    if str(project_archive or "").strip():
        path = Path(str(project_archive)).resolve()
        if not path.is_dir():
            raise FileNotFoundError(str(path))
        return path

    project_id_text = str(project_id or "").strip()
    if project_id_text == "":
        raise ValueError("需要提供 --project-archive 或 --project-id")

    root = Path(str(project_root)).resolve() if str(project_root or "").strip() else _default_project_archive_root()
    path = (root / project_id_text).resolve()
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    return path


def _iter_struct_decoded_files(project_archive_path: Path) -> List[Path]:
    directory = project_archive_path / "管理配置" / "结构体定义" / "原始解析"
    if not directory.is_dir():
        return []
    return sorted(directory.glob("struct_def_*_*.decoded.json"))


def iter_struct_decoded_files(project_archive_path: Path) -> List[Path]:
    """
    Public API (no leading underscores).

    Import policy: cross-module imports must not import underscored private names.
    """
    return _iter_struct_decoded_files(project_archive_path)


def _iter_basic_struct_py_files(project_archive_path: Path) -> List[Path]:
    directory = project_archive_path / "管理配置" / "结构体定义" / "基础结构体"
    if not directory.is_dir():
        return []
    files = sorted(
        [
            p
            for p in directory.rglob("*.py")
            if p.is_file()
            and p.suffix.lower() == ".py"
            and p.name != "__init__.py"
            and (not p.name.startswith("_"))
            and p.parent.name != "__pycache__"
        ],
        key=lambda p: p.as_posix().casefold(),
    )
    return files


def collect_basic_struct_definitions(project_archive_path: Path) -> Dict[str, Tuple[Path, Dict[str, Any]]]:
    """对齐 Graph_Generater 的代码级 Schema 作用域：
    - 共享根 + 当前项目存档根
    - 若共享与项目出现同 STRUCT_ID，则以项目定义覆盖共享定义
    """
    project_files = _iter_basic_struct_py_files(Path(project_archive_path))

    shared_root = repo_root() / "assets" / "资源库" / "共享" / "管理配置" / "结构体定义" / "基础结构体"
    shared_files: List[Path] = []
    if shared_root.is_dir():
        shared_files = sorted(
            [
                p
                for p in shared_root.rglob("*.py")
                if p.is_file()
                and p.suffix.lower() == ".py"
                and p.name != "__init__.py"
                and (not p.name.startswith("_"))
                and p.parent.name != "__pycache__"
            ],
            key=lambda p: p.as_posix().casefold(),
        )

    # 用 STRUCT_ID 做覆盖合并（项目覆盖共享）
    by_id = {}
    for path in (*shared_files, *project_files):
        definition = read_code_definition(path, id_name="STRUCT_ID", payload_name="STRUCT_PAYLOAD")
        if definition is not None:
            by_id[str(definition["STRUCT_ID"]).strip()] = (path, definition["STRUCT_PAYLOAD"])

    return dict(sorted(by_id.items(), key=lambda item: item[1][0].as_posix().casefold()))


def collect_basic_struct_py_files_in_scope(project_archive_path: Path) -> List[Path]:
    """Public API (no leading underscores)."""
    return [path for path, _ in collect_basic_struct_definitions(project_archive_path).values()]

