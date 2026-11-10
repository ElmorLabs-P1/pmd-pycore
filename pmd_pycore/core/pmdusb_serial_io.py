"""
Serial communication helpers for the ElmorLabs PMD-USB.

Example:
    >>> from pmd_pycore.core import get_pmdusb_ports, read_pmdusb_id, read_pmdusb_sensors
    >>> ports = get_pmdusb_ports()
    >>> if ports:
    >>>     import serial
    >>>     ser = serial.Serial(ports[0]['port'], 115200, timeout=1)
    >>>     info = read_pmdusb_id(ser)
    >>>     sensors = read_pmdusb_sensors(ser)
    >>>     ser.close()
"""

import os
import sys
import time
import logging
import serial
import serial.tools.list_ports
from ctypes import sizeof
from typing import List, Dict, Optional

from pmd_pycore.core.pmdusb_structures import (
    PMDUSBIdStruct,
    SensorValuesPMDUSB,
    PMDUSB_CMD,
    PMDUSB_VENDOR_ID,
    PMDUSB_PRODUCT_ID,
    PMDUSB_PRODUCT_STRING,
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("pmd_pycore.core.pmdusb_serial_io")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# PMD-USB uses a CH340 USB-serial bridge, not the STM32 VCP that PMD2/PMD2X
# use -- a different VID:PID entirely.
_PMDUSB_VID_PID = "VID:PID=1A86:7523"

_WELCOME_REPLY_LEN = len(PMDUSB_PRODUCT_STRING)


# --- Serial port helpers ---

def get_pmdusb_ports() -> List[Dict[str, str]]:
    """Return all candidate PMD-USB COM ports without opening them.

    Returns:
        List[Dict[str, str]]: List of dicts with a 'port' key, e.g. [{'port': 'COM3'}].
    """
    try:
        ports = serial.tools.list_ports.comports()
    except serial.SerialException as e:
        logger.error("Failed to enumerate serial ports: %s", e)
        raise

    pmdusb_ports = []
    for p in ports:
        if _PMDUSB_VID_PID in p.hwid.upper():
            pmdusb_ports.append({"port": p.device})
    return pmdusb_ports


# --- UART helpers ---

def read_pmdusb_uart(ser: serial.Serial, cmd: PMDUSB_CMD, size: int) -> Optional[bytes]:
    """Send a command and read `size` bytes from the device.

    Returns:
        Optional[bytes]: Raw bytes read, or None if the read was incomplete.
    """
    ser.reset_input_buffer()
    ser.write(cmd.toByte())
    # Measured 0/5000 failures at 0ms across 5 trials against a live
    # PMD-USB (its CH340 bridge responds faster than PMD2/PMD2X's STM32
    # CDC-ACM stack did), but a small margin is kept anyway -- that same
    # "0ms looked fine" read on PMD2/PMD2X didn't hold up under more
    # sustained testing, and a cheap sleep costs far less than a stall on
    # the read timeout if it's ever wrong on different hardware.
    time.sleep(0.002)
    buffer = ser.read(size)
    if len(buffer) != size:
        logger.warning("UART read incomplete: expected %d, got %d bytes", size, len(buffer))
        return None
    return buffer


def read_pmdusb_welcome_string(ser: serial.Serial) -> Optional[str]:
    """Send CMD_WELCOME and return the device's product name.

    Returns:
        Optional[str]: Decoded product name, or None if the read failed.
    """
    buffer = read_pmdusb_uart(ser, PMDUSB_CMD.CMD_WELCOME, _WELCOME_REPLY_LEN)
    if buffer is None:
        return None
    try:
        return buffer.decode("ascii").rstrip("\x00")
    except UnicodeDecodeError:
        logger.warning("Failed to decode welcome string: %r", buffer)
        return None


def read_pmdusb_id(ser: serial.Serial) -> Optional[Dict[str, int]]:
    """Read and validate vendor/product/firmware info from the device.

    Returns:
        Optional[Dict[str, int]]: Dict with 'VendorId', 'ProductId', 'FwVersion',
            or None if the read failed or the vendor/product ID didn't match.
    """
    buffer = read_pmdusb_uart(ser, PMDUSB_CMD.CMD_READ_ID, sizeof(PMDUSBIdStruct))
    if buffer is None:
        return None

    id_struct = PMDUSBIdStruct.from_buffer_copy(buffer)
    if id_struct.VendorId != PMDUSB_VENDOR_ID or id_struct.ProductId != PMDUSB_PRODUCT_ID:
        logger.warning("Unexpected vendor data: %s", id_struct)
        return None

    return {
        "VendorId": id_struct.VendorId,
        "ProductId": id_struct.ProductId,
        "FwVersion": id_struct.FwVersion,
    }


def read_pmdusb_sensors(ser: serial.Serial) -> Optional[SensorValuesPMDUSB]:
    """Read all sensor values from the device.

    Returns:
        Optional[SensorValuesPMDUSB]: Decoded sensor structure, or None if the
            read failed.
    """
    buffer = read_pmdusb_uart(ser, PMDUSB_CMD.CMD_READ_SENSOR_VALUES, sizeof(SensorValuesPMDUSB))
    if buffer is None:
        logger.warning("Failed to read sensors from device")
        return None
    return SensorValuesPMDUSB.from_buffer_copy(buffer)
