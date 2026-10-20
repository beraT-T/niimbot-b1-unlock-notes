# B1 6.19 registration investigation — 2026-10-21

Status: unresolved. These observations concern one B1, HW 6.01 / FW 6.19.
They do not establish compatibility with other printers or media.

## Hardware observations

The operator reports approximately twice the vertical scale with the original
RFID-equipped roll after installing the density patch. Horizontal scale remains
correct. The same problem persists with the stock motor ramp restored.
Thus restoring that ramp alone does not solve the problem on this device.

With detached original labels and no tag, scale is correct. The calibration
command (0x8e) advances approximately four to five labels. The first subsequent
print starts approximately 9 mm too late and can span two labels. Later prints,
including a three-copy job without opening the lid, register correctly.
These are operator measurements, not instrumented motion traces.

Both NiimBlue and the inventory application exhibit the problem. The inventory
application now crops its 400-dot source centrally to the 384-dot print head.
Successful printing does not establish reliable registration after a media change.

A blank alignment print is experimental. Its paper cost and ability to correct
registration have not been measured; it is not a verified workaround.

## Source identity and verification

The source is the community-hosted B1 6.19 image, not a device readback or a
vendor-authenticated dump. Its MD5 is `fd9efd1441b5f05ca46c310b8d162dc1`.
The rebuilt density image matches the pinned lotabout image byte for byte;
its MD5 is `1553badbc6b1b53cb36919786149e2de`.

On October 21 the upstream density verifier was rerun with Capstone 5.0.6.
All checks passed, including its optional disassembly check. This verifies the
specified patch structure, not the entire firmware or physical printer behavior.
An attempted Unicorn-based execution test terminated in the host runtime before
producing results; no emulator validation is claimed.

## Stock-ramp variant

This variant starts with the verified density image and replaces file offsets
`0x1d21c..0x1d29b` (128 bytes, 64 little-endian uint16 entries) with the original
image's bytes. Firmware addresses are `0x0102d21c..0x0102d29b`.
No other bytes are changed. Example, after checking both input hashes:

```python
from pathlib import Path
from hashlib import sha256
stock = Path("B1_6.19_stock.bin").read_bytes()
density = Path("B1_6.19_density_coeff.bin").read_bytes()
assert sha256(stock).hexdigest() == "a4973f78ed4416df3c614d4a87c30df68daf30fe3cf7f9aa3987bc0944650b57"
assert sha256(density).hexdigest() == "12bd8e925b9de46b543bd2caf6b3bcc1b3bde294a80836996eeff8be8b9d5876"
out = bytearray(density)
out[0x1d21c:0x1d29c] = stock[0x1d21c:0x1d29c]
assert sha256(out).hexdigest() == "84bc22990a68f49769c9f192aed0ac9a0d1579de07564c881f72d6fb2f1ab8ac"
Path("B1_6.19_density_stockramp.bin").write_bytes(out)
```

MD5: `dc5d862b5c0f359d5190c0a229484482`; size: 124436 bytes.
The variant has 143 changed bytes relative to stock. It was installed and tested;
the tagged-roll vertical stretch persisted. The upstream density build multiplies
the original table by 1.5. That is consistent with a changed motor sound, but an
acoustic comparison after restoring the table has not been recorded.

## Static findings, not a demonstrated fix

Addresses below refer to the known stock image loaded at `0x01010000`.
Analysis uses targeted Thumb disassembly; no complete control-flow recovery or
hardware trace has been completed.

- The routine at `0x01016110` reads label information at `0x0002e458`, including
  tag presence and usage/capacity fields, and chooses a mode stored at
  `0x000204ca`. Valid tagged media can select mode 0; the alternate path selects
  mode 3. The renderers branch on their mode argument. This is a candidate
  explanation for why the same coefficient patch behaves differently with a tag.
  The precise cause of the factor-of-two stretch remains unproven.
