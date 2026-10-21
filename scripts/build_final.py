#!/usr/bin/env python3
"""Reproduce the operator-tested B1 HW6.01/FW6.19 variant. Never flashes a device."""
import argparse
import hashlib
from pathlib import Path

STOCK = 'a4973f78ed4416df3c614d4a87c30df68daf30fe3cf7f9aa3987bc0944650b57'
DENSITY = '12bd8e925b9de46b543bd2caf6b3bcc1b3bde294a80836996eeff8be8b9d5876'
FINAL = 'bdbe795844d700b07da4c249cd9bce81b1cb785349de2ec9abf528da16cfffe1'
SIZE = 124436


def verified(path, digest):
    data = path.read_bytes()
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Unexpected input identity: {path}')
    return data


def build(stock, density):
    out = bytearray(density)
    # Restore stock motor ramp, feed-target literals and tagged-renderer literals.
    for start, end in [(0x1d21c, 0x1d29c), (0x1e60, 0x1e70),
                       (0x6614, 0x6628), (0x6d50, 0x6d60)]:
        out[start:end] = stock[start:end]
    # Reduce RFID retry travel; select mode0; prevent density handler resetting mode3.
    for offset, before, after in [(0x15442, b'\x41', b'\x01'),
                                   (0x612c, b'\x03', b'\x00'),
                                   (0xdb64, b'\x0b\x70', b'\x00\xbf')]:
        if out[offset:offset + len(before)] != before:
            raise ValueError(f'Unexpected patch site: {offset:#x}')
        out[offset:offset + len(after)] = after
    if hashlib.sha256(out).hexdigest() != FINAL:
        raise ValueError('Final image hash mismatch; no output written')
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stock', type=Path, required=True)
    p.add_argument('--density', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        data = build(verified(a.stock, STOCK), verified(a.density, DENSITY))
        with a.out.open('xb') as f:
            f.write(data)
    except (ValueError, OSError) as e:
        p.exit(1, f'{e}\n')
    print(f'{FINAL}  {a.out} ({len(data)} bytes)')


if __name__ == '__main__':
    main()
