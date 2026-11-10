# pmd-pycore

Python interface for ElmorLabs PMD power measurement devices (PMD2, PMD2X, PMD-USB).

More information:
- https://elmorlabs.com/product/elmorlabs-pmd2x-power-measurement-device-2x
- https://elmorlabs.com/product/elmorlabs-pmd-usb-power-measurement-device-with-usb/

## Pre-requisites
- Python >= 3.11, with pyserial (and numpy for the example scripts)
- PMD-USB uses a CH340 USB-serial chip. Linux has an in-kernel driver for it (binds
  automatically, nothing to install). **Windows does not ship one** -- if the device shows up
  in Device Manager but never gets a COM port, install the CH340/CH341 driver from the chip
  manufacturer's site ([wch-ic.com](https://www.wch-ic.com/), search "CH340"/"CH341") and
  replug. PMD2/PMD2X use an STM32 VCP instead and don't need a separate driver on either OS.

## Install

```
pip install -r requirements.txt
pip install -e .
```

## Usage

### PMD2 / PMD2X

```python
from pmd_pycore.core import (
    get_pmd_ports,
    read_welcome_string,
    read_device,
    read_uid,
    read_sensors,
    translate_sensor_struct,
)
import serial

port = get_pmd_ports()[0]["port"]
ser = serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False)

device_info = read_device(ser)
sensors = read_sensors(ser, device_info["ProductId"])
readings = translate_sensor_struct(sensors, device_info["ProductId"])
print(readings["12V"])  # {'voltage': 12.0, 'current': 1.0, 'power': 12.0}
```

Currently implemented are the device's read-only commands:
`CMD_WELCOME` (`read_welcome_string`), `CMD_READ_VENDOR_DATA` (`read_device`), `CMD_READ_UID`
(`read_uid`), and `CMD_READ_SENSOR_VALUES` (`read_sensors`). Writing/action commands (continuous
TX, config read/write, reset, bootloader) are not implemented.

See `examples/read_sensors.py` — a polling/averaging loop that mirrors the original sample script.

### PMD-USB

PMD-USB is a different device family -- a CH340 USB-serial bridge rather than PMD2/PMD2X's STM32
VCP, with its own command set and a simpler sensor set (PCIE1, PCIE2, EPS1, EPS2 only; no ATX24
rails, no 12VHPWR). There's no firmware source for it, so this was ported from and verified
against the reference implementations linked below plus a real device.

```python
from pmd_pycore.core import get_pmdusb_ports, read_pmdusb_id, read_pmdusb_sensors, translate_pmdusb_sensors
import serial

port = get_pmdusb_ports()[0]["port"]
ser = serial.Serial(port, 115200, timeout=1)

device_info = read_pmdusb_id(ser)
sensors = read_pmdusb_sensors(ser)
readings = translate_pmdusb_sensors(sensors)
print(readings["EPS1"])  # {'voltage': 12.0, 'current': 1.0, 'power': 12.0}
```

Implemented: `CMD_WELCOME` (`read_pmdusb_welcome_string`), `CMD_READ_ID` (`read_pmdusb_id`), and
`CMD_READ_SENSOR_VALUES` (`read_pmdusb_sensors`/`translate_pmdusb_sensors`). This command already
returns calibrated readings -- confirmed against the official PMD-USB GUI app's source, which
uses it directly with no client-side calibration math -- so `CMD_READ_ADC`'s raw path isn't
needed. `translate_pmdusb_aggregate_power` adds GPU/CPU/Total power (PCIE1+PCIE2 /  EPS1+EPS2 /
sum), computed client-side the same way the official app does; PMD-USB's firmware doesn't
compute these on-device the way PMD2/PMD2X's does.

Note: PMD-USB has no per-unit UID/serial number anywhere -- not in the UART protocol (no command
for it), and not at the USB level (the CH340 chip's serial number field reads empty on the
device tested here). If you have more than one, there's no way to tell them apart besides which
COM port they land on.

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for what's deliberately out of scope and why.

## Examples

- `examples/quickstart.py` — connect to the first device found, trying PMD2/PMD2X first and
  falling back to PMD-USB, print its identity, and read sensor values once (for PMD2/PMD2X:
  per-rail readings, firmware-computed aggregate power, chip health, and PMD2X's 12VHPWR
  connector temperatures).
- `examples/read_sensors.py` — a polling/averaging loop, refreshing in place, for whichever
  device family is connected (same PMD2/PMD2X-first-then-PMD-USB detection as `quickstart.py`).

## Status

This repository is under active development at
[ElmorLabs-P1/pmd-pycore](https://github.com/ElmorLabs-P1/pmd-pycore). It provides an installable
`pmd_pycore` package (serial discovery, UART command helpers, sensor structures, and
readable-unit translation for the supported devices), a test suite, and CI for tests and tagged
releases.

## Related repositories

- [PMD2-FW (pmd2x branch)](https://github.com/ElmorLabs/PMD2-FW/tree/pmd2x) — PMD2X firmware,
  useful reference for the UART command set and sensor data structures used here.
- [PMDLogger](https://github.com/ElmorLabs/PMDLogger) — C# reference implementation for PMD-USB
  (there's no public PMD-USB firmware source); `PMD_USB_Device.cs` has the command set and sensor
  scaling used here.
- [pmd-usb-serial-interface-fast](https://github.com/ElmorLabs/pmd-usb-serial-interface-fast) /
  [elmorlabs-pmd-usb-serial-interface](https://github.com/bjorntas/elmorlabs-pmd-usb-serial-interface) —
  Python sample scripts for PMD-USB, cross-checked against PMDLogger and a real device.
