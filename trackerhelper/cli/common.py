from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_root(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        logger.error("Error: '%s' is not a directory.", root)
        return False
    return True


def ensure_executable(name: str) -> bool:
    if shutil.which(name) is None:
        logger.error("Error: '%s' not found in PATH.", name)
        return False
    return True


def resolve_root(path_str: str) -> Path:
    return Path(path_str).expanduser().resolve()


def prepare_audio_root(path_str: str, *, skip_checks: bool) -> tuple[Path, int | None]:
    root = resolve_root(path_str)
    if skip_checks:
        return root, None
    if not ensure_root(root):
        return root, 2
    if not ensure_executable("ffprobe"):
        return root, 3
    return root, None


def is_within(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except AttributeError:
        resolved = path.resolve()
        root_resolved = root.resolve()
        return root_resolved == resolved or root_resolved in resolved.parents


def ensure_outside_roots(path: Path, roots: list[Path], label: str) -> bool:
    for root in roots:
        if is_within(path, root):
            logger.error("Error: %s cannot be inside the music root: %s", label, root)
            return False
    return True
