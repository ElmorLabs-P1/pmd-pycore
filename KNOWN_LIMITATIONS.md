# Known limitations

Things this library doesn't do yet, and why, so nobody has to re-derive this
from commit history.

## Only four commands are implemented

`pmd2_pycore` implements `CMD_WELCOME`, `CMD_READ_VENDOR_DATA`, `CMD_READ_UID`,
and `CMD_READ_SENSOR_VALUES` -- the device's read-only telemetry commands.
Per [PMD2-FW's `pmd2.h`](https://github.com/ElmorLabs/PMD2-FW/blob/pmd2x/Core/Inc/pmd2.h)
and its USB command dispatch
([`usbd_cdc_if.c`](https://github.com/ElmorLabs/PMD2-FW/blob/pmd2x/USB_DEVICE/App/usbd_cdc_if.c)),
the full command set also includes:

- `CMD_READ_DEVICE_DATA` (3) -- declared in the firmware's `USB_CMD` enum but
  has no `case` in the device's dispatch switch. Sending it is a no-op on
  real hardware, not something this library is missing.
- `CMD_WRITE_CONT_TX` (5), `CMD_READ_CONFIG`/`CMD_WRITE_CONFIG` (6/7),
  `CMD_RESET` (0xF0), `CMD_BOOTLOADER` (0xF1), `CMD_MCU_CMD` (0xF2) -- write
  or device-action commands, out of scope for this round of work by request.

## Config/calibration reading is unresolved, not just unimplemented

`CMD_READ_CONFIG` was investigated but deliberately left out. The firmware's
`DeviceConfigStruct` (in `pmd2.h`) changed shape across commits -- fields for
display rotation and timeout were added after this device's firmware was
built (see "Firmware version mismatch" below). Reading `CMD_READ_CONFIG`
against a live PMD2X returned 150 bytes, which didn't cleanly match the byte
layout implied by *any* single commit of `pmd2.h` on the `pmd2x` branch that
was checked. Implementing `read_config()` without pinning down the exact
layout risks silently misdecoding fields. If this becomes needed, resolving
the byte offsets against the actual firmware revision in the field (not just
the latest branch HEAD) is a prerequisite.

## Firmware version mismatch

This library was developed and verified against a PMD2X reporting
`FwVersion: 0x0`. The `pmd2x` branch HEAD defines `FIRMWARE_VERSION 0x00` as
a pre-release placeholder; later commits bump it to `0x02` once
display-rotation/timeout config fields landed. The sensor struct layout
(`SENSOR_POWER_NUM=16`, `Ts[]` temperatures, firmware-computed `HPWR`/
aggregate power) was confirmed against this device and matches the current
branch, but the config struct does not -- see above. A device running
different firmware may need re-verification.

## No PMD2 (non-X) hardware has been tested

Everything here has been verified against a live PMD2X. The PMD2 (non-X)
code paths -- the 10-channel `SensorStructPMD2`, `PMD2_CHANNELS` mapping, no
`Ts[]`/HPWR-wire fields -- are implemented per the firmware source but have
not been run against real PMD2 hardware.

## Examples only talk to one device at a time

`get_pmd_ports()`/`find_pmd_devices()` enumerate all connected PMD2/PMD2X
units, and the library has no single-device assumption baked in -- open one
`serial.Serial` per port and call the read functions independently. Neither
`examples/quickstart.py` nor `examples/read_sensors.py` do this, though:
they pick the first device found (`read_sensors.py` prompts for a port index
if more than one is detected, but still only monitors that one device for
the rest of the run).
