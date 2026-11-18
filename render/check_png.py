#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_png.py -- validate a candidate entry against this competition's gate.

    python render/check_png.py entry.png [entry2.png ...]

Standard library only, the same constraint the graded runtime runs under.
Checks, exiting non-zero on the first failure:

  signature   the first 8 bytes are the PNG magic (RULES: "a PNG or a JPEG,
              told apart by its first bytes")
  header      IHDR is the first chunk; 8-bit truecolour/grayscale; width and
              height each <= 1024
  size cap    the file is <= 1048576 bytes
  wholeness   every chunk's CRC32 matches, the stream runs IHDR .. IEND with
              no trailing bytes (RULES: "every PNG chunk with its checksum")
  pixels      every IDAT concatenated zlib-inflates to exactly
              height * (1 + width * channels) bytes, so the pixel data really
              is the image its header describes
  determinism given several files, their sha256 digests must all be equal
"""
from __future__ import annotations

import hashlib
import struct
import sys
import zlib

CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}   # colour type -> samples per pixel
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(msg: str):
    print(f"FAIL  {msg}")
    raise SystemExit(1)


def check(path: str) -> str:
    data = open(path, "rb").read()
    print(f"file        : {path}")

    if data[:8] != PNG_MAGIC:
        fail("signature          not a PNG")
    if len(data) > 1048576:
        fail(f"size cap           {len(data)} bytes > 1048576")
    print(f"signature   : ok (PNG, {len(data)} bytes <= 1048576)")

    pos, chunks, ihdr, idat = 8, [], None, b""
    while pos < len(data):
        if pos + 8 > len(data):
            fail("truncated          chunk header at end of file")
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if len(body) != length:
            fail(f"truncated          {ctype!r} declares {length} bytes")
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc:
            fail(f"crc                {ctype.decode('latin1')} chunk CRC mismatch")
        chunks.append(ctype)
        if ctype == b"IHDR":
            ihdr = body
        elif ctype == b"IDAT":
            idat += body
        pos += 12 + length
        if ctype == b"IEND":
            break
    if pos != len(data):
        fail(f"trailing bytes     {len(data) - pos} bytes after IEND")
    if not chunks or chunks[0] != b"IHDR":
        fail("structure          IHDR is not the first chunk")
    if chunks[-1] != b"IEND":
        fail("structure          no IEND chunk")
    print(f"structure   : ok ({len(chunks)} chunks, crc verified, IHDR..IEND clean)")

    w, h, depth, ctype, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr)
    if depth != 8:
        fail(f"bit depth          {depth} (this checker reads 8-bit images)")
    if ctype not in CHANNELS:
        fail(f"colour type        {ctype} unsupported")
    if interlace != 0:
        fail("interlace          interlaced PNG not expected")
    if w > 1024 or h > 1024:
        fail(f"dimensions         {w}x{h} exceeds 1024x1024")
    print(f"header      : ok (IHDR {w}x{h}, 8-bit, colour type {ctype})")

    raw = zlib.decompress(idat)
    want = h * (1 + w * CHANNELS[ctype])
    if len(raw) != want:
        fail(f"pixels             inflated {len(raw)} bytes, expected {want}")
    for row in range(h):
        f = raw[row * (1 + w * CHANNELS[ctype])]
        if f > 4:
            fail(f"filter             row {row} uses filter type {f}")
    print(f"pixels      : ok ({len(raw)} bytes of scanlines, all filter types valid)")

    digest = hashlib.sha256(data).hexdigest()
    print(f"sha256      : {digest}")
    return digest


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: check_png.py <entry.png> [entry2.png ...]")
    digests = [check(p) for p in argv[1:]]
    if len(set(digests)) != 1:
        fail(f"determinism        {len(set(digests))} distinct digests across "
             f"{len(digests)} files")
    if len(digests) > 1:
        print(f"determinism : ok ({len(digests)} runs produced the same sha256)")
    print("PASS: entry is within the gate")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
