# Known limitations

Things this library doesn't do yet, and why, so nobody has to re-derive this
from commit history.

## Only four PMD2/PMD2X commands are implemented

`pmd_pycore` implements `CMD_WELCOME`, `CMD_READ_VENDOR_DATA`, `CMD_READ_UID`,
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

## PMD2 (non-X) hardware: verified, with one open question

A real PMD2 (ProductId `0x15`, `FwVersion: 0x2`) has been tested: identity,
the 10-channel `SensorStructPMD2` layout, `PMD2_CHANNELS` mapping, and
aggregate power all decode correctly, and `quickstart.py`/`read_sensors.py`
both run cleanly against it (correctly skipping the PMD2X-only 12VHPWR
section).

`Tchip` reads a consistent raw `0` on this device across 20+ reads over 4+
seconds -- not a translation bug (the raw wire value is 0, confirmed by
reading the struct directly), but unclear whether that firmware revision
doesn't populate chip temperature on PMD2, or whether it needs a longer
warm-up than tested here. `Vdd` reads a plausible ~3.28V on the same device,
so this looks specific to `Tchip`.

Note this PMD2 unit's `FwVersion: 0x2` is not the same firmware line as the
PMD2X unit's `FwVersion: 0x0` discussed above -- they're different product
variants with independent version counters, not sequential revisions of the
same thing.

## PMD-USB: no firmware source, config writing and raw-ADC path unimplemented

Unlike PMD2/PMD2X, there is no public PMD-USB firmware source to check
against. This was ported from and verified against reference
implementations -- [PMDLogger](https://github.com/ElmorLabs/PMDLogger)'s C#
`PMD_USB_Device.cs`, the official [PMD-USB](https://github.com/ElmorLabs/PMD-USB)
GUI app's `FormPMD.cs`, and the Python sample scripts
[pmd-usb-serial-interface-fast](https://github.com/ElmorLabs/pmd-usb-serial-interface-fast)
and [elmorlabs-pmd-usb-serial-interface](https://github.com/bjorntas/elmorlabs-pmd-usb-serial-interface)
-- plus a real device: identity (`CMD_WELCOME`/`CMD_READ_ID`),
`CMD_READ_SENSOR_VALUES`'s plain `int16*0.01V`/`*0.1A` scaling, and
`CMD_READ_CONFIG`'s 34-byte `ConfigStructV5` layout (firmware >= 6) all
decode correctly against a live device.

`CMD_READ_SENSOR_VALUES` already returns calibrated readings -- confirmed
by `FormPMD.cs`'s live monitoring loop, which calls it directly with no
client-side offset/gain correction. So there's no separate calibration gap
for sensor reading the way there briefly seemed to be. `CMD_READ_ADC` (the
raw, uncalibrated 12-bit path PMD-USB's higher-speed continuous-TX mode
uses) and `CMD_WRITE_CONFIG`/device settings management are both out of
scope -- read-only telemetry is covered, config writing and the raw-ADC
path are not.

There is no per-unit UID/UUID anywhere for PMD-USB: no UART command for
one (confirmed against `FormPMD.cs`'s full command enum and by probing
unused command bytes 9-19 against a live device -- all silently ignored),
and the CH340 chip's USB serial-number field reads empty on the device
tested here. Unlike PMD2/PMD2X's `CMD_READ_UID`, there's no way to tell two
PMD-USB units apart besides which COM port they happen to land on.

`PMDLogger` also has a `PMD_Device.cs` for an original PMD variant that
connects over I2C via an EVC2 USB-to-I2C bridge rather than USB-serial --
a different physical interface entirely, not something `pyserial` can talk
to and out of scope for this library.

## Linux support: code-reviewed, not hardware-tested

Nothing in `pmd_pycore` is Windows-specific: port discovery uses
`serial.tools.list_ports.comports()` and checks `p.hwid` for
`VID:PID=...`, which pyserial's Linux backend (`list_ports_linux.py`)
produces via the same shared `usb_info()` formatting Windows uses -- not
a Windows-only string. Port names are always treated as opaque strings
passed straight to `serial.Serial()`, with no `COMx`-shaped parsing
anywhere. `rtscts`/`dsrdtr`/`.dtr` are standard pyserial attributes backed
by termios on POSIX, not Windows-only workarounds.

That said, this has only been reviewed, not run against real hardware on
Linux -- all verification in this repo so far has been on Windows. If you
hit something that doesn't work on Linux, it's worth filing, not assuming
away.

## Examples only talk to one device at a time

`get_pmd_ports()`/`find_pmd_devices()` enumerate all connected PMD2/PMD2X
units, and the library has no single-device assumption baked in -- open one
`serial.Serial` per port and call the read functions independently. Neither
`examples/quickstart.py` nor `examples/read_sensors.py` do this, though:
they pick the first device found (`read_sensors.py` prompts for a port index
if more than one is detected, but still only monitors that one device for
the rest of the run).
