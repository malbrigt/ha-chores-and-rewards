"""Generate brand/icon.png (256x256): a green rounded tile with a white check mark. No deps."""

import struct
import zlib
from pathlib import Path

S = 256
BG = (46, 125, 50)
FG = (255, 255, 255)


def inside_rounded(x: int, y: int, r: int = 48) -> bool:
    cx = min(max(x, r), S - 1 - r)
    cy = min(max(y, r), S - 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def near_segment(px, py, ax, ay, bx, by, w):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    qx, qy = ax + t * dx, ay + t * dy
    return (px - qx) ** 2 + (py - qy) ** 2 <= w * w


rows = []
for y in range(S):
    row = bytearray([0])
    for x in range(S):
        if not inside_rounded(x, y):
            row += bytes((0, 0, 0, 0))
        elif near_segment(x, y, 64, 132, 108, 178, 16) or near_segment(x, y, 108, 178, 196, 82, 16):
            row += bytes((*FG, 255))
        else:
            row += bytes((*BG, 255))
    rows.append(bytes(row))


def chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", S, S, 8, 6, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
out = Path(__file__).resolve().parent.parent / "custom_components/chores_and_rewards/brand/icon.png"
out.write_bytes(png)
print(out, len(png))
