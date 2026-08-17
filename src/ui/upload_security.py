"""Bounded, streaming persistence for untrusted Streamlit uploads."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tempfile
from typing import BinaryIO, Collection

from src.ui.export_helpers import safe_uploaded_filename


MEBIBYTE = 1024 * 1024
MAX_IFC_UPLOAD_BYTES = 200 * MEBIBYTE
MAX_REGULATION_UPLOAD_BYTES = 25 * MEBIBYTE
UPLOAD_CHUNK_BYTES = MEBIBYTE
IFC_SUFFIXES = frozenset({".ifc", ".ifczip"})
REGULATION_SUFFIXES = frozenset({".txt", ".md", ".pdf", ".docx"})


class UploadValidationError(ValueError):
    """Raised when an upload violates the application's resource policy."""


@dataclass(frozen=True)
class SavedUpload:
    """Verified metadata for one upload persisted in temporary storage."""

    path: str
    original_name: str
    safe_name: str
    suffix: str
    bytes_written: int
    sha256: str


def validate_upload_metadata(
    uploaded_file: BinaryIO,
    *,
    allowed_suffixes: Collection[str],
    max_bytes: int,
) -> tuple[str, str]:
    """Validate the declared upload name and size before reading its payload."""
    original_name = str(getattr(uploaded_file, "name", "upload"))
    safe_name = safe_uploaded_filename(original_name)
    suffix = Path(safe_name).suffix.lower()
    normalized_suffixes = {item.lower() for item in allowed_suffixes}
    if suffix not in normalized_suffixes:
        allowed = ", ".join(sorted(normalized_suffixes))
        raise UploadValidationError(f"Unsupported file type '{suffix or 'none'}'. Allowed: {allowed}.")

    declared_size = getattr(uploaded_file, "size", None)
    if isinstance(declared_size, int):
        if declared_size <= 0:
            raise UploadValidationError("The uploaded file is empty.")
        if declared_size > max_bytes:
            raise UploadValidationError(
                f"The upload exceeds the {max_bytes // MEBIBYTE} MB application limit."
            )
    return safe_name, suffix


def persist_uploaded_file(
    uploaded_file: BinaryIO,
    directory: str | Path,
    *,
    allowed_suffixes: Collection[str],
    max_bytes: int,
) -> SavedUpload:
    """Stream an upload to temporary storage with an atomic final rename."""
    safe_name, suffix = validate_upload_metadata(
        uploaded_file,
        allowed_suffixes=allowed_suffixes,
        max_bytes=max_bytes,
    )
    save_dir = Path(directory)
    save_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    bytes_written = 0
    part_path: Path | None = None

    try:
        uploaded_file.seek(0)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".upload-",
            suffix=".part",
            dir=save_dir,
            delete=False,
        ) as destination:
            part_path = Path(destination.name)
            while True:
                chunk = uploaded_file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise UploadValidationError(
                        f"The upload exceeds the {max_bytes // MEBIBYTE} MB application limit."
                    )
                digest.update(chunk)
                destination.write(chunk)

        if bytes_written == 0:
            raise UploadValidationError("The uploaded file is empty.")

        sha256 = digest.hexdigest()
        final_path = save_dir / f"{sha256[:12]}_{safe_name}"
        part_path.replace(final_path)
        part_path = None
        return SavedUpload(
            path=str(final_path),
            original_name=str(getattr(uploaded_file, "name", safe_name)),
            safe_name=safe_name,
            suffix=suffix,
            bytes_written=bytes_written,
            sha256=sha256,
        )
    finally:
        if part_path is not None:
            part_path.unlink(missing_ok=True)
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass
