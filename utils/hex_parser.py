import os
from typing import Union


def parse_intel_hex(path: str) -> bytes:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    data = bytearray()
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line.startswith(":"):
                continue

            length = int(line[1:3], 16)
            rectype = int(line[7:9], 16)

            if rectype != 0:
                continue

            for i in range(length):
                start = 9 + i * 2
                end = start + 2
                data.append(int(line[start:end], 16))

    return bytes(data)


def read_firmware(path: str) -> bytes:
    if path.endswith(".hex"):
        return parse_intel_hex(path)
    elif path.endswith(".bin"):
        with open(path, "rb") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file format: {path}")