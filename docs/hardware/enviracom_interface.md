# DIY EnviraCOM Interface Circuit

A practical interface circuit to connect an ESP32/Arduino to the EnviraCOM 3-wire bus.

## Overview

The EnviraCOM bus uses three wires:
- **R** (Red): 24VAC hot
- **C** (Common): 24VAC neutral/ground reference
- **D** (Data): Modulated signal, 0-18VDC relative to C

**Data encoding:**
- HIGH (recessive): 12-18V DC (idle state)
- LOW (dominant): 0-3V DC (active drive)
- Bit rate: 120 bps synchronized to 60Hz zero-crossings
- Each bit = one AC half-cycle (~8.33ms at 60Hz)

## Block Diagram

```
24VAC (R) ───┬─────────────────────────────────────┐
             │                                     │
             ├──[Zero-Cross Detect]──► MCU GPIO    │
             │                         (interrupt) │
             │                                     │
Data (D) ────┼──[RX Circuit]─────────► MCU GPIO    │
             │                         (input)     │
             │                                     │
             └──[TX Circuit]◄─────────  MCU GPIO   │
                                       (output)    │
                                                   │
Common (C) ────────────────────────────────────────┘
                       │
                      GND reference
```

## Circuit Design

### Bill of Materials

| Ref | Component | Value/Part | Qty | Notes |
|-----|-----------|------------|-----|-------|
| U1 | Optocoupler | H11AA1 | 1 | Zero-crossing detector |
| U2 | Optocoupler | 4N35 or PC817 | 1 | Data RX isolation |
| U3 | Optocoupler | 4N35 or PC817 | 1 | Data TX isolation |
| Q1 | N-MOSFET | 2N7000 | 1 | TX pull-down driver |
| R1, R2 | Resistor | 100kΩ 1/4W | 2 | H11AA1 current limit |
| R3 | Resistor | 47kΩ 1/2W | 1 | Data line divider |
| R4 | Resistor | 10kΩ 1/4W | 1 | Data line divider |
| R5 | Resistor | 1kΩ 1/4W | 1 | 4N35 LED current |
| R6 | Resistor | 10kΩ 1/4W | 1 | MCU pull-up (ZC) |
| R7 | Resistor | 10kΩ 1/4W | 1 | MCU pull-up (RX) |
| R8 | Resistor | 330Ω 1/4W | 1 | TX optocoupler LED |
| R9 | Resistor | 10kΩ 1/4W | 1 | TX MOSFET gate pull-down |
| R10 | Resistor | 22Ω 1W | 1 | TX current limit |
| D1 | Zener diode | 5.1V 500mW | 1 | Clamp for RX |
| D2 | Diode | 1N4148 | 1 | Flyback protection |
| C1 | Capacitor | 0.1µF | 1 | Noise filter |

### 1. Zero-Crossing Detector

The H11AA1 has back-to-back LEDs, detecting both AC half-cycles.

```
     24VAC (R) ──────┬────[R1 100kΩ]────┐
                     │                   │
                     │              ┌────┴────┐
                     │              │  H11AA1 │
                     │              │         │
                     │        1 ────┤►  LED  ├──── 4 (Collector)──┬── +3.3V
                     │              │  ◄►    │                    │
     Common (C) ─────┴──[R2 100kΩ]──┤   LED  ├──── 5 (Emitter)────┼── MCU_ZC_PIN
                                    │         │                    │
                                    │    3────┤ (Base - NC)       [R6 10kΩ]
                                    └─────────┘                    │
                                                                  GND
```

**Output:** MCU_ZC_PIN goes LOW at each zero-crossing (120Hz pulse train).
Use edge interrupt to synchronize bit sampling.

### 2. Data Receive Circuit

Voltage divider + optocoupler for isolation:

```
     Data (D) ────[R3 47kΩ]───┬───[R4 10kΩ]───┬─── Common (C)
                              │               │
                              │              [D1 5.1V Zener]
                              │               │
                              └───────────────┤
                                              │
                              ┌───────────────┘
                              │
                         ┌────┴────┐
                         │  4N35   │
                         │         │
                    1 ───┤►  LED  ├──── 4 (Collector)──┬── +3.3V
                         │         │                    │
     Common (C) ─[R5 1kΩ]┤         ├──── 5 (Emitter)───┼── MCU_RX_PIN
                         │    3────┤ (Base - NC)       [R7 10kΩ]
                         └─────────┘                    │
                                                       GND
```

**Note:** The voltage divider reduces ~15V to ~2.6V for the optocoupler LED.
When Data is HIGH (15V), LED conducts, output is LOW.
When Data is LOW (0V), LED off, output pulled HIGH.
**Signal is inverted** - handle in software.

### 3. Data Transmit Circuit

Isolated MOSFET driver to pull Data line LOW:

```
                              ┌────────────────────── Data (D)
                              │
                             [R10 22Ω 1W]
                              │
                              │ Drain
                         ┌────┴────┐
                         │  2N7000 │
                         │         │
                         │    Gate ├────┬─────────────┐
                         │         │    │             │
                         └────┬────┘  [R9 10kΩ]       │
                              │ Source  │             │
                              │         │             │
     Common (C) ──────────────┴─────────┴─────┐       │
                                              │       │
                         ┌────────────────────┴───────┤
                         │  4N35                      │
                         │         │                  │
                    1 ───┤►  LED  ├──── 4 (Collector)─┘
                         │         │
     MCU_TX_PIN ─[R8 330Ω]         ├──── 5 (Emitter)─── MCU GND
                         │    3────┤ (Base - NC)
                         └─────────┘
```

