from __future__ import annotations

import logging
from pathlib import Path

from ..core.utils import which

logger = logging.getLogger(__name__)


def ensure_root(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        logger.error("Error: '%s' is not a directory.", root)
        return False
    return True


def ensure_ffprobe() -> bool:
    if which("ffprobe") is None:
        logger.error("Error: ffprobe not found. Install ffmpeg (ffprobe) and retry.")
        return False
    return True
