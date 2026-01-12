from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class FastPicUploadError(RuntimeError):
    pass


def upload_to_fastpic_get_direct_link(
    file_path: Path,
    *,
    resize_to: int = 500,
    endpoint: str = "https://fastpic.org/upload?api=1",
    timeout: int = 60,
    session=None,
) -> str:
    """Загружает картинку на FastPic и возвращает Direct Link (<imagepath>)."""
    if requests is None:
        raise RuntimeError("Cover upload requires 'requests'. Install it or run without cover upload in release.")

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    s = session or requests.Session()

    data = {
        "method": "file",
        "uploading": "1",
        "check_thumb": "no",
        "check_orig_resize": "1",
        "orig_resize": str(int(resize_to)),
    }

    with file_path.open("rb") as f:
        resp = s.post(endpoint, data=data, files={"file1": f}, timeout=timeout)
    resp.raise_for_status()

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        raise FastPicUploadError(
            f"Не смог распарсить XML-ответ: {e}. Ответ: {resp.text[:300]!r}"
        ) from e

    err = root.findtext("error")
    if err:
        raise FastPicUploadError(f"FastPic вернул ошибку: {err}")

    direct = root.findtext("imagepath")
    if not direct:
        raise FastPicUploadError(f"В ответе нет <imagepath>. Ответ: {resp.text[:500]!r}")

    return direct.strip()


class FastPicCoverUploader:
    """Uploader с переиспользованием Session и простым in-memory кешем."""

    def __init__(
        self,
        *,
        resize_to: int = 500,
        endpoint: str = "https://fastpic.org/upload?api=1",
        timeout: int = 60,
    ) -> None:
        if requests is None:
            raise RuntimeError("FastPicCoverUploader requires 'requests'")
        self.resize_to = int(resize_to)
        self.endpoint = endpoint
        self.timeout = int(timeout)
        self.session = requests.Session()
        self._cache: dict[str, str] = {}

    def upload(self, file_path: Path) -> str:
        key = str(file_path.resolve())
        if key in self._cache:
            return self._cache[key]

        url = upload_to_fastpic_get_direct_link(
            file_path,
            resize_to=self.resize_to,
            endpoint=self.endpoint,
            timeout=self.timeout,
            session=self.session,
        )
        self._cache[key] = url
        return url


def find_cover_jpg(release_folder: Path) -> Path | None:
    """Ищем cover.jpg в папке релиза (case-insensitive)."""
    p = release_folder / "cover.jpg"
    if p.is_file():
        return p

    try:
        for child in release_folder.iterdir():
            if child.is_file() and child.name.lower() == "cover.jpg":
                return child
    except FileNotFoundError:
        return None

    return None