**Operation:**
- MCU_TX_PIN HIGH → optocoupler conducts → MOSFET gate HIGH → pulls Data LOW (dominant)
- MCU_TX_PIN LOW → optocoupler off → MOSFET off → Data floats HIGH (recessive)

**R10 limits current** when driving dominant. The bus has a pull-up, so releasing allows recessive state.

## Complete Schematic

```
                           ISOLATED SIDE                    │    MCU SIDE
                                                            │
    ┌──────────────────────────────────────────────────────┼────────────────────┐
    │                                                       │                    │
    │  24VAC (R) ──┬────[R1]────┐                          │                    │
    │              │            │     ┌──────────┐         │    +3.3V           │
    │              │       ┌────┴─────┤  H11AA1  ├─────────┼────┬──[R6]──┐      │
    │              │       │          └──────────┘         │    │        │      │
    │  Common (C) ─┴─[R2]──┘                               │    │    MCU_ZC     │
    │       │                                              │    │               │
    │       │                                              │    │               │
    │       │                           ┌──────────┐       │    │               │
    │  Data (D)──[R3]──┬──[R4]──┬──────┤   4N35   ├───────┼────┼──[R7]──┐      │
    │                  │        │       └──────────┘       │    │        │      │
    │                 [D1]     [R5]                        │    │    MCU_RX     │
    │                  │        │                          │    │               │
    │                  └────────┴──────────────────────────┼────┘               │
    │                                                      │                    │
    │                           ┌──────────┐               │                    │
    │  Data (D)──[R10]──┬──────┤  2N7000  │               │                    │
    │                   │       └────┬─────┘               │                    │
    │                   │            │                     │                    │
    │                   │          [R9]    ┌──────────┐    │                    │
    │                   │            └─────┤   4N35   ├────┼────[R8]── MCU_TX   │
    │                   │                  └──────────┘    │                    │
    │  Common (C) ──────┴──────────────────────────────────┼────── MCU GND      │
    │                                                      │                    │
    └──────────────────────────────────────────────────────┼────────────────────┘
                                                           │
                                              ISOLATION BARRIER
```

## Software Timing

```c
// ESP32 example - interrupt-driven EnviraCOM receiver

#define PIN_ZC   4   // Zero-crossing input
#define PIN_RX   5   // Data receive
#define PIN_TX  18   // Data transmit

volatile uint32_t last_zc_time = 0;
volatile bool bit_ready = false;
volatile bool current_bit = false;

// Zero-crossing ISR - fires at 120Hz
void IRAM_ATTR zc_isr() {
    uint32_t now = micros();
    last_zc_time = now;

    // Sample data ~4ms after zero-crossing (mid-bit)
    // Schedule a timer or use delayed sampling
    bit_ready = true;
}

void setup() {
    pinMode(PIN_ZC, INPUT);
    pinMode(PIN_RX, INPUT_PULLUP);
    pinMode(PIN_TX, OUTPUT);
    digitalWrite(PIN_TX, LOW);  // Start recessive

    attachInterrupt(digitalPinToInterrupt(PIN_ZC), zc_isr, FALLING);
}

void loop() {
    if (bit_ready) {
        // Wait ~4ms from zero-crossing for mid-bit sample
        delayMicroseconds(4000);

        // Read data (inverted due to optocoupler)
        current_bit = !digitalRead(PIN_RX);

        // Process bit...

        bit_ready = false;
    }
}

// Transmit a dominant bit (pull low)
void tx_dominant() {
    digitalWrite(PIN_TX, HIGH);
}

// Transmit a recessive bit (release)
void tx_recessive() {
    digitalWrite(PIN_TX, LOW);
}
```

## PCB Layout Tips

1. **Keep isolation gap ≥2.5mm** between AC and DC sides
2. **Use ground plane** on MCU side only
3. **Add TVS diode** (P6KE30A) across R-C for surge protection
4. **Consider conformal coating** for humidity resistance
5. **Mount in ventilated enclosure** - resistors dissipate ~0.5W total

## Testing Procedure

1. **Power off HVAC system** before connecting
2. **Verify 24VAC** between R and C with multimeter
3. **Connect interface**, power on
4. **Check zero-crossing** - should see 120Hz pulses on scope
5. **Monitor Data line** - should see activity when thermostat communicates
6. **Passive capture first** - don't transmit until you understand the protocol

## Safety Warnings

- **24VAC can cause injury** - treat with respect
- **Never work on live circuits** unless necessary
- **Use fused connections** if available
- **Isolation is critical** - double-check optocoupler connections
- **Keep original thermostat** available as backup
- **Don't experiment during extreme weather**

## References

- [US Patent 6373376B1](https://patents.google.com/patent/US6373376B1/en) - Original EnviraCOM hardware
- [US Patent 7769932](https://patents.google.com/patent/US7769932) - Complete transceiver specs
- [Bloominglabs EnviraCOM](https://bloominglabs.org/Water_Heater_Monitoring_and_Setback_Control) - Community project
- [H11AA1 Datasheet](https://www.vishay.com/docs/83608/h11aa1.pdf) - Zero-crossing optocoupler
