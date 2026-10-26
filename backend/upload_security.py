"""Validate uploaded text files before model prediction."""

from fastapi import UploadFile

from errors import ApiError
import settings


MAX_FILE_BYTES = 32_000


async def read_safe_text_file(file: UploadFile) -> str:
    try:
        filename = file.filename or ""

        # Reject paths and allow only .txt files.
        if (
            not filename.lower().endswith(".txt")
            or "/" in filename
            or "\\" in filename
            or any(ord(char) < 32 for char in filename)
        ):
            raise ApiError(
                415,
                "unsupported_file_type",
                "Upload a .txt file with a valid filename.",
            )

        # Read only up to the limit plus one byte.
        content = await file.read(MAX_FILE_BYTES + 1)

        if len(content) > MAX_FILE_BYTES:
            raise ApiError(
                413,
                "file_too_large",
                "File must be at most 32,000 bytes.",
            )

        if not content:
            raise ApiError(
                422,
                "empty_file",
                "The uploaded file is empty.",
            )

        # Check actual content, rather than trusting the MIME type.
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ApiError(
                415,
                "invalid_encoding",
                "File must contain UTF-8 text.",
            ) from None

        # Reject binary control characters; allow tabs and newlines.
        if any(
            (ord(char) < 32 and char not in "\t\n\r")
            or 127 <= ord(char) <= 159
            for char in text
        ):
            raise ApiError(
                415,
                "invalid_file_content",
                "File contains unsupported control characters.",
            )

        if not text.strip():
            raise ApiError(
                422,
                "empty_file",
                "File must contain readable text.",
            )

        if len(text) > settings.MAX_CHARS:
            raise ApiError(
                413,
                "text_too_long",
                f"Text must be at most {settings.MAX_CHARS:,} characters.",
            )

        # Return text only. Never save or execute the uploaded file.
        return text

    finally:
        await file.close()