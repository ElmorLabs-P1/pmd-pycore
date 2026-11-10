# pmd_pycore/core/__init__.py

from .serial_io import (
    get_pmd_ports,
    find_pmd_devices,
    read_uart,
    read_welcome_string,
    read_device,
    read_uid,
    read_sensors,
)
from .sensor_translation import (
    translate_sensor_struct,
    translate_aggregate_power,
    translate_chip_sensors,
    translate_hpwr_temperatures,
    PMD2_CHANNELS,
    PMD2X_CHANNELS,
)
from .structures import (
    VendorDataStruct,
    PowerSensor,
    SensorStructPMD2,
    SensorStructPMD2X,
    PMD_CMD,
    VENDOR_ID,
    PMD2_PRODUCT_ID,
    PMD2X_PRODUCT_ID,
    PMD2_PRODUCT_STRING,
    PMD2X_PRODUCT_STRING,
    PMD2_SENSOR_POWER_NUM,
    PMD2X_SENSOR_POWER_NUM,
    PMD2X_SENSOR_TS_NUM,
    PMD2X_TS_IN,
    PMD2X_TS_OUT,
    PMD2X_TS_NOT_CONNECTED,
)
from .pmdusb_serial_io import (
    get_pmdusb_ports,
    read_pmdusb_uart,
    read_pmdusb_welcome_string,
    read_pmdusb_id,
    read_pmdusb_sensors,
)
from .pmdusb_sensor_translation import translate_pmdusb_sensors
from .pmdusb_structures import (
    PMDUSBIdStruct,
    PMDUSBChannelValues,
    SensorValuesPMDUSB,
    PMDUSB_CMD,
    PMDUSB_VENDOR_ID,
    PMDUSB_PRODUCT_ID,
    PMDUSB_PRODUCT_STRING,
    PMDUSB_CHANNEL_NUM,
    PMDUSB_CHANNELS,
)

__all__ = [
    # serial_io
    "get_pmd_ports",
    "find_pmd_devices",
    "read_uart",
    "read_welcome_string",
    "read_device",
    "read_uid",
    "read_sensors",
    # sensor_translation
    "translate_sensor_struct",
    "translate_aggregate_power",
    "translate_chip_sensors",
    "translate_hpwr_temperatures",
    "PMD2_CHANNELS",
    "PMD2X_CHANNELS",
    # structures
    "VendorDataStruct",
    "PowerSensor",
    "SensorStructPMD2",
    "SensorStructPMD2X",
    "PMD_CMD",
    "VENDOR_ID",
    "PMD2_PRODUCT_ID",
    "PMD2X_PRODUCT_ID",
    "PMD2_PRODUCT_STRING",
    "PMD2X_PRODUCT_STRING",
    "PMD2_SENSOR_POWER_NUM",
    "PMD2X_SENSOR_POWER_NUM",
    "PMD2X_SENSOR_TS_NUM",
    "PMD2X_TS_IN",
    "PMD2X_TS_OUT",
    "PMD2X_TS_NOT_CONNECTED",
    # pmdusb_serial_io
    "get_pmdusb_ports",
    "read_pmdusb_uart",
    "read_pmdusb_welcome_string",
    "read_pmdusb_id",
    "read_pmdusb_sensors",
    # pmdusb_sensor_translation
    "translate_pmdusb_sensors",
    # pmdusb_structures
    "PMDUSBIdStruct",
    "PMDUSBChannelValues",
    "SensorValuesPMDUSB",
    "PMDUSB_CMD",
    "PMDUSB_VENDOR_ID",
    "PMDUSB_PRODUCT_ID",
    "PMDUSB_PRODUCT_STRING",
    "PMDUSB_CHANNEL_NUM",
    "PMDUSB_CHANNELS",
]
