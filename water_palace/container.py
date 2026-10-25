"""Observed 49-byte chunk headers and bounded zlib decompression."""
import struct
import zlib

HEADER = struct.Struct('<QQBQQQQ')
MAGIC = 0x222222229E2A83C1
CHUNK = 131072
MAX_SIZE = 512 * 1024 * 1024


def unpack(data):
    if not data or len(data) > MAX_SIZE:
        raise ValueError('Empty save or input exceeds the 512 MiB limit')
    offset = 0
    result = bytearray()
    blocks = []
    while offset < len(data):
        start = offset
        if len(data) - offset < HEADER.size:
            raise ValueError('Truncated chunk header')
        magic, chunk, method, size, raw_size, size2, raw_size2 = HEADER.unpack_from(data, offset)
        if (magic, chunk, method) != (MAGIC, CHUNK, 3):
            raise ValueError('Unsupported save container')
        if size != size2 or raw_size != raw_size2 or not 0 < raw_size <= CHUNK:
            raise ValueError('Invalid chunk sizes')
        offset += HEADER.size
        if not 0 < size <= len(data) - offset or len(result) + raw_size > MAX_SIZE:
            raise ValueError('Truncated chunk or decompressed size limit exceeded')
        decoder = zlib.decompressobj()
        raw = decoder.decompress(data[offset:offset + size], raw_size + 1)
        if len(raw) != raw_size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('Invalid compressed chunk')
        blocks.append((start, offset, size, raw_size, len(result)))
        result.extend(raw)
        offset += size
    return bytes(result), blocks


def pack(raw):
    if not 0 < len(raw) <= MAX_SIZE:
        raise ValueError('Invalid payload size')
    result = bytearray()
    for offset in range(0, len(raw), CHUNK):
        block = raw[offset:offset + CHUNK]
        compressed = zlib.compress(block)
        result.extend(HEADER.pack(MAGIC, CHUNK, 3, len(compressed), len(block), len(compressed), len(block)))
        result.extend(compressed)
    return bytes(result)
