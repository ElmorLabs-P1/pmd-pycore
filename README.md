# pmd2-pycore

Python interface for ElmorLabs PMD2/PMD2X power measurement devices.

More information: https://elmorlabs.com/product/elmorlabs-pmd2x-power-measurement-device-2x

## Pre-requisites
- Python >= 3.11, with pyserial (and numpy for the example scripts)

## Install

```
pip install -r requirements.txt
pip install -e .
```

## Usage

```python
from pmd2_pycore.core import (
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

See:
- `examples/quickstart.py` — connect once, print device identity/UID, and read every sensor group
  (rails, firmware-computed aggregate power, chip health, and PMD2X's 12VHPWR connector
  temperatures) a single time.
- `examples/read_sensors.py` — a polling/averaging loop that mirrors the original sample script.

## Status

This repository is under active development at
[ElmorLabs-P1/pmd-pycore](https://github.com/ElmorLabs-P1/pmd-pycore). It provides an installable
`pmd2_pycore` package (serial discovery, UART command helpers, PMD2/PMD2X sensor structures, and
readable-unit translation), a test suite, and CI for tests and tagged releases.

## Related repositories

- [PMD2-FW (pmd2x branch)](https://github.com/ElmorLabs/PMD2-FW/tree/pmd2x) — PMD2X firmware,
  useful reference for the UART command set and sensor data structures used here.
