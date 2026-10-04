"""Generate a simple multiresolution download-arrow ICO using standard-library code."""

import struct
from pathlib import Path


def image(size: int) -> bytes:
    """Draw an opaque rounded blue square and white download arrow as an ICO DIB."""
    pixels = bytearray()
    for y in reversed(range(size)):
        for x in range(size):
            u, v = (x + 0.5) / size, (y + 0.5) / size
            dx, dy = max(0.12 - u, 0, u - 0.88), max(0.12 - v, 0, v - 0.88)
            inside = dx * dx + dy * dy < 0.12**2
            arrow = (
                (0.44 < u < 0.56 and 0.22 < v < 0.55)
                or (0.48 < v < 0.70 and abs(u - 0.5) < 0.70 - v)
                or (0.26 < u < 0.74 and 0.75 < v < 0.81)
            )
            pixels.extend((250, 250, 250, 255) if arrow else (220, 110, 35, 255 if inside else 0))
    header = struct.pack("<IIIHHIIIIII", 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    mask = bytes(((size + 31) // 32) * 4 * size)
    return header + pixels + mask


def main() -> None:
    """Write the committed icon deterministically at common Windows DPI sizes."""
    sizes = (16, 24, 32, 48, 64, 128, 256)
    payloads = [image(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = bytearray()
    for size, payload in zip(sizes, payloads, strict=True):
        entries.extend(
            struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(payload), offset)
        )
        offset += len(payload)
    path = Path(__file__).resolve().parents[1] / "src/mediagrab/desktop/resources/mediagrab.ico"
    path.write_bytes(struct.pack("<HHH", 0, 1, len(sizes)) + entries + b"".join(payloads))


if __name__ == "__main__":
    main()
