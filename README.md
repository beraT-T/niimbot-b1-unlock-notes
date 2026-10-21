# NIIMBOT B1 RFID-free printing notes

Reproducible patches and device test notes for **NIIMBOT B1 hardware 6.01 / firmware 6.19**. Based on [lotabout's 6.19 port](https://github.com/lotabout/niimbot/tree/e3746375de3373c7a63810d2b3aac1e3d9087193), derived from [ThreeDaPrint](https://github.com/ThreeDaPrint/niimbot).

## Current result — October 21, 2026

The operator reports that the latest variant prints without a label RFID tag **at the same apparent speed and contrast as tagged media**. Earlier variants printed tagless labels slowly and faintly, or stretched tagged output vertically. The final change prevents the density command handler from reselecting the fallback printing mode.

This is a published experimental milestone, **not production-qualified firmware or a fully open-source printer firmware**. The proprietary base image is still required. No firmware binaries are distributed here. See [test results and patch details](RESULTS-2026-10-21.md).

## Scope and remaining limitations

- Tested on **one B1, HW 6.01 / FW 6.19**, with 50 x 30 mm gap labels at density 3. The paper was original label stock separated from its RFID tag; purchased third-party rolls have not been validated.
- Speed and contrast matching are the operator's visual/audible comparison, not timed throughput or optical-density measurements. Exact dimensions on the final build and a separate post-final-patch tagged regression test have not been recorded.
- **The first label after loading media can still be misaligned.** Subsequent labels aligned in earlier tests. Plan for a sacrificial first label and inspect alignment; this is not a validated automatic alignment procedure. Do not assume an 8-row blank page behaves identically to a full label.
- Command `0x8e` calibration advanced four to five labels in tests. Its first subsequent print was offset approximately 6–9 mm. It is not a reliable one-label alignment command. Automatic first-label alignment remains unresolved.
- Long runs, all density settings, other label dimensions, other B1 revisions, and thermal/print-head lifetime have not been established. Do not raise density automatically to compensate for a problem.
- Earlier revisions were exercised through USB CLI and Chrome/NiimBlue over USB and Bluetooth. The final revision has not received a complete transport/application regression matrix.

## Risks and disclaimer

This is independent community research, unaffiliated with or endorsed by NIIMBOT. Firmware modification may damage the printer or print head, cause overheating or unusable output, affect warranty/support eligibility, or make recovery impossible. Use at your own risk; no compatibility, fitness, safety, or recovery guarantee is made. The MIT license includes warranty and liability disclaimers.

The patch changes RFID handling and printing behavior. Restoring motor timing and some coefficients does **not** establish stock-equivalent heating: shared coefficients and density hooks remain modified. Hashes establish file identity, not physical safety. Stop testing if behavior is abnormal or the printer overheats.

Use only the exact verified **6.19** source for **HW 6.01**. Never substitute a 4.x/5.x image. Keep the original image, but understand that a backup file cannot recover a device whose upgrade interface no longer works. Restoration to completely stock firmware has not been tested on this device. Respect applicable law and the rights/licenses of firmware and upstream authors.

## Reproduce the tested variant

Requirements: Python 3, Git and curl. Run from this repository's root. Review scripts before execution. Building does not contact the printer.

```sh
git clone https://github.com/lotabout/niimbot.git upstream
git -C upstream checkout --detach e3746375de3373c7a63810d2b3aac1e3d9087193
mkdir -p local
curl --fail --location https://fw.niim.blue/stable/B1/B1_6.19.bin \
  --output local/B1_6.19_stock.bin
python3 upstream/build/build_b1_619_density.py \
  --src local/B1_6.19_stock.bin --out local/B1_6.19_density_coeff.bin
python3 upstream/repro/verify_b1_619_density.py \
  --src local/B1_6.19_stock.bin --img local/B1_6.19_density_coeff.bin
python3 scripts/build_final.py \
  --stock local/B1_6.19_stock.bin --density local/B1_6.19_density_coeff.bin \
  --out local/B1_6.19_mode0_densitytest.bin
```

Stop on any failure. The local builder rejects incorrect input size/hash, unexpected patch bytes, an incorrect output hash, and an existing output file. The upstream verifier has optional checks: inspect any `SKIP` lines. Its Capstone check passed during our October 21 review of the upstream density image; that check alone does not validate this final variant.

All images are 124436 bytes:

| Image | SHA-256 |
|---|---|
| Stock 6.19 | `a4973f78ed4416df3c614d4a87c30df68daf30fe3cf7f9aa3987bc0944650b57` |
| Upstream density | `12bd8e925b9de46b543bd2caf6b3bcc1b3bde294a80836996eeff8be8b9d5876` |
| Latest operator-tested variant | `bdbe795844d700b07da4c249cd9bce81b1cb785349de2ec9abf528da16cfffe1` |

The source is from the [community firmware collection](https://fw.niim.blue/stable/B1/), not a device readback or vendor-authenticated dump. The generated filename is retained to match the tested artifact; “densitytest” does not identify a vendor release.

## Installation and initial checks

Disconnect browser/printer clients. Use a USB data cable, sufficient battery charge and an uninterrupted connection. Install the pinned CLI, scan, and inspect the printer before flashing:

```sh
npm install --prefix local/cli @mmote/niimblue-node@1.4.1
node local/cli/node_modules/@mmote/niimblue-node/cli.mjs scan -t serial
NIIMBOT_PORT=/dev/cu.usbmodemYOUR_DEVICE
node local/cli/node_modules/@mmote/niimblue-node/cli.mjs info -t serial -a "$NIIMBOT_PORT"
```

Replace the placeholder port with the scanned B1 port. Confirm hardware 6.01 and firmware 6.19. The following command **writes firmware**:

```sh
node local/cli/node_modules/@mmote/niimblue-node/cli.mjs flash \
  -t serial -a "$NIIMBOT_PORT" -n 6.19 -f local/B1_6.19_mode0_densitytest.bin
```

After successful completion the printer shuts down. Power it on manually and repeat `info`. In one test, USB reconnection was needed after negotiation timed out. All variants still report 6.19; the version string cannot identify the installed patch. Successful upload is not a flash readback verification.

Load gap labels, keep the RFID-equipped roll away and query:

```sh
node local/cli/node_modules/@mmote/niimblue-node/cli.mjs rfid -t serial -a "$NIIMBOT_PORT"
```

Confirm `tagPresent: false`. Start with one low-coverage test at density 3, 384 x 240 dots, direction `top`, B1 task, label type 1. Use a 20 mm square/ruler to check both axes and leading margins, then compare subsequent labels without opening the lid. Check actual paper output; 100% protocol completion can occur with a blank print. Check tagged media separately. In [NiimBlue](https://niim.blue/), use 50 x 30 mm gap media and account for the 384-dot (~48 mm) printable head width.

If the upgrade interface still works, the corresponding stock restoration command is below. **This recovery has not been exercised**:

```sh
node local/cli/node_modules/@mmote/niimblue-node/cli.mjs flash \
  -t serial -a "$NIIMBOT_PORT" -n 6.19 -f local/B1_6.19_stock.bin
```

## Attribution and license

- [lotabout/niimbot](https://github.com/lotabout/niimbot/tree/e3746375de3373c7a63810d2b3aac1e3d9087193): upstream 6.19 port, RFID bypass, density hooks, build and verification tools.
- [ThreeDaPrint/niimbot](https://github.com/ThreeDaPrint/niimbot): original upstream reverse engineering and density work.
- [MultiMote/niimbluelib](https://github.com/MultiMote/niimbluelib), [niimblue-node](https://github.com/MultiMote/niimblue-node), and [NiimBlue](https://github.com/MultiMote/niimblue): transport, CLI and browser software.
- This repository: additional device observations, patch isolation, reproduction script and documentation, developed with assistance from Claude and Codex. AI-generated analysis was checked where stated; do not treat hypotheses as measurements.

Original documentation and code in this repository are MIT licensed; see [LICENSE](LICENSE). This does not license the vendor firmware or upstream code, which retain their own terms. This is not a claim of independent authorship of the upstream unlock.

For additional reports, include hardware/firmware, image SHA-256, media, density, transport, dimensions and observed results. Remove serial numbers, MAC addresses, RFID identifiers and credentials from logs.

Historical investigation: [October 21 initial analysis](INVESTIGATION-2026-10-21.md). Its earlier candidate status is superseded by the current results where explicitly noted.
