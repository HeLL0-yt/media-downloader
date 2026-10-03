"""Validate untrusted URLs and prepare writable output directories."""

import ipaddress
import re
import tempfile
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit

from mediagrab.core.errors import InvalidUrlError, OutputDirectoryError

_HOST_LABEL = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)\Z")
_INVALID_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")


def _has_unsafe_characters(value: str) -> bool:
    return any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)


def _canonical_host(host: str) -> str:
    host = host.removesuffix(".")
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        ascii_host = host.encode("idna").decode("ascii").lower()
    labels = ascii_host.split(".")
    if (
        len(ascii_host) > 253
        or not all(_HOST_LABEL.fullmatch(label) for label in labels)
        or ascii_host.replace(".", "").isdigit()
    ):
        raise ValueError("Invalid host name")
    return ascii_host


def _host_is_allowed(host: str, domain: str) -> bool:
    if host == domain:
        return True
    try:
        ipaddress.ip_address(domain)
    except ValueError:
        return host.endswith("." + domain)
    return False


def validate_url(url: str, allowed_domains: Iterable[str] | None = None) -> str:
    """Validate a URL and return it with surrounding whitespace removed.

    Control characters are rejected before stripping or URL parsing. Credentials,
    backslashes, internal whitespace, malformed escapes, and encoded control
    characters are rejected. No DNS request is made and private hosts are allowed.

    Args:
        url: Untrusted HTTP or HTTPS URL.
        allowed_domains: Optional host names; includes their subdomains. IP
            addresses match exactly. None permits all hosts; an empty list denies
            all hosts. Entries must be bare host names, without ports or schemes.

    Returns:
        Validated URL, preserving its path, query, and fragment.

    Raises:
        InvalidUrlError: The URL or domain policy is invalid or the host is denied.
    """
    if not isinstance(url, str) or _has_unsafe_characters(url):
        raise InvalidUrlError("URLs must not contain control or invisible formatting characters.")
    value = url.strip()
    if (
        not value
        or "\\" in value
        or any(character.isspace() for character in value)
        or _INVALID_ESCAPE.search(value)
        or _has_unsafe_characters(unquote(value))
    ):
        raise InvalidUrlError()
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
            raise ValueError("HTTP or HTTPS with a host is required")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("URL credentials are not allowed")
        if parsed.netloc.startswith("["):
            suffix = parsed.netloc.partition("]")[2]
            if suffix and not suffix.startswith(":"):
                raise ValueError("Invalid text after IPv6 address")
        if parsed.port == 0 or parsed.netloc.endswith(":"):
            raise ValueError("Invalid port")
        host = _canonical_host(parsed.hostname)
    except (ValueError, UnicodeError) as error:
        raise InvalidUrlError() from error
    if allowed_domains is not None:
        if isinstance(allowed_domains, str):
            raise InvalidUrlError("Allowed domains must be a collection of bare host names.")
        try:
            domains = [_canonical_host(domain) for domain in allowed_domains]
        except (ValueError, UnicodeError, AttributeError) as error:
            raise InvalidUrlError(
                "Allowed domains must be bare host names without ports."
            ) from error
        if not any(_host_is_allowed(host, domain) for domain in domains):
            raise InvalidUrlError("This site's domain is not permitted.")
    return value


def ensure_output_directory(directory: Path) -> Path:
    """Create an output directory and verify it accepts a temporary file.

    This is an I/O operation for the download worker, separate from options
    building. The returned resolved path identifies the user-selected destination.

    Args:
        directory: Chosen destination, which can be relative or contain a tilde.

    Returns:
        Absolute, resolved output directory.

    Raises:
        OutputDirectoryError: The directory cannot be resolved, created, or written.
    """
    try:
        resolved = directory.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=resolved) as probe:
            probe.write(b"\0")
            probe.flush()
    except (OSError, RuntimeError, ValueError) as error:
        raise OutputDirectoryError() from error
    return resolved
