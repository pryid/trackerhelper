from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable


def render_csv_rows(rows: Iterable[Iterable[object]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")
