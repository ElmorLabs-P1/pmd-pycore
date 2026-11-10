"""
Minimal example: connect to the first PMD2/PMD2X device found, print its
identity, and read sensors once -- per-rail readings, firmware-computed
aggregate power, chip health, and (PMD2X only) 12VHPWR connector temperatures.
"""

import serial

from pmd2_pycore.core import (
    get_pmd_ports,
    read_device,
    read_sensors,
    translate_sensor_struct,
    translate_aggregate_power,
    translate_chip_sensors,
    translate_hpwr_temperatures,
    PMD2_PRODUCT_ID,
    PMD2X_PRODUCT_ID,
)

PRODUCT_NAMES = {PMD2_PRODUCT_ID: "PMD2", PMD2X_PRODUCT_ID: "PMD2X"}


def connect() -> serial.Serial:
    ports = get_pmd_ports()
    if not ports:
        raise SystemExit("No PMD2/PMD2X device found.")

    port = ports[0]["port"]
    print(f"Connecting to {port}...")

    # rtscts/dsrdtr disabled: the device uses DTR as its "is a host listening"
    # signal, so pyserial's automatic flow-control handling must stay out of the way.
    ser = serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False)
    ser.dtr = True
    ser.read_all()  # discard any unsolicited welcome push sent on DTR assert
    return ser


def print_device_info(device_info: dict) -> None:
    product_name = PRODUCT_NAMES.get(device_info["ProductId"], "unknown")
    print("--- Device ---")
    print(f"Product:    {product_name}")
    print(f"Vendor ID:  {hex(device_info['VendorId'])}")
    print(f"Product ID: {hex(device_info['ProductId'])}")
    print(f"Firmware:   {hex(device_info['FwVersion'])}")
    print()


def print_rail_readings(readings: dict) -> None:
    print("--- Rails ---")
    print(f'{"Rail":<10}{"Voltage":>10}{"Current":>10}{"Power":>10}')
    for rail, reading in readings.items():
        print(
            f'{rail:<10}{reading["voltage"]:>9.3f}V{reading["current"]:>9.3f}A'
            f'{reading["power"]:>9.3f}W'
        )
    print()


def print_aggregate_power(aggregates: dict) -> None:
    print("--- Aggregate power ---")
    print(f'EPS (CPU):       {aggregates["eps"]:>8.3f} W')
    print(f'PCIe (GPU):      {aggregates["pcie"]:>8.3f} W')
    print(f'Motherboard:     {aggregates["mb"]:>8.3f} W')
    print(f'Total:           {aggregates["total"]:>8.3f} W')
    print()


def print_chip_sensors(chip: dict) -> None:
    print("--- Device health ---")
    print(f'Supply (Vdd):    {chip["vdd"]:>8.3f} V')
    print(f'Chip temp:       {chip["tchip"]:>8.1f} C')


def print_hpwr_temperatures(temps: dict) -> None:
    def fmt(value):
        return f"{value:.1f} C" if value is not None else "not connected"

    print(f'12VHPWR in:      {fmt(temps["ts_in"]):>12}')
    print(f'12VHPWR out:     {fmt(temps["ts_out"]):>12}')


def main() -> None:
    ser = connect()
    try:
        device_info = read_device(ser)
        if device_info is None:
            raise SystemExit("Failed to read device info -- is this a PMD2/PMD2X device?")
        print_device_info(device_info)

        product_id = device_info["ProductId"]
        sensors = read_sensors(ser, product_id)
        if sensors is None:
            raise SystemExit("Failed to read sensor values.")

        print_rail_readings(translate_sensor_struct(sensors, product_id))
        print_aggregate_power(translate_aggregate_power(sensors))
        print_chip_sensors(translate_chip_sensors(sensors))
        if product_id == PMD2X_PRODUCT_ID:
            print_hpwr_temperatures(translate_hpwr_temperatures(sensors))
    finally:
        ser.close()


if __name__ == "__main__":
    main()
