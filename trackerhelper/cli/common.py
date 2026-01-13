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
