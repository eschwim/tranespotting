# EnviraCOM Physical Layer

## Overview

The native EnviraCOM bus uses a 3-wire interface with 24VAC modulation,
fundamentally different from RS-485.

## Wiring

| Terminal | Name | Function |
|----------|------|----------|
| R | Red | 24VAC (hot) |
| C | Common | 24VAC (common/neutral) |
| D | Data | Modulated 24VAC data signal |

## Signal Characteristics

### Power
- 24VAC provided on R and C lines
- Powers all bus devices
- Also used as timing reference

### Data Encoding
- **Baud rate**: 120 bps at 60Hz (100 bps at 50Hz)
- **Bit timing**: Each bit synchronized to one half-cycle of AC (8.33ms at 60Hz)
- **Encoding**: Dominant/recessive (similar to CAN bus)
  - Dominant bit: Data line pulled to specific voltage
  - Recessive bit: Data line at idle state
  - Dominant wins in collision (enables arbitration)

### Zero-Crossing Synchronization
- Bits are aligned to the zero-crossing of the 24VAC signal
- Receiver must detect zero-crossings to sample data correctly
- This provides inherent synchronization without a separate clock

## Hardware Interface Design

To interface with the EnviraCOM bus, you need:

### 1. Zero-Crossing Detector
Detect when 24VAC crosses zero to synchronize bit sampling.

```
24VAC ─────┬──[R1]──┬──[R2]──┬─── +3.3V
           │        │        │
           │      [D1]     [D2]
           │        │        │
           └────────┴────────┴─── To MCU GPIO (zero-cross interrupt)
```

Options:
- Optocoupler (H11AA1 or similar) for isolation
- Resistor divider with comparator
- Dedicated zero-crossing IC

### 2. Data Line Interface
Read and write the modulated data signal.

**Reading**:
- Resistor divider or optocoupler to reduce 24VAC to logic levels
- Sample at zero-crossing + offset

**Writing**:
- Transistor or TRIAC to modulate the data line
- Must handle dominant/recessive arbitration

### 3. Power Supply
- Derive 5V/3.3V from 24VAC for your microcontroller
- Small transformer or capacitive dropper

## Example Interface Circuit

See US Patent 6373376B1 for detailed circuit diagrams.

Basic concept for data reading:

```
Data (D) ──[100kΩ]──┬──[10kΩ]──┬─── GND
                    │          │
                    └──[Zener]─┘
                    │
                    └─── To MCU ADC or comparator
```

**WARNING**: 24VAC can be dangerous. Use appropriate isolation
and safety measures. Consider optocoupler-based designs.

## Timing Diagram

```
24VAC:    ╱╲  ╱╲  ╱╲  ╱╲  ╱╲  ╱╲  ╱╲  ╱╲
         ╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲
              │     │     │     │
Zero-X:      ─┴─────┴─────┴─────┴─────

Data:    ───┐     ┌─────┐     ┌───────
            └─────┘     └─────┘

Bits:       [  1  ] [  0  ] [  1  ] [  0  ]

            ←8.33ms→ (at 60Hz)
```

## Arbitration

Like CAN bus, EnviraCOM uses bitwise arbitration:
1. Multiple devices can start transmitting simultaneously
2. Each device monitors the bus while transmitting
3. If a device transmits recessive but sees dominant, it loses arbitration
4. Losing device stops transmitting and becomes receiver
5. Winning device continues uninterrupted

This allows collision-free multi-master communication.

## Message Framing

Messages are broadcast to all devices (no addressing at physical layer).
Message structure and addressing are handled at higher protocol layers.

## Comparison with RS-485

| Feature | EnviraCOM | RS-485 |
|---------|-----------|--------|
| Wires | 3 (power + data) | 2-4 (differential data) |
| Speed | 120 bps | Typically 9600-115200 bps |
| Power | Integrated 24VAC | Separate |
| Arbitration | Built-in | None (requires protocol) |
| Max distance | 300 ft | 4000 ft |
| Interface cost | Custom circuit | $10 adapter |

## Determining Your System's Physical Layer

To check if your system uses native EnviraCOM or RS-485:

1. **Count the wires** between thermostat and relay panel
   - 3 wires (R, C, D): Likely native EnviraCOM
   - 4+ wires with separate data pair: Possibly RS-485

2. **Measure with oscilloscope**
   - EnviraCOM: 24VAC on data line, modulated at AC frequency
   - RS-485: ±2-6V differential signal, higher frequency transitions

3. **Check relay panel documentation**
   - BAY24VRPAC52DC may convert between protocols
   - Look for RS-485 terminals (A/B or +/-)

## References

- US Patent 6373376B1 - EnviraCOM hardware implementation
- [Bloominglabs Water Heater Control](https://www.bloominglabs.org/index.php/Water_Heater_Monitoring_and_Setback_Control)
- [EnviraCOM GitHub](https://github.com/roy-bentley/enviracom)
