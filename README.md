# TraneSpotting

Reverse engineering tools for the Trane ComfortLink II protocol used in residential HVAC systems.

## Goal

Enable custom thermostats (Home Assistant, etc.) to communicate with
Trane ComfortLink II compatible equipment:
- Trane/American Standard communicating furnaces (SV92, etc.)
- Trane/American Standard communicating heat pumps (XV19, etc.)
- Via BAY24VRPAC52DC relay panel

## Protocol Background

**ComfortLink II is based on Honeywell EnviraCOM 2.0 protocol.**

The XL850/XL950/XL1050 thermostats are manufactured by Honeywell for Trane.
This is significant because it means existing EnviraCOM documentation and
tools may be applicable.

### Two Possible Physical Layers

Your system may use one of two physical layers:

| Type | EnviraCOM (Native) | RS-485 |
|------|-------------------|--------|
| Wires | 3 (R, C, D) | 2-4 |
| Data signal | Modulated 24VAC | Differential ±5V |
| Baud rate | 120 bps | 9600-38400 bps |
| Interface | Custom circuit needed | $10 USB adapter |

**First step: Determine which physical layer your system uses!**

## Project Status

**Phase 0: Physical Layer Identification** - Start Here

## Quick Start

### Installation

```bash

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"

# For analysis tools (pandas, matplotlib)
pip install -e ".[analysis]"

# For hardware design tools (circuit schematics)
pip install -e ".[hardware]"
```

### Step 1: Identify Physical Layer

Before capturing data, determine your bus type:

**Option A: Visual Inspection**
- Count wires between thermostat and relay panel
- 3 wires (R, C, D): Likely EnviraCOM
- 4+ wires with labeled A/B: Likely RS-485

**Option B: Oscilloscope Measurement**
1. Probe the data line
2. EnviraCOM: 24VAC signal with slow (8ms) transitions
3. RS-485: Fast differential signal (microsecond transitions)

**Option C: Use Signal Analyzer** (if you have logic analyzer captures)
```bash
python -m tools.signal_analyze capture.csv
```

### Step 2a: If RS-485

```bash
# Get USB to RS-485 adapter (FTDI chipset recommended)

# Auto-detect baud rate
python -m tools.baudrate_detect -p /dev/ttyUSB0

# Start capturing
python -m tools.capture -p /dev/ttyUSB0 -b <detected_baud>
```

### Step 2b: If EnviraCOM (Native)

You'll need custom hardware. Options:
1. **Find a W8735A Serial Adapter** (discontinued 2013, check eBay)
2. **Build the DIY interface circuit** - See [`docs/hardware/enviracom_interface.md`](docs/hardware/enviracom_interface.md)
   - Complete schematic with BOM (~$15 in parts)
   - Uses H11AA1 + 4N35 optocouplers for isolation
   - ESP32/Arduino compatible
3. **Generate circuit diagrams**:
   ```bash
   pip install -e ".[hardware]"
   python -m tools.hardware.enviracom_schematic --format png
   ```
4. **Generate PCB manufacturing files** (Gerber, BOM, etc.):
   ```bash
   # Install cuflow dependencies
   pip install -e ".[pcb]"

   # Clone cuflow (not available on PyPI)
   git clone https://github.com/jamesbowman/cuflow.git /tmp/cuflow
   export PYTHONPATH="/tmp/cuflow:$PYTHONPATH"

   # Generate PCB files
   python -m tools.hardware.enviracom_pcb
   ```

### Step 3: Analyze Captures

```bash
# Analyze a capture file
python -m tools.analyze captures/raw/capture_*.bin

# Export to readable format
python -m tools.analyze capture.bin --export packets.txt --format parsed

# View specific packet
python -m tools.analyze capture.bin --packet 42
```

## Tools

| Tool | Description |
|------|-------------|
| `tools/capture.py` | Capture RS-485 bus traffic |
| `tools/analyze.py` | Analyze captured packets |
| `tools/replay.py` | Replay packets (use with caution) |
| `tools/baudrate_detect.py` | Auto-detect RS-485 baud rate |
| `tools/signal_analyze.py` | Analyze oscilloscope/logic analyzer captures |
| `tools/packet.py` | Packet parser library |
| `tools/hardware/enviracom_schematic.py` | Generate EnviraCOM interface circuit diagrams |
| `tools/hardware/enviracom_interface.py` | EnviraCOM interface BOM and pinout |
| `tools/hardware/enviracom_pcb.py` | Generate PCB layout and Gerber files (via cuflow) |

## Project Structure

```
trane_protocol/
├── captures/
│   ├── raw/           # Binary capture files
│   └── parsed/        # Analyzed/exported data
├── docs/
│   ├── hardware/      # Wiring and setup guides
│   └── protocol/      # Protocol documentation
│       ├── README.md           # Protocol overview
│       └── enviracom_physical.md  # Physical layer details
├── tools/
│   ├── capture.py     # RS-485 bus capture
│   ├── analyze.py     # Packet analysis
│   ├── replay.py      # Packet replay
│   ├── packet.py      # Packet parser
│   ├── baudrate_detect.py    # Baud rate detection
│   └── signal_analyze.py     # Waveform analysis
├── tests/
├── config.example.yaml
├── pyproject.toml
└── README.md
```

## Related Projects

- [EnviraCOM (GitHub)](https://github.com/roy-bentley/enviracom) - Honeywell EnviraCOM interface
- [Net485](https://github.com/kpishere/Net485) - Multi-brand HVAC RS-485 protocol project
- [Infinitive](https://github.com/acd/infinitive) - Carrier Infinity integration
- [gofinity](https://github.com/bvarner/gofinity) - Go library for Carrier/Bryant

## Key References

- [Bloominglabs EnviraCOM Info](https://www.bloominglabs.org/index.php/Water_Heater_Monitoring_and_Setback_Control) - Physical layer details
- US Patent 6373376B1 - EnviraCOM hardware implementation
- [CocoonTech Forums](https://cocoontech.com/threads/anyone-using-honeywells-enviracom-protocol.16760/) - Community discussion

## Safety Warnings

- **24VAC is dangerous** - Use proper isolation when building interfaces
- Only connect to communication bus lines, NEVER directly to 24VAC power
- Keep a working thermostat available as backup
- Don't experiment during extreme weather
- Start with passive monitoring before sending any packets
- Understand packets before replaying them

## Contributing

Contributions welcome! Especially:
- Confirmation of physical layer type for specific equipment
- Packet captures from different equipment configurations
- Protocol documentation updates
- Checksum algorithm identification
- EnviraCOM interface circuit designs
- Message type mappings

## License

MIT License - See LICENSE file
