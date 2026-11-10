"""
Translate raw PMD2/PMD2X sensor structures into human-readable readings.
"""

from typing import Dict, Optional, Union

from pmd2_pycore.core.structures import (
    SensorStructPMD2,
    SensorStructPMD2X,
    PMD2_PRODUCT_ID,
    PMD2X_TS_IN,
    PMD2X_TS_OUT,
    PMD2X_TS_NOT_CONNECTED,
)

# Channel index -> rail name, for each product. Matches SENSOR_POWER_* in
# the PMD2-FW pmd2.h header (https://github.com/ElmorLabs/PMD2-FW/blob/pmd2x/Core/Inc/pmd2.h).
# Index 4 ("HPWR"/"HPWR1") is computed by the firmware itself from the six
# wire channels (10-15) -- it isn't something the host needs to average.
PMD2_CHANNELS = {
    0: "12V", 1: "5V", 2: "5VSB", 3: "3.3V",
    4: "HPWR",
    5: "EPS1", 6: "EPS2",
    7: "PCIE1", 8: "PCIE2", 9: "PCIE3",
}

PMD2X_CHANNELS = {
    0: "12V", 1: "5V", 2: "5VSB", 3: "3.3V",
    4: "HPWR",
    5: "EPS1", 6: "EPS2",
    7: "PCIE1", 8: "PCIE2", 9: "PCIE3",
    10: "HPWR_W1", 11: "HPWR_W2", 12: "HPWR_W3",
    13: "HPWR_W4", 14: "HPWR_W5", 15: "HPWR_W6",
}


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
        Dict[str, Dict[str, float]]: Rail name -> reading.
    """
    channels = PMD2_CHANNELS if product_id == PMD2_PRODUCT_ID else PMD2X_CHANNELS
    readings = sensors.PowerReadings

    return {
        name: _reading(readings[idx].Voltage, readings[idx].Current, readings[idx].Power)
        for idx, name in channels.items()
    }


def translate_aggregate_power(
    sensors: Union[SensorStructPMD2, SensorStructPMD2X],
) -> Dict[str, float]:
    """Read the firmware-computed power aggregates, in watts.

    The device sums these on-board rather than requiring the host to add up
    individual rails:
        - eps: EPS/CPU power (EPS1 + EPS2)
        - pcie: PCIe/GPU power (PCIE1-3, plus HPWR on PMD2X)
        - mb: motherboard power (ATX24 rails: 12V/5V/5VSB/3.3V)
        - total: sum of all of the above
    """
    return {
        "eps": sensors.EpsPower / 1000,
        "pcie": sensors.PciePower / 1000,
        "mb": sensors.MbPower / 1000,
        "total": sensors.TotalPower / 1000,
    }


def translate_chip_sensors(sensors: Union[SensorStructPMD2, SensorStructPMD2X]) -> Dict[str, float]:
    """Read the device's own supply voltage and chip temperature.

    Tchip is in tenths of a degree C, per sensor.c's TH_GetTs()/
    __LL_ADC_CALC_TEMPERATURE() usage -- confirmed against a live device
    (raw 320 read back as a plausible 32.0 C, not 320 C).

    Returns:
        Dict[str, float]: 'vdd' in volts, 'tchip' in degrees Celsius.
    """
    return {"vdd": sensors.Vdd / 1000, "tchip": sensors.Tchip / 10}


def translate_hpwr_temperatures(sensors: SensorStructPMD2X) -> Dict[str, Optional[float]]:
    """Read the 12VHPWR connector's two thermistor temperatures (PMD2X only), in Celsius.

    Ts[] comes from TH_GetTs() (see PMD2-FW's th.c/th_lut.h), which is also
    in tenths of a degree C. 0x7FFF means the thermistor read out of range,
    i.e. nothing is plugged in.

    Returns:
        Dict[str, Optional[float]]: 'ts_in' and 'ts_out'; either is None if
            that thermistor is not connected.
    """
    def _value(raw: int) -> Optional[float]:
        return None if raw == PMD2X_TS_NOT_CONNECTED else raw / 10

    return {
        "ts_in": _value(sensors.Ts[PMD2X_TS_IN]),
        "ts_out": _value(sensors.Ts[PMD2X_TS_OUT]),
    }
