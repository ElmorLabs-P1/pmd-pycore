# ElmorLabs PMD2/PMD2X Python sample code

More information: https://elmorlabs.com/product/elmorlabs-pmd2x-power-measurement-device-2x

## Pre-requisites
- Python 3.13 with pyserial, numpy and matplotlib

## Status

This repository is under active development at
[ElmorLabs-P1/pmd-pycore](https://github.com/ElmorLabs-P1/pmd-pycore). It contains a single
sample script, `pmd2-msm.py`, which connects to a PMD2 or PMD2X device over serial, polls sensor
values, and prints averaged voltage/current/power readings per rail to the console.

There is no packaging, test suite, or CLI argument handling yet — the script is run directly
and prompts for a serial port selection if multiple matching devices are found.

## Related repositories

- [PMD2-FW (pmd2x branch)](https://github.com/ElmorLabs/PMD2-FW/tree/pmd2x) — PMD2X firmware,
  useful reference for the UART command set and sensor data structures used here.
