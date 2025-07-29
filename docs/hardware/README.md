# Hardware Setup

## System Components

### Trane XL1050 Thermostat
- 7" touchscreen communicating thermostat
- Manufactured by Honeywell for Trane
- Uses EnviraCOM 2.0 protocol (Honeywell proprietary)
- Acts as system controller

### Trane SV92 Furnace
- Variable speed gas furnace
- Communicating control board

### Trane XV19 Heat Pump
- Variable speed heat pump
- Communicating control board

### BAY24VRPAC52DC Relay Panel
- Interface between thermostat and equipment
- May convert between communication protocols
- Provides 24V interface option

## Determining Your Physical Layer

**Critical first step**: Identify which physical layer your system uses.

### Method 1: Wire Count

Examine the wiring between your thermostat and relay panel:

| Wire Count | Likely Type | Notes |
|------------|-------------|-------|
| 3 wires (R, C, D) | EnviraCOM | Native 24VAC modulated |
| 4+ wires with A/B | RS-485 | Differential signaling |

### Method 2: Oscilloscope

Probe the data line(s):

**EnviraCOM characteristics:**
- 24VAC signal on data line
- Slow transitions (~8ms per bit)
- Synchronized to 60Hz AC

**RS-485 characteristics:**
- Differential signal (A and B lines)
- ±2-6V signal levels
- Fast transitions (microseconds)

### Method 3: Relay Panel Inspection

Look at the BAY24VRPAC52DC terminals:
- Labels like "D" or "Data" suggest EnviraCOM
- Labels like "A/B" or "+/-" suggest RS-485

## Hardware Options by Physical Layer

### For RS-485 Systems

Simple and inexpensive:

**USB to RS-485 Adapter**
- Recommended: FTDI chipset adapters
- Examples:
  - DSD TECH SH-U10
  - DTECH USB to RS485
- Cost: $10-20
- Connection: Screw terminals to A/B lines

```
HVAC Bus          USB Adapter
   A ─────────────── A (Data+)
   B ─────────────── B (Data-)
   GND ───────────── GND (if available)
```

### For EnviraCOM Systems

More complex - requires custom hardware or rare adapter:

**Option 1: W8735A Serial Adapter (Discontinued)**
- Honeywell EnviraCOM to RS-232 adapter
- Discontinued in 2013
- Check eBay, surplus electronics
- RS-232 side: 19200 baud, 8N1

**Option 2: DIY Interface Circuit**

You need to build circuitry that:
1. Detects 24VAC zero-crossings for bit synchronization
2. Demodulates the 24VAC data signal
3. Handles dominant/recessive arbitration
4. Optionally derives power from 24VAC

See `docs/protocol/enviracom_physical.md` for circuit details.

**Option 3: Microcontroller Interface**

Use an ESP32 or Arduino with:
- Zero-crossing detector circuit
- ADC or comparator for data line
- Optocoupler for isolation

Example components:
- H11AA1 optocoupler (zero-crossing detection)
- 4N35 optocoupler (data isolation)
- Voltage divider resistors

## Wiring Diagrams

### RS-485 Passive Tap

```
                    ┌─────────────┐
Thermostat ────A────┤             ├────A──── Equipment
               │    │  Your Tap   │    │
               └────┤    Point    ├────┘
                    │             │
Thermostat ────B────┤             ├────B──── Equipment
               │    │             │    │
               └────┤             ├────┘
                    └──┬─────┬───┘
                       │     │
                       A     B
                       │     │
                    ┌──┴─────┴──┐
                    │ USB-RS485 │
                    │  Adapter  │
                    └─────┬─────┘
                          │
                         USB
                          │
                       Computer
```

### EnviraCOM Bus Tap

```
                    ┌─────────────┐
Thermostat ────R────┤             ├────R──── Equipment
(24VAC Hot)    │    │             │    │
               └────┤             ├────┘
                    │             │
Thermostat ────C────┤  Your Tap   ├────C──── Equipment
(24VAC Com)    │    │   Point     │    │
               └────┤             ├────┘
                    │             │
Thermostat ────D────┤             ├────D──── Equipment
(Data)         │    │             │    │
               └────┤             ├────┘
                    └──┬──┬──┬───┘
                       │  │  │
                       R  C  D
                       │  │  │
                    ┌──┴──┴──┴──┐
                    │  Custom   │
                    │ Interface │
                    │  Circuit  │
                    └─────┬─────┘
                          │
                      Serial/USB
                          │
                       Computer
```

## Safety Notes

1. **24VAC Power**
   - Never connect your computer directly to 24VAC
   - Use optoisolators for safety
   - EnviraCOM data line carries 24VAC!

2. **Isolation**
   - RS-485: Consider optoisolated adapters
   - EnviraCOM: Isolation is essential

3. **Grounding**
   - Ensure proper grounding to avoid noise
   - Don't create ground loops

4. **System Backup**
   - Keep the original thermostat available
   - Be able to restore stock configuration

5. **Weather Considerations**
   - Don't experiment during extreme heat/cold
   - Have a fallback plan

## Required Equipment

### Minimum for Investigation
- Multimeter (for checking voltages)
- Oscilloscope or logic analyzer (for signal analysis)

### For RS-485 Capture
- USB to RS-485 adapter (~$10-20)
- Computer with USB port

### For EnviraCOM Capture
- W8735A adapter (if you can find one), OR
- Custom interface circuit components:
  - Optocouplers (H11AA1, 4N35)
  - Resistors (various values)
  - Zener diodes (for voltage clamping)
  - Small transformer or capacitive dropper (for power)
  - Microcontroller (ESP32, Arduino, etc.)

### Optional
- Logic analyzer (Saleae, DSLogic, etc.)
- Second RS-485 adapter (for man-in-the-middle capture)
