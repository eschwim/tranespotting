# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TraneSpotting**: Reverse engineering tools for the Trane ComfortLink II protocol (based on Honeywell EnviraCOM 2.0) used in residential HVAC systems. Goal: enable custom thermostats (Home Assistant) to communicate with Trane communicating furnaces and heat pumps.

## Commands

```bash
# Install
pip install -e .              # Base install
pip install -e ".[dev]"       # With pytest, ruff
pip install -e ".[analysis]"  # With pandas, matplotlib
pip install -e ".[hardware]"  # With skidl for circuit generation

# Run tools
python -m tools.capture -p /dev/ttyUSB0 -b 19200      # Capture RS-485 traffic
python -m tools.analyze captures/raw/capture_*.bin    # Analyze packets
python -m tools.baudrate_detect -p /dev/ttyUSB0       # Auto-detect baud rate
python -m tools.signal_analyze capture.csv            # Classify physical layer

# Hardware design (EnviraCOM interface circuit)
python -m tools.hardware.enviracom_interface --svg    # Generate SVG schematic
python -m tools.hardware.enviracom_interface --netlist # Generate KiCad netlist

# Tests
pytest                        # Run all tests
pytest tests/test_packet.py   # Single test file
pytest -k "test_packet"       # By name pattern

# Lint
ruff check tools/ tests/
ruff format tools/ tests/
```

## Architecture

### Two Physical Layers

The protocol can use either:
1. **Native EnviraCOM**: 3-wire bus, 120 baud, modulated 24VAC, requires custom hardware
2. **RS-485**: Standard differential signaling, 9600-38400 baud, USB adapter works

Tools in this repo primarily target RS-485. EnviraCOM requires the discontinued W8735A adapter or custom circuitry.

### Core Components

- **`tools/packet.py`**: `Packet` dataclass for parsing. Header structure is tentative (10-byte header, 0-240 byte payload, 2-byte checksum). Checksum algorithm is unknown - `_verify_checksum()` currently returns True.

- **`tools/capture.py`**: Serial capture with gap-based packet framing (50ms timeout). Writes binary format: `[8-byte timestamp][4-byte length][data]`.

- **`tools/analyze.py`**: Loads captures, extracts address/message type statistics, finds repeating patterns.

- **`tools/hardware/enviracom_interface.py`**: SKiDL circuit definition for DIY EnviraCOM interface. Generates SVG schematics and KiCad netlists for PCB fabrication.

### Key Protocol Details

- EnviraCOM message format: `[Priority]_[MsgType]_[Instance]_[OpType]_[Length]_[Payload]_[Checksum]`
- Known message types: 10E0 (Node ID), 3E70 (Device Status), etc.
- Device discovery uses Node Identification 1 (10E0) broadcast

### Data Flow

```
HVAC Bus → capture.py → captures/raw/*.bin → analyze.py → statistics/patterns
```

## Status

Protocol reverse engineering is in early stages. Packet field assignments in `packet.py` are guesses based on similar protocols (Net485, Carrier Infinity). Update as real captures reveal the actual structure.
