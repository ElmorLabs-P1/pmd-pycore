"""
Serial communication helpers for ElmorLabs PMD2/PMD2X devices.

Example:
    >>> from pmd2_pycore.core import get_pmd_ports, read_device, read_sensors
    >>> ports = get_pmd_ports()
    >>> if ports:
    >>>     import serial
    >>>     ser = serial.Serial(ports[0]['port'], 115200, timeout=1,
    >>>                          rtscts=False, dsrdtr=False)
    >>>     info = read_device(ser)
    >>>     sensors = read_sensors(ser, info['ProductId'])
    >>>     ser.close()
"""

import os
import sys
import time
import logging
import serial
import serial.tools.list_ports
from ctypes import sizeof
from typing import List, Dict, Optional, Union

from pmd2_pycore.core.structures import (
    VendorDataStruct,
    SensorStructPMD2,
    SensorStructPMD2X,
    PMD_CMD,
    VENDOR_ID,
    PMD2_PRODUCT_ID,
    PMD2X_PRODUCT_ID,
    PMD2_PRODUCT_STRING,
    PMD2X_PRODUCT_STRING,
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("pmd2_pycore.core.serial_io")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# VID:PID shared by PMD2 and PMD2X (checked case-insensitively).
_PMD_VID_PID = "VID:PID=0483:5740"

# Longest welcome string a device can push on connect.
_WELCOME_PUSH_MAX_LEN = max(len(PMD2_PRODUCT_STRING), len(PMD2X_PRODUCT_STRING)) + 1

# CMD_WELCOME replies with BuildData.ProductName truncated to 15 bytes
# (CDC_Transmit_FS((void*)BuildData.ProductName, 15) in usbd_cdc_if.c) --
# a fixed size independent of the unsolicited DTR-triggered push above.
_WELCOME_REPLY_LEN = 15

_UID_LEN = 12


# --- Serial port helpers ---

def get_pmd_ports() -> List[Dict[str, str]]:
    """Return all candidate PMD2/PMD2X COM ports without opening them.

    Returns:
        List[Dict[str, str]]: List of dicts with a 'port' key, e.g. [{'port': 'COM3'}].
    """
    try:
        ports = serial.tools.list_ports.comports()
    except serial.SerialException as e:
        logger.error("Failed to enumerate serial ports: %s", e)
        raise

    pmd_ports = []
    for p in ports:
        if _PMD_VID_PID in p.hwid.upper():
            pmd_ports.append({"port": p.device})
    return pmd_ports


def _drain_welcome_push(ser: serial.Serial) -> Optional[str]:
    """Read and decode the unsolicited welcome string a device pushes after DTR is asserted."""
    buffer = ser.read(_WELCOME_PUSH_MAX_LEN)
    try:
        return buffer.decode("ascii").rstrip("\x00")
    except UnicodeDecodeError:
        return None


def find_pmd_devices() -> List[Dict[str, str]]:
    """Scan and return all connected PMD2/PMD2X devices with identity info.

    Returns:
        List[Dict[str, str]]: List of dicts with 'port', 'product_id', 'fw' keys.

    Note:
        This opens and closes a serial connection per candidate port.
    """
    devices = []
    for port_info in get_pmd_ports():
        port = port_info["port"]
        product_id, fw = "?", "?"
        try:
            with serial.Serial(port, 115200, timeout=1, rtscts=False, dsrdtr=False) as ser:
                ser.dtr = True
                _drain_welcome_push(ser)
                device_info = read_device(ser)
                if device_info:
                    product_id = device_info["ProductId"]
                    fw = device_info["FwVersion"]
            logger.info("Found device on %s: ProductId=%s, FW=%s", port, product_id, fw)
        except serial.SerialException as e:
            logger.warning("Failed to open serial port %s: %s", port, e)
        except Exception as e:
            logger.warning("Failed to read device on %s: %s", port, e)
        devices.append({"port": port, "product_id": product_id, "fw": fw})
    return devices


# --- UART helpers ---

def read_uart(ser: serial.Serial, cmd: PMD_CMD, size: int) -> Optional[bytes]:
    """Send a command and read `size` bytes from the device.

    Returns:
        Optional[bytes]: Raw bytes read, or None if the read was incomplete.
    """
    ser.reset_input_buffer()
    ser.write(cmd.toByte())
    # Without a short gap the device occasionally hasn't queued its response
    # yet when we read. 2ms was 0/5000 on a PMD2X but 2-3% failures on a
    # PMD2 (different unit/firmware); 5ms was 0/5000 on both -- cheap
    # insurance against a read that otherwise blocks for the full port
    # timeout before coming back empty.
    time.sleep(0.005)
    buffer = ser.read(size)
    if len(buffer) != size:
        logger.warning("UART read incomplete: expected %d, got %d bytes", size, len(buffer))
        return None
    return buffer


def read_device(ser: serial.Serial) -> Optional[Dict[str, int]]:
    """Read and validate vendor/product/firmware info from the device.

    Returns:
        Optional[Dict[str, int]]: Dict with 'VendorId', 'ProductId', 'FwVersion',
            or None if the read failed or the vendor ID didn't match.
    """
    buffer = read_uart(ser, PMD_CMD.CMD_READ_VENDOR_DATA, sizeof(VendorDataStruct))
    if buffer is None:
        return None

    vendor_struct = VendorDataStruct.from_buffer_copy(buffer)
    if vendor_struct.VendorId != VENDOR_ID or vendor_struct.ProductId not in (
        PMD2_PRODUCT_ID,
        PMD2X_PRODUCT_ID,
    ):
        logger.warning("Unexpected vendor data: %s", vendor_struct)
        return None

    return {
        "VendorId": vendor_struct.VendorId,
        "ProductId": vendor_struct.ProductId,
        "FwVersion": vendor_struct.FwVersion,
    }


def read_welcome_string(ser: serial.Serial) -> Optional[str]:
    """Send CMD_WELCOME and return the device's product name.

    Returns:
        Optional[str]: Decoded product name, or None if the read failed.
    """
    buffer = read_uart(ser, PMD_CMD.CMD_WELCOME, _WELCOME_REPLY_LEN)
    if buffer is None:
        return None
    try:
        return buffer.decode("ascii").rstrip("\x00")
    except UnicodeDecodeError:
        logger.warning("Failed to decode welcome string: %r", buffer)
        return None


def read_uid(ser: serial.Serial) -> Optional[str]:
    """Read the device's unique ID (the STM32's hardware UID).

    Returns:
        Optional[str]: UID as an uppercase hex string, or None if the read failed.
    """
    buffer = read_uart(ser, PMD_CMD.CMD_READ_UID, _UID_LEN)
    if buffer is None:
        return None
    return buffer.hex().upper()


def read_sensors(
    ser: serial.Serial,
    product_id: int,
) -> Optional[Union[SensorStructPMD2, SensorStructPMD2X]]:
    """Read all sensor values from the device.

    Args:
        ser (serial.Serial): Opened serial connection to the device.
        product_id (int): PMD2_PRODUCT_ID or PMD2X_PRODUCT_ID, selecting which
            sensor structure to decode the response as.

    Returns:
        Optional[Union[SensorStructPMD2, SensorStructPMD2X]]: Decoded sensor
            structure, or None if the read failed.
    """
    struct_type = SensorStructPMD2X if product_id == PMD2X_PRODUCT_ID else SensorStructPMD2
    buffer = read_uart(ser, PMD_CMD.CMD_READ_SENSOR_VALUES, sizeof(struct_type))
    if buffer is None:
        logger.warning("Failed to read sensors from device")
        return None
    return struct_type.from_buffer_copy(buffer)
