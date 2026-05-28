"""Document conversion helpers for Markdown export."""

from __future__ import annotations

from dataclasses import dataclass
from io import BufferedIOBase, BytesIO
from pathlib import Path
from typing import BinaryIO

from markitdown import (
    FileConversionException,
    MarkItDown,
    MissingDependencyException,
    StreamInfo,
    UnsupportedFormatException,
)

from app.core.errors import ValidationError


@dataclass(slots=True)
class MarkdownConversionResult:
    source_filename: str | None
    title: str | None
    markdown: str


class DocumentConversionService:
    def __init__(self, converter: MarkItDown | None = None) -> None:
        self._converter = converter or MarkItDown()

    @staticmethod
    def _build_stream_info(*, filename: str | None, content_type: str | None) -> StreamInfo:
        extension = Path(filename).suffix.lower() if filename else None
        return StreamInfo(mimetype=content_type or None, extension=extension or None)

    @staticmethod
    def _ensure_buffered_stream(file_stream: BinaryIO) -> BinaryIO:
        if isinstance(file_stream, BufferedIOBase):
            file_stream.seek(0)
            return file_stream

        raw = file_stream.read()
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return BytesIO(raw)

    def convert_stream(
        self,
        *,
        file_stream: BinaryIO,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> MarkdownConversionResult:
        stream_info = self._build_stream_info(filename=filename, content_type=content_type)
        buffered_stream = self._ensure_buffered_stream(file_stream)

        try:
            result = self._converter.convert_stream(buffered_stream, stream_info=stream_info)
        except (FileConversionException, MissingDependencyException, UnsupportedFormatException) as exc:
            raise ValidationError(f"Could not convert '{filename or 'upload'}' to Markdown: {exc}") from exc

        return MarkdownConversionResult(
            source_filename=filename,
            title=result.title,
            markdown=result.markdown,
        )