"""Recover checksum-pinned public IFC fixtures excluded from the repository."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

import requests


CHUNK_BYTES = 1024 * 1024
ALLOWED_SOURCE_HOSTS = frozenset({"media.githubusercontent.com"})


@dataclass(frozen=True)
class PublicFixture:
    filename: str
    url: str
    bytes_expected: int
    sha256: str


PUBLIC_FIXTURES = (
    PublicFixture(
        filename="01_IFC2X3_Duplex_A_20110907.ifc",
        url=(
            "https://media.githubusercontent.com/media/buildingsmart-community/"
            "Community-Sample-Test-Files/main/IFC%202.3.0.1%20%28IFC%202x3%29/"
            "Duplex%20Apartment/Duplex_A_20110907.ifc"
        ),
        bytes_expected=2_380_763,
        sha256="b347a2c8aa8fff6db896a4417a9c50c22ac0ccd7c5cfc22b99b8d29336c606ed",
    ),
    PublicFixture(
        filename="02_IFC2X3_Duplex_Rooms_And_Spaces.ifc",
        url=(
            "https://media.githubusercontent.com/media/buildingsmart-community/"
            "Community-Sample-Test-Files/main/IFC%202.3.0.1%20%28IFC%202x3%29/"
            "Duplex%20Apartment/Duplex_M_20111024_ROOMS_AND_SPACES.ifc"
        ),
        bytes_expected=8_781_887,
        sha256="3cd577ecff9daf91632789a408070251a431b198de7be47f64e01c7fda1be92b",
    ),
    PublicFixture(
        filename="03_IFC2X3_Clinic_Architectural.ifc",
        url=(
            "https://media.githubusercontent.com/media/buildingsmart-community/"
            "Community-Sample-Test-Files/main/IFC%202.3.0.1%20%28IFC%202x3%29/"
            "Medical-Dental%20Clinic/Clinic_Architectural.ifc"
        ),
        bytes_expected=13_003_205,
        sha256="2ac970ce065ecac4e0c9e5f453a257169e90d0067f419b7e33533a64ef837880",
    ),
)


class FixtureRecoveryError(RuntimeError):
    """Raised when a downloaded fixture cannot be authenticated."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fixture(path: Path, fixture: PublicFixture) -> None:
    """Verify exact size, digest and IFC STEP header for a fixture payload."""
    if path.stat().st_size != fixture.bytes_expected:
        raise FixtureRecoveryError(
            f"{fixture.filename}: expected {fixture.bytes_expected} bytes, "
            f"received {path.stat().st_size}."
        )
    if _sha256(path) != fixture.sha256:
        raise FixtureRecoveryError(f"{fixture.filename}: SHA-256 verification failed.")
    with path.open("rb") as handle:
        if not handle.read(32).lstrip().startswith(b"ISO-10303-21;"):
            raise FixtureRecoveryError(f"{fixture.filename}: payload is not an IFC STEP file.")


def _is_expected_lfs_pointer(path: Path, fixture: PublicFixture) -> bool:
    if path.stat().st_size > 512:
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return (
        text.startswith("version https://git-lfs.github.com/spec/v1")
        and f"oid sha256:{fixture.sha256}" in text
        and f"size {fixture.bytes_expected}" in text
    )


def _validate_source_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_SOURCE_HOSTS:
        raise FixtureRecoveryError(f"Refused untrusted fixture source: {url}")


def recover_fixture(
    fixture: PublicFixture,
    output_dir: Path,
    *,
    overwrite: bool = False,
    session=requests,
) -> dict:
    """Download one fixture atomically and return machine-readable evidence."""
    if Path(fixture.filename).name != fixture.filename:
        raise FixtureRecoveryError("Fixture filenames must not contain path components.")
    _validate_source_url(fixture.url)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / fixture.filename

    if destination.exists():
        try:
            verify_fixture(destination, fixture)
            return {**asdict(fixture), "path": str(destination), "status": "verified_existing"}
        except FixtureRecoveryError:
            if not overwrite and not _is_expected_lfs_pointer(destination, fixture):
                raise FixtureRecoveryError(
                    f"{destination} contains a different payload; use --overwrite to replace it."
                )

    part_path: Path | None = None
    try:
        response = session.get(
            fixture.url,
            stream=True,
            timeout=(10, 120),
            allow_redirects=True,
        )
        response.raise_for_status()
        _validate_source_url(response.url)
        declared_length = response.headers.get("content-length")
        if declared_length and int(declared_length) != fixture.bytes_expected:
            raise FixtureRecoveryError(
                f"{fixture.filename}: source declared an unexpected content length."
            )

        bytes_written = 0
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{fixture.filename}-",
            suffix=".part",
            dir=output_dir,
            delete=False,
        ) as handle:
            part_path = Path(handle.name)
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                bytes_written += len(chunk)
                if bytes_written > fixture.bytes_expected:
                    raise FixtureRecoveryError(
                        f"{fixture.filename}: source exceeded the pinned byte count."
                    )
                digest.update(chunk)
                handle.write(chunk)

        if bytes_written != fixture.bytes_expected or digest.hexdigest() != fixture.sha256:
            raise FixtureRecoveryError(f"{fixture.filename}: downloaded payload did not match its pin.")
        verify_fixture(part_path, fixture)
        part_path.replace(destination)
        part_path = None
        return {**asdict(fixture), "path": str(destination), "status": "downloaded_verified"}
    finally:
        if part_path is not None:
            part_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/test_ifc"))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace a mismatched local payload. Known matching Git LFS pointers are replaced automatically.",
    )
    args = parser.parse_args()

    results = []
    failed = False
    for fixture in PUBLIC_FIXTURES:
        try:
            results.append(recover_fixture(fixture, args.output_dir, overwrite=args.overwrite))
        except (FixtureRecoveryError, OSError, requests.RequestException) as exc:
            failed = True
            results.append({**asdict(fixture), "status": "failed", "error": str(exc)})
    print(json.dumps({"fixtures": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
