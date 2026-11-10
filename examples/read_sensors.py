"""
Connect to a PMD2/PMD2X device and print averaged rail readings in a loop.
"""

import time

import numpy as np
import serial

from pmd2_pycore.core import (
    get_pmd_ports,
    read_device,
    read_sensors,
    translate_sensor_struct,
)

NUM_SAMPLES = 500


def main():
    print("\nFinding potential PMD2/PMD2X Serial Ports...\n")
    ports = get_pmd_ports()
    for i, p in enumerate(ports):
        print(f"{i} - {p['port']}")
    print()

    if not ports:
        print("No PMD2/PMD2X serial ports found.")
        return

    port_index = 0
    if len(ports) > 1:
        print("Multiple PMD2/PMD2X serial ports found. Input which port to use:")
        port_index = int(input())
        if port_index >= len(ports):
            print("Invalid port index.")
            return

    port = ports[port_index]["port"]
    print(f"Using port index {port_index} ({port})\n")

    ser = serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False)
    ser.dtr = True
    ser.read_all()  # discard any unsolicited welcome push

    print("Reading vendor data...")
    device_info = read_device(ser)
    if device_info is None:
        print("Failed to read vendor data from device.")
        return
    print(f"Result: {device_info}\n")

    product_id = device_info["ProductId"]

    while True:
        samples = []
        for _ in range(NUM_SAMPLES):
            sensors = None
            while sensors is None:
                try:
                    sensors = read_sensors(ser, product_id)
                except serial.SerialException:
                    time.sleep(0.1)
            samples.append(translate_sensor_struct(sensors, product_id))

        rail_names = samples[0].keys()
        averaged = {
            rail: {
                field: float(np.mean([s[rail][field] for s in samples]))
                for field in ("voltage", "current", "power")
            }
            for rail in rail_names
        }

        print(f'{"Rail":<10}{"Voltage":>10}{"Current":>10}{"Power":>10}')
        for rail, reading in averaged.items():
            print(
                f'{rail:<10}{reading["voltage"]:>10.3f}'
                f'{reading["current"]:>10.3f}{reading["power"]:>10.3f}'
            )
        print()

        time.sleep(0.5)


if __name__ == "__main__":
    main()
