"""Tests for checksum-pinned public IFC fixture recovery."""
from __future__ import annotations

import hashlib

import pytest

from scripts.recover_public_ifc_fixtures import (
    FixtureRecoveryError,
    PublicFixture,
    recover_fixture,
)


class FakeResponse:
    def __init__(self, payload: bytes, url: str):
        self.payload = payload
        self.url = url
        self.headers = {"content-length": str(len(payload))}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.payload), max(1, chunk_size // 2)):
            yield self.payload[offset : offset + max(1, chunk_size // 2)]


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        assert kwargs["stream"] is True
        assert kwargs["timeout"] == (10, 120)
        return self.response


def fixture_for(payload: bytes) -> PublicFixture:
    return PublicFixture(
        filename="fixture.ifc",
        url="https://media.githubusercontent.com/media/example/repo/main/fixture.ifc",
        bytes_expected=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def test_recovery_streams_and_verifies_exact_payload(tmp_path):
    payload = b"ISO-10303-21;\nHEADER;\nENDSEC;\n"
    fixture = fixture_for(payload)
    session = FakeSession(FakeResponse(payload, fixture.url))

    result = recover_fixture(fixture, tmp_path, session=session)

    assert result["status"] == "downloaded_verified"
    assert (tmp_path / fixture.filename).read_bytes() == payload
    assert session.calls == 1
    assert not list(tmp_path.glob("*.part"))


def test_verified_existing_payload_does_not_use_network(tmp_path):
    payload = b"ISO-10303-21;\nDATA;\nENDSEC;\n"
    fixture = fixture_for(payload)
    (tmp_path / fixture.filename).write_bytes(payload)
    session = FakeSession(FakeResponse(b"unexpected", fixture.url))

    result = recover_fixture(fixture, tmp_path, session=session)

    assert result["status"] == "verified_existing"
    assert session.calls == 0


def test_matching_lfs_pointer_is_replaced_without_overwrite_flag(tmp_path):
    payload = b"ISO-10303-21;\nDATA;\nENDSEC;\n"
    fixture = fixture_for(payload)
    (tmp_path / fixture.filename).write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid sha256:{fixture.sha256}\n"
        f"size {fixture.bytes_expected}\n",
        encoding="utf-8",
    )

    result = recover_fixture(
        fixture,
        tmp_path,
        session=FakeSession(FakeResponse(payload, fixture.url)),
    )

    assert result["status"] == "downloaded_verified"
    assert (tmp_path / fixture.filename).read_bytes() == payload


def test_mismatched_payload_is_preserved_and_requires_overwrite(tmp_path):
    payload = b"ISO-10303-21;\nDATA;\nENDSEC;\n"
    fixture = fixture_for(payload)
    destination = tmp_path / fixture.filename
    destination.write_bytes(b"someone else's model")

    with pytest.raises(FixtureRecoveryError, match="different payload"):
        recover_fixture(
            fixture,
            tmp_path,
            session=FakeSession(FakeResponse(payload, fixture.url)),
        )

    assert destination.read_bytes() == b"someone else's model"


def test_untrusted_redirect_is_rejected_and_partial_file_removed(tmp_path):
    payload = b"ISO-10303-21;\nDATA;\nENDSEC;\n"
    fixture = fixture_for(payload)
    response = FakeResponse(payload, "https://example.invalid/fixture.ifc")

    with pytest.raises(FixtureRecoveryError, match="untrusted fixture source"):
        recover_fixture(fixture, tmp_path, session=FakeSession(response))

    assert not list(tmp_path.iterdir())
