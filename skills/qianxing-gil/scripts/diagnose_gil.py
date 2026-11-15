#!/usr/bin/env python3
"""Read-only GIL binary structure diagnostics.

Usage: python diagnose_gil.py <path-to-gil>

Parses the 20-byte big-endian header and lists protobuf fields.
Does NOT modify any files.
"""
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
from level_inventory import fields as checked_fields


def read_varint(data, pos):
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return result, pos
        shift += 7
    raise ValueError("Truncated varint")


def parse_protobuf_fields(data):
    return [(number,wire,0 if wire==0 else len(value)) for number,wire,value,_ in checked_fields(data)]


def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_gil.py <path-to-gil>")
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, "rb") as f:
        data = f.read()

    file_size = len(data)
    if file_size < 20:
        print(f"File too small ({file_size} bytes), not a valid GIL")
        sys.exit(1)

    header_vals = struct.unpack(">5I", data[:20])
    payload_size = header_vals[4]

    print(f"File: {filepath} ({file_size} bytes)")
    print('Scope: bounded raw field inspection; native semantics and host compatibility not checked')
    print(f"Header: {list(header_vals)}")
    print(f"  header[0] = payload_size + 20 = {header_vals[0]}")
    print(f"  header[4] = payload_size = {payload_size}")

    if 20 + payload_size > file_size:
        print(f"WARNING: payload_size ({payload_size}) exceeds file bounds")
        sys.exit(1)

    payload = data[20 : 20 + payload_size]
    trailer_size = file_size - 20 - payload_size

    try:
        fields = parse_protobuf_fields(payload)
    except ValueError as e:
        print(f"Protobuf parse error: {e}")
        sys.exit(1)

    print(f"Payload fields: {len(fields)}")
    for fn, wt, size in fields:
        if wt == 2:
            size_str = f"{size} bytes"
        elif wt in (1, 5):
            size_str = f"{size} bytes (fixed)"
        else:
            size_str = "varint"
        print(f"  field {fn}, wire {wt}, {size_str}")

    if trailer_size > 0:
        print(f"Trailer: {trailer_size} bytes")

    expected_total = header_vals[0]
    if file_size != expected_total + trailer_size:
        print(f"WARNING: file size ({file_size}) != header[0] ({expected_total}) + trailer ({trailer_size})")
        sys.exit(1)


if __name__ == "__main__":
    main()
