#!/usr/bin/env python3
"""news-image-20261123 entrypoint.

Copies the rendered front page (entry.png, drawn in-session for Monday
23 November 2026: 36 stories, UTC timeline, world map, date check) to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

Python 3.13, standard library only. Deterministic: no network, no clock,
no randomness. Before copying it verifies the PNG is whole: the PNG
signature, an IHDR describing a 1024x1024 image, and a final IEND chunk
with the correct CRC.
"""

import os
import shutil
import struct
import sys
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IEND_CRC = 0xAE426082
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024


def check_png(data):
    """Raise ValueError unless data is a whole 1024x1024 PNG."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file: bad signature")
    if len(data) < 8 + 25:
        raise ValueError("PNG too short for an IHDR chunk")
    ihdr_len = struct.unpack(">I", data[8:12])[0]
    ihdr_type = data[12:16]
    if ihdr_type != b"IHDR" or ihdr_len != 13:
        raise ValueError("first chunk is not a 13-byte IHDR")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise ValueError(
            "expected %dx%d, got %dx%d"
            % (EXPECTED_WIDTH, EXPECTED_HEIGHT, width, height)
        )
    if data[-8:-4] != b"IEND":
        raise ValueError("last chunk is not IEND")
    iend_crc = struct.unpack(">I", data[-4:])[0]
    if iend_crc != IEND_CRC:
        raise ValueError(
            "IEND CRC mismatch: 0x%08X" % iend_crc
        )
    # Walk every chunk and confirm the file ends exactly at the end
    # of IEND, with no trailing bytes and every chunk CRC valid.
    off = 8
    while True:
        if off + 12 > len(data):
            raise ValueError("truncated PNG chunk at offset %d" % off)
        chunk_len, chunk_type = struct.unpack(">I4s", data[off:off + 8])
        end = off + 12 + chunk_len
        if end > len(data):
            raise ValueError("chunk %r overruns the file" % chunk_type)
        stored = struct.unpack(">I", data[off + 8 + chunk_len:end])[0]
        actual = zlib.crc32(data[off + 4:off + 8 + chunk_len]) & 0xFFFFFFFF
        if stored != actual:
            raise ValueError("chunk %r has a bad CRC" % chunk_type)
        off = end
        if chunk_type == b"IEND":
            break
    if off != len(data):
        raise ValueError("trailing bytes after IEND")
    return True


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    dst = os.path.join(out_dir, "entry.png")
    with open(src, "rb") as fh:
        data = fh.read()
    check_png(data)
    os.makedirs(out_dir, exist_ok=True)
    with open(dst, "wb") as fh:
        fh.write(data)
    # Confirm the copy is byte-identical to the shipped image.
    with open(dst, "rb") as fh:
        written = fh.read()
    if written != data:
        raise ValueError("written file differs from entry.png")
    print("wrote %s (%d bytes, %dx%d PNG)"
          % (dst, len(data), EXPECTED_WIDTH, EXPECTED_HEIGHT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
