from __future__ import annotations

import logging


def setup_logging() -> None:
    """Configure default console logging."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
