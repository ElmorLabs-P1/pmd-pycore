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

    try:
        ser = serial.Serial(port, 115200, timeout=1, write_timeout=1, rtscts=False, dsrdtr=False)
    except serial.SerialException as e:
        print(f"Failed to open {port}: {e}")
        return

    try:
        ser.dtr = True
        # The device pushes an unsolicited welcome string on DTR assert, but it
        # can arrive after this point rather than before it. Give it a moment to
        # land, then flush -- read_uart() also flushes before each command, so a
        # late push can never corrupt the next real response.
        time.sleep(0.1)
        ser.reset_input_buffer()

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
    finally:
        ser.close()


if __name__ == "__main__":
    main()
