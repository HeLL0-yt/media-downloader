"""URL and destination validation, including parser normalization edge cases."""

from pathlib import Path
from typing import cast

import pytest

from mediagrab.core import validators
from mediagrab.core.errors import InvalidUrlError, OutputDirectoryError
from mediagrab.core.validators import ensure_output_directory, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=example&list=example",
        "https://youtu.be/example",
        "http://example.com/video",
        "HTTPS://EXAMPLE.COM/video",
        "https://example.com:8443/video#fragment",
        "http://127.0.0.1:8000/video",
        "http://localhost/video",
        "http://[::1]:8000/video",
        "https://example.com./video",
        "https://bücher.example/video",
        "https://example.com/%E3%81%82?name=%C3%A9",
        "https://example.com/watch?token=abc%2Fdef%2Bghi%3D",
        "https://example.com/watch?redirect=https%3A%2F%2Fexample.org",
        "https://example.com/#javascript:alert(1)",
        "  https://example.com/watch?v=example  ",
    ],
)
def test_valid_urls_preserve_content(url: str) -> None:
    assert validate_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        None,
        123,
        "",
        "   ",
        "youtube.com/watch?v=example",
        "//example.com/video",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "ftp://example.com/video",
        "data:text/plain,example",
        "https:example.com/video",
        "https:///video",
        "https://",
        "https://user@example.com/video",
        "https://user:password@example.com/video",
        "https://@example.com/video",
        "https://example.com\\@evil.example/video",
        "https://exa mple.com/video",
        "https://example.com/video title",
        "https://example.com:65536/video",
        "https://example.com:-1/video",
        "https://example.com:0/video",
        "https://example.com:/video",
        "https://example.com:invalid/video",
        "https://example..com/video",
        "https://example.com../video",
        "https://-example.com/video",
        "https://example-.com/video",
        "https://exa_mple.com/video",
        "https://999.999.999.999/video",
        "https://[invalid]/video",
        "https://[::1]junk/video",
        "https://[::1/video",
        "https://example.com/video%",
        "https://example.com/video%0G",
        "https://%65xample.com/video",
        "https://example.com\u00a0/video",
        "https://example.com/\u200bvideo",
        "https://example.com/\u202evideo",
        "https://example.com/\ud800video",
        "https://example.com/video%00",
        "https://example.com/video%0A",
        "https://example.com/video%0d",
        "https://example.com/video%1f",
        "https://example.com/video%7F",
        "https://example.com/video%C2%85",
        "https://example.com/video%E2%80%8B",
        "https://" + "a" * 64 + ".example/video",
        "https://" + ".".join(["a" * 63] * 5) + "/video",
    ],
)
def test_invalid_urls_are_rejected(url: object) -> None:
    with pytest.raises(InvalidUrlError):
        validate_url(cast(str, url))


@pytest.mark.parametrize("codepoint", [*range(32), *range(127, 160)])
def test_all_c0_and_c1_controls_are_rejected_before_parsing(codepoint: int) -> None:
    character = chr(codepoint)
    for url in (f"https://example.com/vi{character}deo", f"{character}https://example.com/"):
        with pytest.raises(InvalidUrlError):
            validate_url(url)


@pytest.mark.parametrize(
    ("url", "domains"),
    [
        ("https://example.com/video", ["example.com"]),
        ("https://media.example.com/video", ["EXAMPLE.COM."]),
        ("https://bücher.example/video", ["xn--bcher-kva.example"]),
        ("http://127.0.0.1/video", ["127.0.0.1"]),
        ("http://[::1]/video", ["::1"]),
    ],
)
def test_domain_allowlist_accepts_exact_hosts_and_real_subdomains(
    url: str, domains: list[str]
) -> None:
    assert validate_url(url, domains) == url


@pytest.mark.parametrize(
    ("url", "domains"),
    [
        ("https://example.com/video", []),
        ("https://notexample.com/video", ["example.com"]),
        ("https://example.com.evil.example/video", ["example.com"]),
        ("https://sub.127.0.0.1/video", ["127.0.0.1"]),
        ("https://example.com/video", ["https://example.com"]),
        ("https://example.com/video", ["example.com:443"]),
        ("https://example.com/video", ["*.example.com"]),
        ("https://example.com/video", ["example.com.."]),
        ("https://example.com/video", [""]),
        ("https://example.com/video", "example.com"),
        ("https://example.com/video", [None]),
    ],
)
def test_domain_allowlist_rejects_bypasses_and_bad_policy(url: str, domains: object) -> None:
    with pytest.raises(InvalidUrlError):
        validate_url(url, cast(list[str], domains))


def test_invalid_url_message_does_not_include_credentials_or_signed_query() -> None:
    url = "https://user:secret@example.com/watch?token=private-token"
    with pytest.raises(InvalidUrlError) as caught:
        validate_url(url)
    assert "secret" not in str(caught.value)
    assert "private-token" not in str(caught.value)


def test_output_directory_is_created_resolved_and_probe_is_removed(tmp_path: Path) -> None:
    directory = tmp_path / "new" / "nested"
    assert ensure_output_directory(directory) == directory.resolve()
    assert directory.is_dir()
    assert list(directory.iterdir()) == []
    assert ensure_output_directory(directory) == directory.resolve()


def test_output_path_that_is_a_file_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "file"
    destination.write_text("existing file", encoding="utf-8")
    with pytest.raises(OutputDirectoryError) as caught:
        ensure_output_directory(destination)
    assert isinstance(caught.value.__cause__, OSError)
    assert destination.read_text(encoding="utf-8") == "existing file"


def test_unwritable_output_directory_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deny_write(*, dir: Path) -> None:
        raise PermissionError(str(dir))

    monkeypatch.setattr(validators.tempfile, "TemporaryFile", deny_write)
    with pytest.raises(OutputDirectoryError) as caught:
        ensure_output_directory(tmp_path)
    assert isinstance(caught.value.__cause__, PermissionError)


def test_unresolvable_destination_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_expanduser(path: Path) -> Path:
        raise RuntimeError("Home directory is unavailable")

    monkeypatch.setattr(Path, "expanduser", fail_expanduser)
    with pytest.raises(OutputDirectoryError):
        ensure_output_directory(tmp_path)
