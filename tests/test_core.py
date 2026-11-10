# tests/test_core.py

from ctypes import Structure, sizeof
from unittest.mock import patch, MagicMock, Mock

from pmd2_pycore.core import (
    get_pmd_ports,
    find_pmd_devices,
    read_uart,
    read_welcome_string,
    read_device,
    read_uid,
    read_sensors,
    translate_sensor_struct,
    translate_aggregate_power,
    translate_chip_sensors,
    translate_hpwr_temperatures,
    VendorDataStruct,
    PowerSensor,
    SensorStructPMD2,
    SensorStructPMD2X,
    PMD_CMD,
    VENDOR_ID,
    PMD2_PRODUCT_ID,
    PMD2X_PRODUCT_ID,
    PMD2X_TS_IN,
    PMD2X_TS_OUT,
    PMD2X_TS_NOT_CONNECTED,
)


# -----------------------
# Test core imports
# -----------------------
def test_imports():
    assert callable(get_pmd_ports)
    assert callable(find_pmd_devices)
    assert callable(read_uart)
    assert callable(read_welcome_string)
    assert callable(read_device)
    assert callable(read_uid)
    assert callable(read_sensors)
    assert callable(translate_sensor_struct)
    assert callable(translate_aggregate_power)
    assert callable(translate_chip_sensors)
    assert callable(translate_hpwr_temperatures)

    assert isinstance(VendorDataStruct(), Structure)
    assert isinstance(PowerSensor(), Structure)
    assert isinstance(SensorStructPMD2(), Structure)
    assert isinstance(SensorStructPMD2X(), Structure)


# -----------------------
# Test device discovery
# -----------------------
@patch("pmd2_pycore.core.serial_io.serial.tools.list_ports.comports")
def test_get_pmd_ports_filters_by_vid_pid(mock_comports):
    match = Mock(device="COM3", hwid="USB VID:PID=0483:5740 SER=1")
    no_match = Mock(device="COM4", hwid="USB VID:PID=1234:5678 SER=2")
    mock_comports.return_value = [match, no_match]

    ports = get_pmd_ports()

    assert ports == [{"port": "COM3"}]


@patch("pmd2_pycore.core.serial_io.serial.tools.list_ports.comports")
def test_get_pmd_ports_empty(mock_comports):
    mock_comports.return_value = []
    assert get_pmd_ports() == []


# -----------------------
# Test read_uart
# -----------------------
def test_read_uart_success():
    ser = MagicMock()
    ser.read.return_value = b"\x01\x02\x03"

    result = read_uart(ser, PMD_CMD.CMD_READ_VENDOR_DATA, 3)

    assert result == b"\x01\x02\x03"
    ser.write.assert_called_once_with(PMD_CMD.CMD_READ_VENDOR_DATA.toByte())


def test_read_uart_incomplete_returns_none():
    ser = MagicMock()
    ser.read.return_value = b"\x01"

    result = read_uart(ser, PMD_CMD.CMD_READ_VENDOR_DATA, 3)

    assert result is None


# -----------------------
# Test read_device
# -----------------------
def test_read_device_pmd2x():
    vendor_struct = VendorDataStruct(VendorId=VENDOR_ID, ProductId=PMD2X_PRODUCT_ID, FwVersion=0)
    ser = MagicMock()
    ser.read.return_value = bytes(vendor_struct)

    info = read_device(ser)

    assert info == {"VendorId": VENDOR_ID, "ProductId": PMD2X_PRODUCT_ID, "FwVersion": 0}


def test_read_device_wrong_vendor_returns_none():
    vendor_struct = VendorDataStruct(VendorId=0x00, ProductId=PMD2X_PRODUCT_ID, FwVersion=0)
    ser = MagicMock()
    ser.read.return_value = bytes(vendor_struct)

    assert read_device(ser) is None


# -----------------------
# Test read_welcome_string
# -----------------------
def test_read_welcome_string():
    ser = MagicMock()
    ser.read.return_value = b"ElmorLabs PMD2X"

    assert read_welcome_string(ser) == "ElmorLabs PMD2X"


