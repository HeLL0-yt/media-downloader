"""Fetch pinned upstream Windows tools and verify their published SHA-256."""

import argparse
import hashlib
import json
import logging
import re
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen

_ROOT = Path(__file__).resolve().parents[1]
_LOGGER = logging.getLogger(__name__)


def download(url: str, destination: Path) -> None:
    """Download an HTTPS asset with finite socket timeout and no executable step."""
    if not url.startswith("https://"):
        raise ValueError("HTTPS is required.")
    _LOGGER.info("Downloading %s", url)
    with urlopen(url, timeout=30) as response, destination.open("wb") as output:  # noqa: S310
        if not response.url.startswith("https://"):
            raise ValueError("HTTPS redirect downgrade refused.")
        shutil.copyfileobj(response, output, 1024 * 1024)


def fetch(name: str) -> None:
    """Validate the publisher manifest and pinned digest before extracting tools."""
    config = json.loads((_ROOT / "scripts" / "tools.json").read_text(encoding="utf-8"))[name]
    folder = _ROOT / "vendor" / "packaging" / name
    folder.mkdir(parents=True, exist_ok=True)
    checksum = folder / "published-checksum.txt"
    download(config["checksum_url"], checksum)
    hashes = re.findall(r"\b[0-9a-fA-F]{64}\b", checksum.read_text(encoding="utf-8"))
    expected = config["sha256"]
    if expected not in {value.lower() for value in hashes}:
        raise ValueError("Publisher checksum does not match the pinned digest.")
    archive = folder / "download.zip"
    cached_hash = ""
    if archive.is_file():
        with archive.open("rb") as cached:
            cached_hash = hashlib.file_digest(cached, "sha256").hexdigest()
    if cached_hash != expected:
        download(config["url"], archive)
    with archive.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"Checksum mismatch for {name}; archive will not be extracted.")
    extracted = folder / "upstream"
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            target = (extracted / member.filename).resolve()
            if not target.is_relative_to(extracted.resolve()) or "\\" in member.filename:
                raise ValueError("Unsafe archive path.")
            if member.file_size > 512 * 1024 * 1024:
                raise ValueError("Unexpected archive member size.")
        source.extractall(extracted)
    binaries = ("ffmpeg.exe", "ffprobe.exe") if name == "ffmpeg" else ("deno.exe",)
    sizes = {}
    for binary in binaries:
        matches = list(extracted.rglob(binary))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {binary}.")
        shutil.copy2(matches[0], folder / binary)
        sizes[binary] = matches[0].stat().st_size
    (folder / "verified.json").write_text(
        json.dumps({**config, "binary_sizes": sizes}, indent=2), encoding="utf-8"
    )
    _LOGGER.info("Verified %s %s; executable bytes: %s", name, config["version"], sizes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("ffmpeg", "deno"))
    fetch(parser.parse_args().tool)
