"""
Wire-format structures and command enum for the ElmorLabs PMD-USB.

PMD-USB is a different device family from PMD2/PMD2X: it connects via a
CH340 USB-serial bridge rather than an STM32 CDC-ACM VCP, and uses its own
command numbering and sensor layout (PCIE1/PCIE2/EPS1/EPS2 only -- no ATX24
rails, no 12VHPWR). See the reference implementations this was ported from:
https://github.com/ElmorLabs/pmd-usb-serial-interface-fast
https://github.com/ElmorLabs/PMDLogger
"""

from ctypes import Structure, c_uint8, c_int16
from enum import IntEnum

PMDUSB_VENDOR_ID = 0xEE
PMDUSB_PRODUCT_ID = 0x0A

PMDUSB_PRODUCT_STRING = "ElmorLabs PMD-USB"

PMDUSB_CHANNEL_NUM = 4


class PMDUSB_CMD(IntEnum):
    """UART_CMD, per PMDLogger's PMD_USB_Device.cs."""

    CMD_WELCOME = 0
    CMD_READ_ID = 1
    CMD_READ_SENSORS = 2
    CMD_READ_SENSOR_VALUES = 3
    CMD_READ_CONFIG = 4
    CMD_WRITE_CONFIG = 5
    CMD_READ_ADC = 6
    CMD_WRITE_CONFIG_CONT_TX = 7
    CMD_WRITE_CONFIG_UART = 8
    CMD_RESET = 0xF0
    CMD_BOOTLOADER = 0xF1
    CMD_NOP = 0xFF

    def toByte(self) -> bytes:
        return self.value.to_bytes(1, byteorder="little")


class PMDUSBIdStruct(Structure):
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


class PMDUSBChannelValues(Structure):
    _pack_ = 1
    _fields_ = [
        ("Voltage", c_int16),
        ("Current", c_int16),
    ]


class SensorValuesPMDUSB(Structure):
    """CMD_READ_SENSOR_VALUES reply: 4 channels x {Voltage, Current}, 16 bytes total.

    Voltage is raw*0.01 V, current is raw*0.1 A -- plain signed int16, no
    calibration offset or bit-shift (that's CMD_READ_ADC's raw-ADC path,
    not implemented here).
    """

    _pack_ = 1
    _fields_ = [
        ("Channels", PMDUSBChannelValues * PMDUSB_CHANNEL_NUM),
    ]


# Channel index -> rail name, per PMDLogger's PMD_USB_Device constructor and
# bjorntas's elmorlabs-pmd-usb-serial-interface main.py.
PMDUSB_CHANNELS = {
    0: "PCIE1",
    1: "PCIE2",
    2: "EPS1",
    3: "EPS2",
}