def test_read_welcome_string_incomplete_returns_none():
    ser = MagicMock()
    ser.read.return_value = b"short"

    assert read_welcome_string(ser) is None


# -----------------------
# Test read_uid
# -----------------------
def test_read_uid():
    ser = MagicMock()
    ser.read.return_value = bytes.fromhex("32001e000c53545637303120")

    assert read_uid(ser) == "32001E000C53545637303120"


def test_read_uid_incomplete_returns_none():
    ser = MagicMock()
    ser.read.return_value = b"\x01\x02"

    assert read_uid(ser) is None


# -----------------------
# Test read_sensors
# -----------------------
def test_read_sensors_pmd2x_selects_correct_struct():
    sensors = SensorStructPMD2X()
    ser = MagicMock()
    ser.read.return_value = bytes(sensors)

    result = read_sensors(ser, PMD2X_PRODUCT_ID)

    assert isinstance(result, SensorStructPMD2X)


def test_read_sensors_pmd2_selects_correct_struct():
    sensors = SensorStructPMD2()
    ser = MagicMock()
    ser.read.return_value = bytes(sensors)

    result = read_sensors(ser, PMD2_PRODUCT_ID)

    assert isinstance(result, SensorStructPMD2)


def test_read_sensors_incomplete_returns_none():
    ser = MagicMock()
    ser.read.return_value = b""

    assert read_sensors(ser, PMD2X_PRODUCT_ID) is None


# -----------------------
# Test sensor translation
# -----------------------
def test_translate_sensor_struct_pmd2():
    sensors = SensorStructPMD2()
    sensors.PowerReadings[0].Voltage = 12000
    sensors.PowerReadings[0].Current = 1000
    sensors.PowerReadings[0].Power = 12000

    result = translate_sensor_struct(sensors, PMD2_PRODUCT_ID)

    assert result["12V"] == {"voltage": 12.0, "current": 1.0, "power": 12.0}
    assert "HPWR_W1" not in result


def test_translate_sensor_struct_pmd2x_reads_hpwr_and_wires():
    sensors = SensorStructPMD2X()
    # HPWR1 (index 4) is computed on-device from the six wires -- the host
    # reads it directly rather than re-deriving it from the wire channels.
    sensors.PowerReadings[4].Voltage = 12000
    sensors.PowerReadings[4].Current = 3000
    sensors.PowerReadings[4].Power = 36000
    sensors.PowerReadings[10].Voltage = 12000
    sensors.PowerReadings[10].Current = 500
    sensors.PowerReadings[10].Power = 6000

    result = translate_sensor_struct(sensors, PMD2X_PRODUCT_ID)

    assert result["HPWR"] == {"voltage": 12.0, "current": 3.0, "power": 36.0}
    assert result["HPWR_W1"] == {"voltage": 12.0, "current": 0.5, "power": 6.0}


def test_translate_aggregate_power():
    sensors = SensorStructPMD2X()
    sensors.EpsPower = 50000
    sensors.PciePower = 30000
    sensors.MbPower = 20000
    sensors.TotalPower = 60000

    result = translate_aggregate_power(sensors)

    assert result == {"eps": 50.0, "pcie": 30.0, "mb": 20.0, "total": 60.0}


def test_translate_chip_sensors():
    sensors = SensorStructPMD2X()
    sensors.Vdd = 3300
    sensors.Tchip = 420  # tenths of a degree -> 42.0 C

    result = translate_chip_sensors(sensors)

    assert result == {"vdd": 3.3, "tchip": 42.0}


def test_translate_hpwr_temperatures():
    sensors = SensorStructPMD2X()
    sensors.Ts[PMD2X_TS_IN] = 350  # tenths of a degree -> 35.0 C
    sensors.Ts[PMD2X_TS_OUT] = PMD2X_TS_NOT_CONNECTED

    result = translate_hpwr_temperatures(sensors)

    assert result == {"ts_in": 35.0, "ts_out": None}
