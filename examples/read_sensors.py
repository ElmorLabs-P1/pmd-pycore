"""
Connect to a PMD2/PMD2X device and print averaged rail/aggregate/health
readings in a loop, refreshing in place.
"""

import time

import numpy as np
import serial

from pmd_pycore.core import (
    get_pmd_ports,
    read_device,
    read_sensors,
    translate_sensor_struct,
    translate_aggregate_power,
    translate_chip_sensors,
    translate_hpwr_temperatures,
    PMD2X_PRODUCT_ID,
)

# Number of sensor reads averaged into each displayed update.
NUM_SAMPLES = 20

# Target time between displayed updates. read_uart()'s 5ms inter-command
# delay dominates per-sample cost, so NUM_SAMPLES * 5ms (~100ms) alone is
# already close to this budget -- actual cycles land around 110-125ms, not
# exactly 100ms. This is treated as a target to approach, not a hard cap.
UPDATE_INTERVAL_S = 0.1

CLEAR_SCREEN = "\x1b[2J\x1b[H"


def _average_dicts(dicts, fields):
    return {field: float(np.mean([d[field] for d in dicts])) for field in fields}


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
        time.sleep(1)

        product_id = device_info["ProductId"]
        is_pmd2x = product_id == PMD2X_PRODUCT_ID

        while True:
            cycle_start = time.monotonic()
            rail_samples = []
            aggregate_samples = []
            chip_samples = []
            hpwr_temp_samples = []

            for _ in range(NUM_SAMPLES):
                sensors = None
                while sensors is None:
                    try:
                        sensors = read_sensors(ser, product_id)
                    except serial.SerialException:
                        time.sleep(0.1)
                rail_samples.append(translate_sensor_struct(sensors, product_id))
                aggregate_samples.append(translate_aggregate_power(sensors))
                chip_samples.append(translate_chip_sensors(sensors))
                if is_pmd2x:
                    hpwr_temp_samples.append(translate_hpwr_temperatures(sensors))

            rail_names = rail_samples[0].keys()
            averaged_rails = {
                rail: _average_dicts([s[rail] for s in rail_samples], ("voltage", "current", "power"))
                for rail in rail_names
            }
            averaged_aggregates = _average_dicts(aggregate_samples, ("eps", "pcie", "mb", "total"))
            averaged_chip = _average_dicts(chip_samples, ("vdd", "tchip"))

            lines = [f'{"Rail":<10}{"Voltage":>10}{"Current":>10}{"Power":>10}']
            for rail, reading in averaged_rails.items():
                lines.append(
                    f'{rail:<10}{reading["voltage"]:>10.3f}'
                    f'{reading["current"]:>10.3f}{reading["power"]:>10.3f}'
                )
            lines.append("")

            lines.append("--- Aggregate power ---")
            lines.append(f'EPS (CPU):       {averaged_aggregates["eps"]:>8.3f} W')
            lines.append(f'PCIe (GPU):      {averaged_aggregates["pcie"]:>8.3f} W')
            lines.append(f'Motherboard:     {averaged_aggregates["mb"]:>8.3f} W')
            lines.append(f'Total:           {averaged_aggregates["total"]:>8.3f} W')
            lines.append("")

            lines.append("--- Device health ---")
            lines.append(f'{"Supply (Vdd):":<17}{averaged_chip["vdd"]:>8.3f} V')
            lines.append(f'{"Chip temp:":<17}{averaged_chip["tchip"]:>8.1f} C')
            if is_pmd2x:
                def fmt_temp(samples, key):
                    values = [s[key] for s in samples if s[key] is not None]
                    return f"{np.mean(values):>8.1f} C" if values else f"{'n/c':>8} C"

                lines.append(f'{"12VHPWR in:":<17}{fmt_temp(hpwr_temp_samples, "ts_in")}')
                lines.append(f'{"12VHPWR out:":<17}{fmt_temp(hpwr_temp_samples, "ts_out")}')

            print(CLEAR_SCREEN + "\n".join(lines), flush=True)

            elapsed = time.monotonic() - cycle_start
            time.sleep(max(0.0, UPDATE_INTERVAL_S - elapsed))
    finally:
        ser.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
