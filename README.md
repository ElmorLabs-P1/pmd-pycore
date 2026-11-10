# pmd2-pycore

Python interface for ElmorLabs PMD2/PMD2X power measurement devices.

More information: https://elmorlabs.com/product/elmorlabs-pmd2x-power-measurement-device-2x

## Pre-requisites
- Python >= 3.11, with pyserial (and numpy for the example script)

## Install

```
pip install -r requirements.txt
pip install -e .
```

## Usage

```python
from pmd2_pycore.core import get_pmd_ports, read_device, read_sensors, translate_sensor_struct
import serial

port = get_pmd_ports()[0]["port"]
ser = serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False)

device_info = read_device(ser)
sensors = read_sensors(ser, device_info["ProductId"])
readings = translate_sensor_struct(sensors, device_info["ProductId"])
print(readings["12V"])  # {'voltage': 12.0, 'current': 1.0, 'power': 12.0}
```

See `examples/read_sensors.py` for a full polling/averaging loop that mirrors what the original
sample script did.

## Status

This repository is under active development at
[ElmorLabs-P1/pmd-pycore](https://github.com/ElmorLabs-P1/pmd-pycore). It provides an installable
`pmd2_pycore` package (serial discovery, UART command helpers, PMD2/PMD2X sensor structures, and
readable-unit translation), a test suite, and CI for tests and tagged releases.

## Related repositories

- [PMD2-FW (pmd2x branch)](https://github.com/ElmorLabs/PMD2-FW/tree/pmd2x) — PMD2X firmware,
  useful reference for the UART command set and sensor data structures used here.
