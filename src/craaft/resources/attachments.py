from __future__ import annotations

import mimetypes
from builtins import list as _list
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import BinaryIO

from craaft.models import Attachment
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg

# Server cap in internal/attachments/attachments.go
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Download responses can be as large as a single attachment.
_MAX_DOWNLOAD_BYTES = _MAX_UPLOAD_BYTES + (1 << 20)


class AttachmentsResource(BaseResource):
    """Endpoints under ``/cards/{id}/attachments`` and ``/attachments``."""

    def list_for_card(self, card_id: str) -> _list[Attachment]:
        data = self._transport.request(
            "GET", f"/cards/{id_seg(card_id)}/attachments"
        )
        return [Attachment.from_api(row) for row in data]

    def upload(
        self,
        card_id: str,
        *,
        file: str | PathLike[str] | BinaryIO | bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> Attachment:
        """Upload a file to a card.

        Accepts a filesystem path, bytes, or a binary file-like object.
        Requires the card's workspace to be on a paid plan (otherwise 402).
        """
        if isinstance(file, (str, PathLike)):
            path = Path(file)
            name = filename or path.name
            guessed, _ = mimetypes.guess_type(name)
            ct = content_type or guessed or "application/octet-stream"
            raw = path.read_bytes()
            if len(raw) > _MAX_UPLOAD_BYTES:
                raise ValueError("file exceeds the 25 MiB upload limit")
            return self._upload_bytes(card_id, name, raw, ct)

        if isinstance(file, bytes):
            name = filename or "attachment"
            guessed, _ = mimetypes.guess_type(name)
            ct = content_type or guessed or "application/octet-stream"
            if len(file) > _MAX_UPLOAD_BYTES:
                raise ValueError("file exceeds the 25 MiB upload limit")
            return self._upload_bytes(card_id, name, file, ct)

        name = filename or getattr(file, "name", None) or "attachment"
        if isinstance(name, PathLike):
            name = Path(name).name
        guessed, _ = mimetypes.guess_type(str(name))
        ct = content_type or guessed or "application/octet-stream"
        raw = file.read()
        if len(raw) > _MAX_UPLOAD_BYTES:
            raise ValueError("file exceeds the 25 MiB upload limit")
        return self._upload_bytes(card_id, str(name), raw, ct)

    def _upload_bytes(
        self, card_id: str, name: str, raw: bytes, content_type: str
    ) -> Attachment:
        if not raw:
            raise ValueError("cannot upload an empty file")
        data = self._transport.request(
            "POST",
            f"/cards/{id_seg(card_id)}/attachments",
            files={"file": (name, BytesIO(raw), content_type)},
        )
        return Attachment.from_api(data)

    def download(self, attachment_id: str) -> bytes:
        data = self._transport.request(
            "GET",
            f"/attachments/{id_seg(attachment_id)}",
            parse_json=False,
            max_response_bytes=_MAX_DOWNLOAD_BYTES,
        )
        assert isinstance(data, bytes)
        return data

    def delete(self, attachment_id: str) -> None:
        self._transport.request("DELETE", f"/attachments/{id_seg(attachment_id)}")
