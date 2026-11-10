"""
Wire-format structures and command enum for ElmorLabs PMD2/PMD2X devices.
"""

from ctypes import Structure, c_uint8, c_int16, c_int32, c_uint16
from enum import IntEnum

# Vendor/product identification
VENDOR_ID = 0xEE
PMD2_PRODUCT_ID = 0x15
PMD2X_PRODUCT_ID = 0x17

PMD2_PRODUCT_STRING = "ElmorLabs PMD2"
PMD2X_PRODUCT_STRING = "ElmorLabs PMD2X"

PMD2_SENSOR_POWER_NUM = 10
PMD2X_SENSOR_POWER_NUM = 16
PMD2X_SENSOR_TS_NUM = 2


class PMD_CMD(IntEnum):
    """USB_CMD, per PMD2-FW's pmd2.h (https://github.com/ElmorLabs/PMD2-FW/blob/pmd2x/Core/Inc/pmd2.h).

    CMD_READ_DEVICE_DATA is declared there but has no case in the device's
    CDC_Receive_FS dispatch (usbd_cdc_if.c) -- sending it is a no-op.
    """

    CMD_WELCOME = 0
    CMD_READ_VENDOR_DATA = 1
    CMD_READ_UID = 2
    CMD_READ_DEVICE_DATA = 3
    CMD_READ_SENSOR_VALUES = 4
    CMD_WRITE_CONT_TX = 5
    CMD_READ_CONFIG = 6
    CMD_WRITE_CONFIG = 7
    CMD_RESET = 0xF0
    CMD_BOOTLOADER = 0xF1
    CMD_MCU_CMD = 0xF2
    CMD_NOP = 0xFF

    def toByte(self) -> bytes:
        return self.value.to_bytes(1, byteorder="little")


PMD2X_TS_IN = 0   # 12VHPWR connector temperature sensor, cable side
PMD2X_TS_OUT = 1  # 12VHPWR connector temperature sensor, PSU/device side
PMD2X_TS_NOT_CONNECTED = 0x7FFF


class VendorDataStruct(Structure):
    _pack_ = 1
    _fields_ = [
        ("VendorId", c_uint8),
        ("ProductId", c_uint8),
        ("FwVersion", c_uint8),
    ]

    def __str__(self):
        return (
            f"VendorId: {hex(self.VendorId)}, "
            f"ProductId: {hex(self.ProductId)}, "
            f"FwVersion: {hex(self.FwVersion)}"
        )


class PowerSensor(Structure):
    _pack_ = 1
    _fields_ = [
        ("Voltage", c_int16),
        ("Current", c_int32),
        ("Power", c_int32),
    ]

    def __str__(self):
        return f"Voltage: {self.Voltage}, Current: {self.Current}, Power: {self.Power}"


class SensorStructPMD2(Structure):
    _pack_ = 1
    _fields_ = [
        ("Vdd", c_uint16),
        ("Tchip", c_int16),
        ("PowerReadings", PowerSensor * PMD2_SENSOR_POWER_NUM),
        ("EpsPower", c_uint16),
        ("PciePower", c_uint16),
        ("MbPower", c_uint16),
        ("TotalPower", c_uint16),
        ("Ocp", c_uint8 * PMD2_SENSOR_POWER_NUM),
    ]


class SensorStructPMD2X(Structure):
    _pack_ = 1
    _fields_ = [
        ("Vdd", c_uint16),
        ("Tchip", c_int16),
        ("Ts", c_int16 * PMD2X_SENSOR_TS_NUM),
        ("PowerReadings", PowerSensor * PMD2X_SENSOR_POWER_NUM),
        ("EpsPower", c_uint16),
        ("PciePower", c_uint16),
        ("MbPower", c_uint16),
        ("TotalPower", c_uint16),
        ("Ocp", c_uint8 * PMD2X_SENSOR_POWER_NUM),
    ]
