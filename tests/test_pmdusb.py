# tests/test_pmdusb.py

from ctypes import Structure, sizeof
from unittest.mock import patch, MagicMock, Mock

from pmd_pycore.core import (
    get_pmdusb_ports,
    read_pmdusb_uart,
    read_pmdusb_welcome_string,
    read_pmdusb_id,
    read_pmdusb_sensors,
    translate_pmdusb_sensors,
    PMDUSBIdStruct,
    SensorValuesPMDUSB,
    PMDUSB_CMD,
    PMDUSB_VENDOR_ID,
    PMDUSB_PRODUCT_ID,
)


def test_imports():
    assert callable(get_pmdusb_ports)
    assert callable(read_pmdusb_uart)
    assert callable(read_pmdusb_welcome_string)
    assert callable(read_pmdusb_id)
    assert callable(read_pmdusb_sensors)
    assert callable(translate_pmdusb_sensors)

    assert isinstance(PMDUSBIdStruct(), Structure)
    assert isinstance(SensorValuesPMDUSB(), Structure)


@patch("pmd_pycore.core.pmdusb_serial_io.serial.tools.list_ports.comports")
def test_get_pmdusb_ports_filters_by_vid_pid(mock_comports):
    match = Mock(device="COM22", hwid="USB VID:PID=1A86:7523 SER=1")
    no_match = Mock(device="COM4", hwid="USB VID:PID=0483:5740 SER=2")
    mock_comports.return_value = [match, no_match]

    ports = get_pmdusb_ports()

    assert ports == [{"port": "COM22"}]


def test_read_pmdusb_welcome_string():
    ser = MagicMock()
    ser.read.return_value = b"ElmorLabs PMD-USB"

    assert read_pmdusb_welcome_string(ser) == "ElmorLabs PMD-USB"


def test_read_pmdusb_id():
    id_struct = PMDUSBIdStruct(VendorId=PMDUSB_VENDOR_ID, ProductId=PMDUSB_PRODUCT_ID, FwVersion=6)
    ser = MagicMock()
    ser.read.return_value = bytes(id_struct)

    info = read_pmdusb_id(ser)

    assert info == {"VendorId": PMDUSB_VENDOR_ID, "ProductId": PMDUSB_PRODUCT_ID, "FwVersion": 6}


def test_read_pmdusb_id_wrong_vendor_returns_none():
    id_struct = PMDUSBIdStruct(VendorId=0x00, ProductId=PMDUSB_PRODUCT_ID, FwVersion=6)
    ser = MagicMock()
    ser.read.return_value = bytes(id_struct)

    assert read_pmdusb_id(ser) is None


def test_read_pmdusb_sensors():
    sensors = SensorValuesPMDUSB()
    sensors.Channels[0].Voltage = 1200
    sensors.Channels[0].Current = 50
    ser = MagicMock()
    ser.read.return_value = bytes(sensors)

    result = read_pmdusb_sensors(ser)

    assert isinstance(result, SensorValuesPMDUSB)
    assert result.Channels[0].Voltage == 1200


def test_read_pmdusb_sensors_incomplete_returns_none():
    ser = MagicMock()
    ser.read.return_value = b"\x01\x02"

    assert read_pmdusb_sensors(ser) is None


def test_translate_pmdusb_sensors():
    sensors = SensorValuesPMDUSB()
    sensors.Channels[0].Voltage = 1200  # 12.00 V
    sensors.Channels[0].Current = 50   # 5.0 A

    result = translate_pmdusb_sensors(sensors)

    assert result["PCIE1"] == {"voltage": 12.0, "current": 5.0, "power": 60.0}
    assert set(result.keys()) == {"PCIE1", "PCIE2", "EPS1", "EPS2"}
