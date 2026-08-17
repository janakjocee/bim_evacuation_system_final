"""Security and resource-boundary checks for untrusted uploads."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from src.nlp import document_loader
from src.nlp.document_loader import RegulationDocumentError, extract_regulation_text
from src.ui.upload_security import (
    IFC_SUFFIXES,
    MEBIBYTE,
    REGULATION_SUFFIXES,
    UploadValidationError,
    persist_uploaded_file,
    validate_upload_metadata,
)


class Upload(io.BytesIO):
    def __init__(self, payload: bytes, name: str, declared_size: int | None = None):
        super().__init__(payload)
        self.name = name
        if declared_size is not None:
            self.size = declared_size


def test_streaming_upload_persists_digest_and_resets_source(tmp_path):
    payload = (b"ifc-model-chunk" * 100_000) + b"end"
    upload = Upload(payload, "../unsafe model.ifc", len(payload))

    saved = persist_uploaded_file(
        upload,
        tmp_path,
        allowed_suffixes=IFC_SUFFIXES,
        max_bytes=10 * MEBIBYTE,
    )

    assert Path(saved.path).read_bytes() == payload
    assert saved.safe_name == "unsafe model.ifc"
    assert saved.sha256 == hashlib.sha256(payload).hexdigest()
    assert saved.bytes_written == len(payload)
    assert upload.tell() == 0
    assert not list(tmp_path.glob("*.part"))


def test_upload_rejects_declared_and_streamed_oversize_payloads(tmp_path):
    declared = Upload(b"small", "model.ifc", 11)
    with pytest.raises(UploadValidationError, match="exceeds"):
        validate_upload_metadata(declared, allowed_suffixes=IFC_SUFFIXES, max_bytes=10)

    streamed = Upload(b"12345678901", "model.ifc")
    with pytest.raises(UploadValidationError, match="exceeds"):
        persist_uploaded_file(
            streamed,
            tmp_path,
            allowed_suffixes=IFC_SUFFIXES,
            max_bytes=10,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["model.exe", "model.ifc.txt", "model"])
def test_upload_rejects_disallowed_or_missing_suffix(name):
    with pytest.raises(UploadValidationError, match="Unsupported file type"):
        validate_upload_metadata(
            Upload(b"payload", name, 7),
            allowed_suffixes=IFC_SUFFIXES,
            max_bytes=MEBIBYTE,
        )


def test_regulation_upload_accepts_only_document_suffixes():
    safe_name, suffix = validate_upload_metadata(
        Upload(b"rule", "ADB.PDF", 4),
        allowed_suffixes=REGULATION_SUFFIXES,
        max_bytes=MEBIBYTE,
    )
    assert safe_name == "ADB.PDF"
    assert suffix == ".pdf"


def test_docx_archive_expansion_limit_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / "oversized.docx"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"A" * 20_000)
    monkeypatch.setattr(document_loader, "MAX_DOCX_UNCOMPRESSED_BYTES", 10_000)

    with pytest.raises(RegulationDocumentError, match="expanded content"):
        extract_regulation_text(path)


def test_docx_archive_entry_limit_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / "too-many-entries.docx"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"<document />")
        archive.writestr("word/extra.xml", b"<extra />")
    monkeypatch.setattr(document_loader, "MAX_DOCX_ARCHIVE_ENTRIES", 1)

    with pytest.raises(RegulationDocumentError, match="too many entries"):
        extract_regulation_text(path)


def test_extracted_text_character_limit_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / "large.txt"
    path.write_text("A" * 101, encoding="utf-8")
    monkeypatch.setattr(document_loader, "MAX_REGULATION_TEXT_CHARACTERS", 100)

    with pytest.raises(RegulationDocumentError, match="character processing limit"):
        extract_regulation_text(path)
