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
| R1 | Resistor | 4.7kΩ 1/4W | 1 | H11AA1 current limit, AC_HOT leg |
| R2 | Resistor | 4.7kΩ 1/4W | 1 | H11AA1 current limit, AC_COM leg |
| R3 | Resistor | 10kΩ 1/4W | 1 | MCU pull-up (ZC) |
| R4 | Resistor | 4.7kΩ 1/4W | 1 | Data line divider (top) |
| R5 | Resistor | 1.2kΩ 1/4W | 1 | Data line divider (bottom) |
| R6 | Resistor | 220Ω 1/4W | 1 | 4N35 RX LED current |
| R7 | Resistor | 22kΩ 1/4W | 1 | MCU pull-up (RX) |
| R8 | Resistor | 330Ω 1/4W | 1 | TX optocoupler LED |
| R9 | Resistor | 100kΩ 1/4W | 1 | TX MOSFET gate pull-down (AC_COM ref) |
| R10 | Resistor | 22Ω 1W | 1 | TX current limit |
| R11 | Resistor | 33kΩ 1/4W | 1 | AC supply series limiting resistor |
| D1 | Zener diode | 5.1V 500mW | 1 | RX input clamp |
| D2 | Diode | 1N4148 | 1 | TX drain clamp (negative transients) |
| D3 | Diode | 1N4007 | 1 | AC supply half-wave rectifier |
| D4 | Zener diode | 12V 500mW | 1 | AC supply shunt regulator |
| C1 | Capacitor | 10µF 50V electrolytic | 1 | AC supply filter |
| C2 | Capacitor | 100nF | 1 | MCU VCC decoupling |

### 1. Zero-Crossing Detector

The H11AA1 has back-to-back LEDs, detecting both AC half-cycles.
R1 and R2 are split one per leg (hot and common) so each half-cycle sees equal
series impedance. 4.7kΩ + 4.7kΩ = 9.4kΩ total gives ~3.5mA peak LED current
(24VAC ≈ 34V peak). This matters: optocoupler CTR falls off steeply at low LED
current, and the phototransistor must sink ~0.33mA through the 10kΩ pull-up —
a few mA of peak LED drive is required. (With 33kΩ per leg the peak LED current
would be only ~0.5mA and the output would never pull low at all.)
Dissipation is ~30mW per resistor, so 1/4W parts are fine.

```
     24VAC (R) ──[R1 4.7kΩ]──┐                              +3.3V
                             │                                │
                        ┌────┴──────────┐                 [R3 10kΩ]
                        │ 1             │                     │
                        │  ◄►  H11AA1 C ├ 5 (Collector) ──────┴── MCU_ZC_PIN
                        │ LEDs          │
                        │ 2           E ├ 4 (Emitter) ──────────── GND
                        └────┬──────────┘   (6 = Base, NC)
                             │
     Common (C) ─[R2 4.7kΩ]──┘
```

**Output:** MCU_ZC_PIN pulses HIGH around each zero-crossing (120Hz pulse
train). Away from the crossings the LED conducts and the phototransistor holds
the pin LOW; near a crossing the LED current drops out and R3 pulls the pin
HIGH. Use a RISING edge interrupt — the pulse is centered on the true
zero-crossing, so a single edge gives a constant, calibratable offset.

### 2. Data Receive Circuit

Voltage divider (threshold) + optocoupler for isolation:

```
     Data (D) ───[R4 4.7kΩ]───┬───[R5 1.2kΩ]───┬─── Common (C)
                              │                │
                              │            [D1 5.1V Zener]
                              │                │  (cathode to node)
                              ├────────────────┘
                              │
                          [R6 220Ω]
                              │
                              │                             +3.3V
                         ┌────┴──────────┐                    │
                         │ 1 A           │                [R7 22kΩ]
                         │       4N35  C ├ 5 (Collector) ─────┴── MCU_RX_PIN
                         │ 2 K         E ├ 4 (Emitter) ─────────── GND
                         └────┬──────────┘   (6 = Base, NC)
                              │
     Common (C) ──────────────┘
```

**Note:** The LED (~1.1V drop) loads the divider, so it must be included in the
math. With Data HIGH (~15V) the R4/R5 divider presents a Thevenin source of
~3.1V / ~0.96kΩ, giving ~1.6mA through R6 into the LED — enough for the 4N35 to
sink the 22kΩ pull-up (only ~0.15mA needed). With Data at the dominant level
(0–3V), the divider node stays below the LED's forward voltage, so the LED is
off and the output releases. This is why the divider is kept: it sets a receive
threshold between the dominant and recessive levels, not just a "safe voltage."

When Data is HIGH (12–18V), LED conducts, MCU_RX_PIN is LOW.
When Data is LOW (0–3V), LED off, MCU_RX_PIN pulled HIGH.
**Signal is inverted** - handle in software.

### 3. AC-Side Regulated Supply