- The four literals at `0x01011e60..0x01011e6f`, described as base coefficients
  upstream, are also used by a counter-setting path. For gap media, code at
  `0x01011d38` multiplies a value derived from byte `0x0002007b` by the literal
  at `0x01011e64`, converts to integer and stores it at `0x0002092e`.
  Stock uses 60.0; the density patch uses 400.0. It then selects state 0x13.
  The state-handler code at `0x01014da8` increments a counter at `0x0002092c`
  and compares it with this target. Treating all fifteen literals as exclusively
  thermal parameters is therefore not justified. Whether this path causes the
  reported first-print offset still needs a device test.
- The 0x8e handler calls a feed helper with arguments 150, 800, 0 at
  `0x0101dc70`, after activating calibration. This is consistent with a long
  calibration feed, not a one-label alignment request. Exact physical units and
  stopping behavior are not established here. An acknowledgement alone does not
  demonstrate that physical calibration has finished.
- The firmware has feed calls with different direction arguments. The statement
  that the B1 is inherently unable to retract is not established by these tests.

The original successful D3 test used niimblue-node 1.4.1. A handoff attributed it
to a Python driver with a shorter PrintStart packet; that attribution should not
be used as evidence for a protocol-dependent fix.

## Prepared diagnostic images — not hardware-tested

Neither image below has been installed. They are comparison experiments, not
recommended replacement firmware. No firmware binaries are distributed here.

| Variant | Change | SHA-256 |
|---|---|---|
| RFID-only | Stock image; file offset `0x154c2` changes from `01` to `00`, making `movs r1,#1` become `movs r1,#0` before the RFID-failure bit is ORed into status. Exactly one changed byte. All density and motor code remains stock. | `8fd13225186dfa7e03d279c68d0f80c71469f0475266bbb9eaa56ef94302a363` |
| Stock-feed diagnostic | Stock-ramp variant; restore the 16-byte stock region `0x1e60..0x1e6f`. Exactly 12 bytes differ from stock-ramp. All remaining density hooks and renderer coefficients remain patched. | `fc624f6e2cb80d940db1f7c28cfdf51b366ae168e0287f7ef54c9e3890c6890a` |

Both have the original size of 124436 bytes. Their MD5 values are respectively
`d03aefb6cb08eab5f99223c7ce911ec8` and `c0f27c56461cabf22c92e3815e1735ea`.
Byte comparisons verified the exact permitted differences. This does not prove
that either diagnostic fixes registration. RFID-only may produce blank output
without a tag because it retains the stock renderer behavior.

## Controlled device test

Obtain the operator's approval before every new firmware installation. Start
with RFID-only to establish tagged-roll behavior without density modifications.
Record transport, image hash, tag presence, media dimensions and density.

1. With the original tagged roll, print a 50 x 30 mm ruler containing a 20 x 20 mm
   square at density 3. Measure both axes and the leading margin.
2. Invoke calibration once, wait for all motor movement to stop, then print three
   single labels without opening the lid. Record the first and subsequent margins
   separately and count all blank labels advanced.
3. Repeat with tag absent. Record blank output or an error rather than assuming
   the bypass must produce a visible print.
4. If approved, compare the stock-feed diagnostic using the same sequence. Do
   not change host software or media dimensions between comparisons.
5. Only after geometry is stable, compare densities 2, 3 and 4. A longer run of
   20 labels can check registration drift and observed temperature, but cannot
   establish print-head lifetime or thermal safety.

Retain the stock, density and stock-ramp files. The version remains 6.19 for all
variants; identify a file by its hash. Restoration to stock has not yet been
exercised on this device. Do not use a 4.x or 5.x image on this hardware.

## Attribution

The bypass and density patch originate from
[lotabout's pinned 6.19 work](https://github.com/lotabout/niimbot/tree/e3746375de3373c7a63810d2b3aac1e3d9087193),
based on [ThreeDaPrint](https://github.com/ThreeDaPrint/niimbot).
These notes add observations and diagnostic comparisons, not a claim to have
independently developed the original unlock.
