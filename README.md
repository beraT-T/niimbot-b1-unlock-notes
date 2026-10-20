# niimbot-b1-unlock-notes

Reproducible build and hardware test notes for printing without a label RFID tag on a **NIIMBOT B1, hardware 6.01 / firmware 6.19**, using the firmware patch by [lotabout](https://github.com/lotabout/niimbot), derived from [ThreeDaPrint's work](https://github.com/ThreeDaPrint/niimbot).

This repository records an independent installation and test on macOS. The firmware patch and reverse engineering belong to the upstream authors. No firmware binaries or upstream source code are redistributed here.

## Current status — October 21, 2026

**Registration issues remain unresolved.** With the patched firmware, the original
RFID-equipped roll prints at approximately twice the vertical scale. Restoring
the stock motor ramp did not fix it. With the tag absent, scale is correct, but
calibration advances approximately four to five labels and the first subsequent
print can start about 9 mm late. Later prints have aligned correctly on this device.

See [the investigation and diagnostic test plan](INVESTIGATION-2026-10-21.md)
for source hashes, the stock-ramp method, static findings and untested diagnostic
variants. A blank alignment print is not a verified workaround. Do not treat
successful initial prints as evidence of reliable media-change calibration.

## Tested configuration

| Item | Value |
|---|---|
| Printer | NIIMBOT B1, model ID 4096 |
| Hardware / firmware | 6.01 / 6.19 |
| Print head | 384 dots, 203 dpi, approximately 48 mm printable width |
| Media | 50 x 30 mm original labels, detached from the RFID-equipped roll |
| Label type / density | Gap (1) / 3 |
| Host | macOS; OS and Chrome versions were not recorded |
| CLI | `@mmote/niimblue-node@1.4.1` |
| Patch revision | `e3746375de3373c7a63810d2b3aac1e3d9087193` |
| Test date | 2026-10-20 |

## Results

- Stock firmware detected the paper and closed lid, but reported no RFID tag. Printing from NiimBlue failed with `Print error 20: WriteRfidFail`.
- The density-controlled image was rebuilt from the original 6.19 image. The result matched the upstream binary byte for byte.
- The upstream verifier passed its available checks: source identity, image size, coefficients, timing table, patch sites, branch targets, generated code bytes, allowed difference regions and output hashes. The optional Capstone disassembly check was initially skipped. It was rerun with Capstone 5.0.6 on October 21 and passed; this is a patch-structure check, not full firmware verification.
- There were **271 changed bytes**, all inside the verifier's allowed regions.
- USB flashing completed with 622/622 chunks and a successful CLI exit. The printer shut down, then responded over USB after a manual power-on.
- RFID remained absent. A single 384 x 240 dot D3 test image completed at 100% print and 100% feed. The operator confirmed a clear physical print.
- The operator also successfully printed without RFID from **Chrome / NiimBlue over Bluetooth and USB**.
- A photo of three consecutive labels showed complete prints within the label boundaries. When the short strip ended, NiimBlue reported `Print error 8 (In_PrintStatus packet flag)`. NiimBlueLib calls code 8 `PaperOutException`; the timing is consistent with the strip running out, but does not independently prove the cause.

### What has not been established

The test used original label paper separated from its RFID tag, **not a purchased third-party roll**. Long-run registration, every density setting, print-head lifetime and recovery after a failed flash were not established. Later media-change and calibration tests exposed the issues described above. A successful single-device test is not a general safety guarantee.

## Compatibility and recovery

These instructions target **HW 6.01 / FW 6.19 only**. Check the printer's reported versions before selecting any image. Do not flash a 5.x image onto a 6.x device, or assume another B1 hardware revision is compatible.

Keep the original firmware before flashing. If the printer still communicates through the upgrade protocol, it may be possible to restore that image. If boot or USB communication is damaged, having the file alone does not guarantee recovery. Reinstalling official firmware also removes the patch.

The patch changes print energy and line timing as well as RFID error handling. File hashes and a reproducible build establish file identity, not electrical or thermal safety.

## Reproduce the image

Requirements: Git, curl, Python 3 and a separate working directory. Review the upstream scripts before running them. This step does not communicate with the printer.

```sh
git clone https://github.com/lotabout/niimbot.git upstream
cd upstream
git checkout --detach e3746375de3373c7a63810d2b3aac1e3d9087193
mkdir -p local
curl --fail --location https://fw.niim.blue/stable/B1/B1_6.19.bin \
  --output local/B1_6.19_stock.bin
shasum -a 256 local/B1_6.19_stock.bin
```

The source SHA-256 must match the table below. Then:

```sh
python3 build/build_b1_619_density.py \
  --src local/B1_6.19_stock.bin --out local/B1_6.19_density_coeff.bin
python3 repro/verify_b1_619_density.py \
  --src local/B1_6.19_stock.bin --img local/B1_6.19_density_coeff.bin
cmp local/B1_6.19_density_coeff.bin firmware/B1_6.19_density_coeff.bin
shasum -a 256 local/B1_6.19_density_coeff.bin
```

Stop on a mismatch. Read the verifier output, including skipped checks; a zero exit status can still include a skipped optional check.

| Image | SHA-256 |
|---|---|
| Original 6.19 | `a4973f78ed4416df3c614d4a87c30df68daf30fe3cf7f9aa3987bc0944650b57` |
| Rebuilt density patch | `12bd8e925b9de46b543bd2caf6b3bcc1b3bde294a80836996eeff8be8b9d5876` |

Both files are 124436 bytes. The original image is obtained from the community-maintained [firmware collection](https://fw.niim.blue/stable/B1/), not read back from the device.

## USB installation on macOS

Use a USB data cable, sufficient battery charge and an uninterrupted connection. Disconnect other applications from the printer. Install the CLI in a dedicated directory:

```sh
mkdir -p ../niimblue-cli
npm install --prefix ../niimblue-cli @mmote/niimblue-node@1.4.1
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs scan -t serial
```

Set `NIIMBOT_PORT` to the actual B1 port returned by the scan; the path below is a placeholder. Inspect the model, hardware and firmware before proceeding.

```sh
NIIMBOT_PORT=/dev/cu.usbmodemYOUR_DEVICE
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs info \
  -t serial -a "$NIIMBOT_PORT"
```

The following command **writes firmware**. Run it only after checking compatibility and the rebuilt file:

```sh
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs flash \
  -t serial -a "$NIIMBOT_PORT" -n 6.19 -f local/B1_6.19_density_coeff.bin
```

Wait for successful completion. The printer is expected to shut down. Turn it on manually, scan again if its port changed, and repeat `info`. The patched image still reports version 6.19; the version string alone cannot identify the patch.

## Verify printing without RFID

Keep the RFID-equipped roll away from the printer and load a sufficiently long strip of gap labels. Query the tag:

```sh
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs rfid \
  -t serial -a "$NIIMBOT_PORT"
```

Confirm `tagPresent: false`. With paper loaded, send one test:

```sh
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs print \
  -t serial -a "$NIIMBOT_PORT" -p B1 -o top -l 1 -q 3 -n 1 \
  -w 384 -h 240 -f contain test-labels/dtest_D3.png
```

Check the physical output as well as the CLI status. In [NiimBlue](https://niim.blue/), use a 50 x 30 mm label, gap media and density 3 as a starting point. Browser printing was confirmed over both Bluetooth and USB. For a new roll, check repeated identical labels for cumulative registration drift.

## Restore the original image

Restoration was **not exercised** in this test. If the printer remains accessible and accepts an upgrade, the corresponding command is:

```sh
node ../niimblue-cli/node_modules/@mmote/niimblue-node/cli.mjs flash \
  -t serial -a "$NIIMBOT_PORT" -n 6.19 -f local/B1_6.19_stock.bin
```

## Credits and references

- [lotabout/niimbot](https://github.com/lotabout/niimbot/tree/e3746375de3373c7a63810d2b3aac1e3d9087193): 6.19 port, build scripts, verification and RFID bypass analysis.
- [ThreeDaPrint/niimbot](https://github.com/ThreeDaPrint/niimbot): upstream 5.22 reverse engineering and density patch.
- [MultiMote/niimbluelib](https://github.com/MultiMote/niimbluelib), [niimblue-node](https://github.com/MultiMote/niimblue-node) and [NiimBlue](https://github.com/MultiMote/niimblue): communication library, CLI and browser client.
- [B1 community hardware notes](https://printers.niim.blue/hardware/niimbot-b1/).

Corrections and additional test reports are welcome. Include hardware/firmware versions, media type, transport and exact results. Remove device serial numbers, MAC addresses and RFID identifiers from public logs.

## License

The original documentation in this repository is licensed under MIT; see [LICENSE](LICENSE). This does not grant rights to the vendor firmware or upstream projects, which remain subject to their respective terms.
