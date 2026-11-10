"""
Translate raw PMD2/PMD2X sensor structures into human-readable rail readings.
"""

from typing import Dict, List, Union

from pmd2_pycore.core.structures import (
    SensorStructPMD2,
    SensorStructPMD2X,
    PMD2_PRODUCT_ID,
)

# Channel index -> rail name, for each product.
PMD2_CHANNELS = {
    0: "12V", 1: "5V", 2: "5VSB", 3: "3.3V",
    4: "HPWR",
    5: "EPS1", 6: "EPS2",
    7: "PCIE1", 8: "PCIE2", 9: "PCIE3",
}

PMD2X_CHANNELS = {
    0: "12V", 1: "5V", 2: "5VSB", 3: "3.3V",
    5: "EPS1", 6: "EPS2",
    7: "PCIE1", 8: "PCIE2", 9: "PCIE3",
    10: "HPWR_W1", 11: "HPWR_W2", 12: "HPWR_W3",
    13: "HPWR_W4", 14: "HPWR_W5", 15: "HPWR_W6",
}

# PMD2X has no single HPWR channel; it's the average of the six 12V-2x6 wire pairs.
PMD2X_HPWR_WIRE_CHANNELS = [10, 11, 12, 13, 14, 15]


def _reading(voltage: int, current: int, power: int) -> Dict[str, float]:
    return {"voltage": voltage / 1000, "current": current / 1000, "power": power / 1000}


def translate_sensor_struct(
    sensors: Union[SensorStructPMD2, SensorStructPMD2X],
    product_id: int,
) -> Dict[str, Dict[str, float]]:
    """Convert a raw sensor struct into a dict of rail name -> {voltage, current, power} (SI units).

    Args:
        sensors: Decoded sensor struct from read_sensors().
        product_id: PMD2_PRODUCT_ID or PMD2X_PRODUCT_ID.

    Returns:
        Dict[str, Dict[str, float]]: Rail name -> reading. PMD2X additionally
            gets a synthetic "HPWR" entry averaged from its six wire channels.
    """
    channels = PMD2_CHANNELS if product_id == PMD2_PRODUCT_ID else PMD2X_CHANNELS
    readings = sensors.PowerReadings

    result = {
        name: _reading(readings[idx].Voltage, readings[idx].Current, readings[idx].Power)
        for idx, name in channels.items()
    }

    if product_id != PMD2_PRODUCT_ID:
        n = len(PMD2X_HPWR_WIRE_CHANNELS)
        voltage = sum(readings[i].Voltage for i in PMD2X_HPWR_WIRE_CHANNELS) / n
        current = sum(readings[i].Current for i in PMD2X_HPWR_WIRE_CHANNELS) / n
        power = sum(readings[i].Power for i in PMD2X_HPWR_WIRE_CHANNELS) / n
        result["HPWR"] = _reading(voltage, current, power)

    return result
