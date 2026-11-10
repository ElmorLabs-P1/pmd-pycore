"""
Translate raw PMD-USB sensor structures into human-readable readings.
"""

from typing import Dict

from pmd_pycore.core.pmdusb_structures import SensorValuesPMDUSB, PMDUSB_CHANNELS

# Channel indices feeding each aggregate, matching the official PMD-USB GUI
# app's update_task() (FormPMD.cs): PCIE1+PCIE2 -> GPU, EPS1+EPS2 -> CPU.
_GPU_CHANNELS = (0, 1)
_CPU_CHANNELS = (2, 3)


def translate_pmdusb_sensors(sensors: SensorValuesPMDUSB) -> Dict[str, Dict[str, float]]:
    """Convert a raw PMD-USB sensor struct into a dict of channel name -> reading.

    Per the reference implementations (bjorntas's elmorlabs-pmd-usb-serial-interface,
    PMDLogger's PMD_USB_Device.cs, and the official PMD-USB GUI app's
    FormPMD.cs update_task): raw voltage is a signed int16 scaled by 0.01
    (V), raw current by 0.1 (A). CMD_READ_SENSOR_VALUES already returns
    calibrated readings -- the official GUI app's live monitoring loop uses
    this command directly with no client-side calibration math, so no
    offset/gain correction is needed here either.

    Returns:
        Dict[str, Dict[str, float]]: Channel name -> {voltage, current, power}.
    """
    result = {}
    for idx, name in PMDUSB_CHANNELS.items():
        channel = sensors.Channels[idx]
        voltage = channel.Voltage * 0.01
        current = channel.Current * 0.1
        result[name] = {"voltage": voltage, "current": current, "power": voltage * current}
    return result


def translate_pmdusb_aggregate_power(sensors: SensorValuesPMDUSB) -> Dict[str, float]:
    """Compute GPU/CPU/Total power from the per-channel readings, in watts.

    Unlike PMD2/PMD2X, the PMD-USB firmware doesn't compute these aggregates
    on-device -- they're derived client-side here, matching the official
    GUI app: gpu = PCIE1 + PCIE2, cpu = EPS1 + EPS2, total = gpu + cpu.
    """
    readings = translate_pmdusb_sensors(sensors)
    channel_names = list(PMDUSB_CHANNELS.values())

    gpu = sum(readings[channel_names[i]]["power"] for i in _GPU_CHANNELS)
    cpu = sum(readings[channel_names[i]]["power"] for i in _CPU_CHANNELS)

    return {"gpu": gpu, "cpu": cpu, "total": gpu + cpu}
