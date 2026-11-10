"""
Translate raw PMD-USB sensor structures into human-readable readings.
"""

from typing import Dict

from pmd_pycore.core.pmdusb_structures import SensorValuesPMDUSB, PMDUSB_CHANNELS


def translate_pmdusb_sensors(sensors: SensorValuesPMDUSB) -> Dict[str, Dict[str, float]]:
    """Convert a raw PMD-USB sensor struct into a dict of channel name -> reading.

    Per the reference implementations (bjorntas's elmorlabs-pmd-usb-serial-interface,
    PMDLogger's PMD_USB_Device.cs device_speed==0 path): raw voltage is a
    signed int16 scaled by 0.01 (V), raw current by 0.1 (A). This is
    CMD_READ_SENSOR_VALUES's plain scaling, not CMD_READ_ADC's raw 12-bit
    ADC path (which needs a per-channel calibration offset this library
    doesn't read).

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