The TX MOSFET gate drive must be referenced to AC_COM (not MCU GND) to preserve
galvanic isolation. A small half-wave supply derived from AC_HOT provides ~12V
above AC_COM for this purpose.

```
     24VAC (R) ──[D3 1N4007]──[R11 33kΩ]──┬── V_AC (~12V above AC_COM)
                                           │
                                          [D4 12V Zener]    [C1 10µF 50V]
                                           │                 │
     Common (C) ───────────────────────────┴─────────────────┘
```

### 4. Data Transmit Circuit

Isolated MOSFET driver to pull Data line LOW. The optocoupler transistor is
powered from V_AC (AC side) so both the collector supply and R9 gate pull-down
are referenced to AC_COM, maintaining full isolation from the MCU.

```
                              ┌────────────────────── Data (D)
                              │
                             [R10 22Ω 1W]
                              │
                              │ Drain
                         ┌────┴────┐
                         │  2N7000 │
                         │         │
                         │    Gate ├────┬───────────── TX_GATE
                         │         │    │
                         └────┬────┘  [R9 100kΩ]
                              │ Source  │  (to AC_COM)
                              │         │
     Common (C) ──────────────┴─────────┘

                                        ┌─────────────┐
     MCU_TX ──[R8 330Ω]────────── 1 (A) ┤►    4N35    ├ 5 (C) ── V_AC
                                        │     (U3)    │
     MCU GND ──────────────────── 2 (K) ┤             ├ 4 (E) ── TX_GATE
                                        └─────────────┘ (6 = Base, NC)
```

**Operation:**
- MCU_TX HIGH → U3 LED conducts → phototransistor pulls gate toward V_AC → MOSFET on → Data LOW (dominant)
- MCU_TX LOW → U3 off → R9 pulls gate to AC_COM → Vgs = 0 → MOSFET off → Data HIGH (recessive)

**Isolation is preserved** because:
- MCU side: MCU_TX → R8 → U3 LED → MCU GND (all MCU-referenced)
- AC side: V_AC → U3 transistor → gate → MOSFET → AC_COM (all AC-referenced)
- The only crossing is optical through the U3 LED/transistor pair.

**R10 limits current** when driving dominant, but only within limits: the
2N7000 is rated for 200mA continuous, and a stiff 15V source through 22Ω would
push ~680mA. The bus master is expected to current-limit the data line — verify
this (measure the data line's short-circuit current to C) before transmitting,
and increase R10 if it exceeds ~150mA. The bus has a pull-up, so releasing the
MOSFET allows the recessive state.

## Complete Schematic

Net-by-net wiring summary. The only things that cross the isolation barrier
are the optical paths inside U1, U2, and U3.

**AC side (everything referenced to Common/AC_COM):**

- Zero-cross: `24VAC (R) → R1 4.7kΩ → U1 pin 1`; `U1 pin 2 → R2 4.7kΩ → Common`
- AC-side supply: `24VAC (R) → D3 1N4007 → R11 33kΩ → V_AC`;
  D4 (12V Zener, cathode to V_AC) and C1 (10µF) each from V_AC to Common
- RX divider: `Data (D) → R4 4.7kΩ → RX_DIV`; `RX_DIV → R5 1.2kΩ → Common`;
  D1 (5.1V Zener, cathode to RX_DIV) to Common;
  `RX_DIV → R6 220Ω → U2 pin 1 (A)`; `U2 pin 2 (K) → Common`
- TX driver: `Data (D) → R10 22Ω → Q1 drain`; D2 (1N4148, cathode to drain) to
  Common; `Q1 source → Common`; `Q1 gate → R9 100kΩ → Common`;
  `U3 pin 5 (C) → V_AC`; `U3 pin 4 (E) → Q1 gate`

**MCU side (everything referenced to MCU GND):**

- `U1 pin 5 (C) → MCU_ZC`, with R3 10kΩ pull-up to +3.3V; `U1 pin 4 (E) → GND`
- `U2 pin 5 (C) → MCU_RX`, with R7 22kΩ pull-up to +3.3V; `U2 pin 4 (E) → GND`
- `MCU_TX → R8 330Ω → U3 pin 1 (A)`; `U3 pin 2 (K) → GND`
- C2 100nF from +3.3V to GND

**Optocoupler pinout reminder (6-pin DIP: H11AA1, 4N35):**
pin 1 = LED anode, pin 2 = LED cathode, pin 3 = NC,
pin 4 = **emitter**, pin 5 = **collector**, pin 6 = base (leave open).
A common wiring error is swapping pins 4 and 5 — the transistor then runs in
reverse-active mode with almost no gain and the output barely moves.

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
// (ZC pin pulses HIGH around each crossing; the pulse is centered on it)
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

    attachInterrupt(digitalPinToInterrupt(PIN_ZC), zc_isr, RISING);
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
5. **Mount in ventilated enclosure** - resistors dissipate ~0.25W total

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
