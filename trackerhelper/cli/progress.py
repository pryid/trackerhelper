from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from ..app.progress import ProgressCallback


class _RichProgress(ProgressCallback):
    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        self._progress = progress
        self._task_id = task_id
        self._total: int | None = None
        self._finished = False

    def start(self, total: int) -> None:
        self._total = total
        self._progress.update(self._task_id, total=total)

    def advance(self, step: int = 1) -> None:
        self._progress.advance(self._task_id, step)

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self._total is not None:
            self._progress.update(self._task_id, completed=self._total)


@contextmanager
def progress_bar(description: str) -> Iterator[ProgressCallback]:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        transient=True,
    )
    task_id: TaskID = progress.add_task(description, total=1)
    with progress:
        tracker = _RichProgress(progress, task_id)
        try:
            yield tracker
        finally:
            tracker.finish()
