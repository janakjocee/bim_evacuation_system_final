"""Validation helpers for compressed IFC uploads."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile


MAX_IFCZIP_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_IFCZIP_COMPRESSION_RATIO = 100


class IFCArchiveError(ValueError):
    """Raised when an IFCZIP payload is unsafe or structurally invalid."""


def validate_ifczip(path: str | Path) -> dict[str, int | str]:
    """Validate a single-model IFCZIP without extracting it."""
    archive_path = Path(path)
    try:
        with ZipFile(archive_path) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
    except (BadZipFile, OSError) as exc:
        raise IFCArchiveError("The uploaded IFCZIP is not a readable ZIP archive.") from exc

    if len(entries) != 1:
        raise IFCArchiveError("An IFCZIP upload must contain exactly one IFC model file.")

    entry = entries[0]
    if "\\" in entry.filename:
        raise IFCArchiveError("The IFCZIP contains an unsafe internal path.")
    entry_path = PurePosixPath(entry.filename)
    if entry_path.is_absolute() or ".." in entry_path.parts:
        raise IFCArchiveError("The IFCZIP contains an unsafe internal path.")
    if entry_path.suffix.lower() != ".ifc":
        raise IFCArchiveError("The IFCZIP must contain one file with the .ifc extension.")
    if entry.flag_bits & 0x1:
        raise IFCArchiveError("Encrypted IFCZIP uploads are not supported.")
    if entry.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
        raise IFCArchiveError("The IFCZIP uses an unsupported compression method.")
    if entry.file_size > MAX_IFCZIP_UNCOMPRESSED_BYTES:
        raise IFCArchiveError(
            "The uncompressed IFC exceeds the 512 MB research-prototype safety limit."
        )

    compressed_size = max(entry.compress_size, 1)
    ratio = entry.file_size / compressed_size
    if ratio > MAX_IFCZIP_COMPRESSION_RATIO:
        raise IFCArchiveError("The IFCZIP compression ratio exceeds the safety limit.")

    return {
        "model_name": entry_path.name,
        "uncompressed_bytes": entry.file_size,
        "compressed_bytes": entry.compress_size,
    }
