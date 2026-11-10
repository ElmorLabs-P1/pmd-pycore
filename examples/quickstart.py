"""
Minimal example: connect to the first PMD2/PMD2X device found, print its
identity, and read sensors once -- per-rail readings, firmware-computed
aggregate power, chip health, and (PMD2X only) 12VHPWR connector temperatures.
"""

import time
from contextlib import contextmanager
from typing import Dict, Iterator, Optional

import serial

from pmd_pycore.core import (
    get_pmd_ports,
    read_device,
    read_uid,
    read_sensors,
    translate_sensor_struct,
    translate_aggregate_power,
    translate_chip_sensors,
    translate_hpwr_temperatures,
    PMD2_PRODUCT_ID,
    PMD2X_PRODUCT_ID,
)

PRODUCT_NAMES = {PMD2_PRODUCT_ID: "PMD2", PMD2X_PRODUCT_ID: "PMD2X"}


@contextmanager
def connect() -> Iterator[serial.Serial]:
    ports = get_pmd_ports()
    if not ports:
        raise SystemExit("No PMD2/PMD2X device found.")
    if len(ports) > 1:
        print(f"Found {len(ports)} devices, using the first: {ports[0]['port']}")

    port = ports[0]["port"]
    print(f"Connecting to {port}...")

    try:
        # rtscts/dsrdtr disabled: the device uses DTR as its "is a host listening"
        # signal, so pyserial's automatic flow-control handling must stay out of the way.
        with serial.Serial(
            port, 115200, timeout=1, write_timeout=1, rtscts=False, dsrdtr=False
        ) as ser:
            ser.dtr = True
            # The device pushes an unsolicited welcome string on DTR assert, but
            # the push can arrive after this point rather than before it. Give it
            # a moment to land, then flush -- read_uart() also flushes before each
            # command, so a late push can never corrupt the next real response.
            time.sleep(0.1)
            ser.reset_input_buffer()
            yield ser
    except serial.SerialException as e:
        raise SystemExit(
            f"Failed to open {port}: {e}\n"
            "(is another program -- a monitoring app, another instance of this "
            "script -- already using the port?)"
        )


def print_device_info(device_info: Dict[str, int], uid: Optional[str]) -> None:
    product_name = PRODUCT_NAMES.get(device_info["ProductId"], "unknown")
    print("--- Device ---")
    print(f"Product:    {product_name}")
    print(f"Vendor ID:  {hex(device_info['VendorId'])}")
    print(f"Product ID: {hex(device_info['ProductId'])}")
    print(f"Firmware:   {hex(device_info['FwVersion'])}")
    print(f"UID:        {uid or 'unavailable'}")
    print()


def print_rail_readings(readings: Dict[str, Dict[str, float]]) -> None:
    print("--- Rails ---")
    print(f'{"Rail":<10}{"Voltage":>9}{"Current":>9}{"Power":>9}')
    for rail, reading in readings.items():
        print(
            f'{rail:<10}{reading["voltage"]:>8.3f}V{reading["current"]:>8.3f}A'
            f'{reading["power"]:>8.3f}W'
        )
    print()


def print_aggregate_power(aggregates: Dict[str, float]) -> None:
    print("--- Aggregate power ---")
    print(f'EPS (CPU):       {aggregates["eps"]:>8.3f} W')
    print(f'PCIe (GPU):      {aggregates["pcie"]:>8.3f} W')
    print(f'Motherboard:     {aggregates["mb"]:>8.3f} W')
    print(f'Total:           {aggregates["total"]:>8.3f} W')
    print()


def print_device_health(chip: Dict[str, float], hpwr_temps: Optional[Dict[str, Optional[float]]]) -> None:
    def fmt_temp(value: Optional[float]) -> str:
        return f"{value:>8.1f} C" if value is not None else f"{'n/c':>8} C"

    print("--- Device health ---")
    print(f'{"Supply (Vdd):":<17}{chip["vdd"]:>8.3f} V')
    print(f'{"Chip temp:":<17}{chip["tchip"]:>8.1f} C')
    if hpwr_temps is not None:
        print(f'{"12VHPWR in:":<17}{fmt_temp(hpwr_temps["ts_in"])}')
        print(f'{"12VHPWR out:":<17}{fmt_temp(hpwr_temps["ts_out"])}')


def main() -> None:
    with connect() as ser:
        device_info = read_device(ser)
        if device_info is None:
            raise SystemExit("Failed to read device info -- is this a PMD2/PMD2X device?")

        product_id = device_info["ProductId"]
        if product_id not in PRODUCT_NAMES:
            raise SystemExit(f"Unrecognized ProductId {hex(product_id)} -- not a PMD2/PMD2X device?")

        print_device_info(device_info, read_uid(ser))

        sensors = read_sensors(ser, product_id)
        if sensors is None:
            raise SystemExit("Failed to read sensor values.")

        print_rail_readings(translate_sensor_struct(sensors, product_id))
        print_aggregate_power(translate_aggregate_power(sensors))
        hpwr_temps = translate_hpwr_temperatures(sensors) if product_id == PMD2X_PRODUCT_ID else None
        print_device_health(translate_chip_sensors(sensors), hpwr_temps)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
