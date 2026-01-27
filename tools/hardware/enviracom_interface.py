#!/usr/bin/env python3
"""
EnviraCOM Interface Circuit - SKiDL Definition

Generates schematic and netlist for a DIY EnviraCOM to MCU interface.
Provides galvanic isolation between 24VAC HVAC bus and 3.3V microcontroller.

Usage:
    python -m tools.hardware.enviracom_interface --svg    # Generate SVG schematic
    python -m tools.hardware.enviracom_interface --netlist # Generate KiCad netlist
    python -m tools.hardware.enviracom_interface --all    # Generate both

Requirements:
    pip install -e ".[hardware]"
"""

import argparse
from pathlib import Path

from skidl import (
    TEMPLATE,
    Net,
    Part,
    Pin,
    generate_netlist,
    generate_svg,
    SKIDL,
    set_default_tool,
)

# Use SKiDL tool mode (no KiCad required)
set_default_tool(SKIDL)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "hardware" / "generated"


# =============================================================================
# PART TEMPLATES - Define component types once, instantiate as needed
# =============================================================================

def _create_resistor_template():
    """Create a 2-pin resistor template."""
    r = Part(name="R", tool=SKIDL, dest=TEMPLATE)
    r.ref_prefix = "R"
    r.description = "Resistor"
    r += Pin(num=1, name="1", func=Pin.types.PASSIVE)
    r += Pin(num=2, name="2", func=Pin.types.PASSIVE)
    return r


def _create_capacitor_template():
    """Create a 2-pin capacitor template."""
    c = Part(name="C", tool=SKIDL, dest=TEMPLATE)
    c.ref_prefix = "C"
    c.description = "Capacitor"
    c += Pin(num=1, name="1", func=Pin.types.PASSIVE)
    c += Pin(num=2, name="2", func=Pin.types.PASSIVE)
    return c


def _create_diode_template():
    """Create a 2-pin diode template (1=K cathode, 2=A anode)."""
    d = Part(name="D", tool=SKIDL, dest=TEMPLATE)
    d.ref_prefix = "D"
    d.description = "Diode"
    d += Pin(num=1, name="K", func=Pin.types.PASSIVE)  # Cathode
    d += Pin(num=2, name="A", func=Pin.types.PASSIVE)  # Anode
    return d


def _create_optocoupler_template():
    """
    Create a 6-pin optocoupler template (4N35-style).
    Pins: 1=A (LED anode), 2=K (LED cathode), 3=NC, 4=C (collector), 5=E (emitter), 6=B (base)
    """
    u = Part(name="OPTO", tool=SKIDL, dest=TEMPLATE)
    u.ref_prefix = "U"
    u.description = "Optocoupler"
    u += Pin(num=1, name="A", func=Pin.types.INPUT)    # LED Anode
    u += Pin(num=2, name="K", func=Pin.types.INPUT)    # LED Cathode
    u += Pin(num=3, name="NC", func=Pin.types.NOCONNECT)  # No connect / Base
    u += Pin(num=4, name="C", func=Pin.types.OPENCOLL)  # Collector
    u += Pin(num=5, name="E", func=Pin.types.OUTPUT)    # Emitter
    u += Pin(num=6, name="B", func=Pin.types.INPUT)     # Base (usually NC)
    return u


def _create_h11aa1_template():
    """
    Create H11AA1 bidirectional optocoupler template.
    Pins: 1=A1, 2=A2/K1, 3=NC, 4=C, 5=E, 6=B
    """
    u = Part(name="H11AA1", tool=SKIDL, dest=TEMPLATE)
    u.ref_prefix = "U"
    u.description = "AC Input Optocoupler"
    u += Pin(num=1, name="A1", func=Pin.types.INPUT)     # LED Anode 1
    u += Pin(num=2, name="A2_K1", func=Pin.types.INPUT)  # LED Anode 2 / Cathode 1
    u += Pin(num=3, name="NC", func=Pin.types.NOCONNECT)
    u += Pin(num=4, name="C", func=Pin.types.OPENCOLL)   # Collector
    u += Pin(num=5, name="E", func=Pin.types.OUTPUT)     # Emitter
    u += Pin(num=6, name="B", func=Pin.types.INPUT)      # Base (usually NC)
    return u


def _create_nfet_template():
    """Create N-channel MOSFET template (G, D, S)."""
    q = Part(name="NFET", tool=SKIDL, dest=TEMPLATE)
    q.ref_prefix = "Q"
    q.description = "N-Channel MOSFET"
    q += Pin(num=1, name="G", func=Pin.types.INPUT)   # Gate
    q += Pin(num=2, name="D", func=Pin.types.PASSIVE)  # Drain
    q += Pin(num=3, name="S", func=Pin.types.PASSIVE)  # Source
    return q


def _create_connector_template(num_pins):
    """Create a connector template with specified pins."""
    j = Part(name=f"CONN_{num_pins}", tool=SKIDL, dest=TEMPLATE)
    j.ref_prefix = "J"
    j.description = f"{num_pins}-pin Connector"
    for i in range(1, num_pins + 1):
        j += Pin(num=i, name=str(i), func=Pin.types.PASSIVE)
    return j


# Create templates (done once at module load)
_R_TEMPLATE = _create_resistor_template()
_C_TEMPLATE = _create_capacitor_template()
_D_TEMPLATE = _create_diode_template()
_OPTO_TEMPLATE = _create_optocoupler_template()
_H11AA1_TEMPLATE = _create_h11aa1_template()
_NFET_TEMPLATE = _create_nfet_template()


def create_enviracom_interface():
    """
    Create the EnviraCOM interface circuit.

    The circuit provides:
    - Zero-crossing detection for bit synchronization (120Hz at 60Hz AC)
    - Isolated data receive path
    - Isolated data transmit path

    Returns:
        dict: Named nets for external connections
    """

    # ==========================================================================
    # NETS - Define all circuit nodes
    # ==========================================================================

    # AC side (HVAC bus) - DANGEROUS 24VAC!
    ac_hot = Net("AC_HOT")  # 24VAC hot (R terminal)
    ac_com = Net("AC_COM")  # 24VAC common (C terminal)
    data = Net("DATA")  # EnviraCOM data line (D terminal)

    # DC side (MCU) - Safe low voltage
    vcc = Net("VCC")  # 3.3V or 5V supply
    gnd = Net("GND")  # MCU ground
    mcu_zc = Net("MCU_ZC")  # Zero-crossing output to MCU
    mcu_rx = Net("MCU_RX")  # Data receive output to MCU
    mcu_tx = Net("MCU_TX")  # Data transmit input from MCU

    # Internal nodes
    zc_led_mid = Net("ZC_LED")  # Between ZC current limit resistors
    rx_divided = Net("RX_DIV")  # Voltage-divided data signal
    tx_gate = Net("TX_GATE")  # TX MOSFET gate drive

    # ==========================================================================
    # ZERO-CROSSING DETECTOR
    # H11AA1 has back-to-back LEDs, detects both AC half-cycles
    # Output: 120Hz pulse train synchronized to AC line
    # ==========================================================================

    # Current limiting resistors for AC input (split for power dissipation)
    # At 24VAC RMS (~34V peak), 200k total gives ~170uA peak LED current
    r_zc1 = _R_TEMPLATE(value="100k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_zc1.ref = "R1"

    r_zc2 = _R_TEMPLATE(value="100k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_zc2.ref = "R2"

    # H11AA1 optocoupler
    opto_zc = _H11AA1_TEMPLATE(value="H11AA1", footprint="Package_DIP:DIP-6_W7.62mm")
    opto_zc.ref = "U1"

    # Pull-up resistor for phototransistor output
    r_zc_pull = _R_TEMPLATE(value="10k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_zc_pull.ref = "R3"

    # Connections - Zero Crossing Detector
    ac_hot += r_zc1[1]
    r_zc1[2] += zc_led_mid
    zc_led_mid += r_zc2[1]
    r_zc2[2] += opto_zc["A1"]
    opto_zc["A2_K1"] += ac_com

    vcc += r_zc_pull[1]
    r_zc_pull[2] += mcu_zc
    opto_zc["C"] += mcu_zc
    opto_zc["E"] += gnd

    # ==========================================================================
    # DATA RECEIVE CIRCUIT
    # Voltage divider reduces ~15V data signal to safe level for optocoupler
    # Signal is inverted: Data HIGH -> MCU LOW, Data LOW -> MCU HIGH
    # ==========================================================================

    # Voltage divider: 47k + 10k divides ~15V to ~2.6V
    r_rx_top = _R_TEMPLATE(value="47k", footprint="Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal")
    r_rx_top.ref = "R4"

    r_rx_bot = _R_TEMPLATE(value="10k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_rx_bot.ref = "R5"

    # Zener clamp for protection (K=cathode, A=anode)
    d_rx_clamp = _D_TEMPLATE(value="5.1V_Zener", footprint="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal")
    d_rx_clamp.ref = "D1"

    # Current limiting for optocoupler LED
    r_rx_led = _R_TEMPLATE(value="1k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_rx_led.ref = "R6"

    # 4N35 optocoupler for isolation
    opto_rx = _OPTO_TEMPLATE(value="4N35", footprint="Package_DIP:DIP-6_W7.62mm")
    opto_rx.ref = "U2"

    # Pull-up for phototransistor output
    r_rx_pull = _R_TEMPLATE(value="10k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_rx_pull.ref = "R7"

    # Connections - Data Receive
    data += r_rx_top[1]
    r_rx_top[2] += rx_divided
    rx_divided += r_rx_bot[1]
    r_rx_bot[2] += ac_com

    rx_divided += d_rx_clamp["K"]  # Cathode to signal (clamps positive)
    d_rx_clamp["A"] += ac_com  # Anode to common

    rx_divided += r_rx_led[1]
    r_rx_led[2] += opto_rx["A"]
    opto_rx["K"] += ac_com

    vcc += r_rx_pull[1]
    r_rx_pull[2] += mcu_rx
    opto_rx["C"] += mcu_rx
    opto_rx["E"] += gnd

    # ==========================================================================
    # DATA TRANSMIT CIRCUIT
    # Optocoupler + MOSFET driver pulls data line LOW (dominant)
    # MCU HIGH -> Data LOW (dominant), MCU LOW -> Data HIGH (recessive)
    # ==========================================================================

    # LED current limiting for TX optocoupler
    r_tx_led = _R_TEMPLATE(value="330", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_tx_led.ref = "R8"

    # 4N35 optocoupler for isolation
    opto_tx = _OPTO_TEMPLATE(value="4N35", footprint="Package_DIP:DIP-6_W7.62mm")
    opto_tx.ref = "U3"

    # Gate pull-down (ensures MOSFET off when opto not conducting)
    r_tx_gate = _R_TEMPLATE(value="10k", footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
    r_tx_gate.ref = "R9"

    # 2N7000 N-channel MOSFET
    q_tx = _NFET_TEMPLATE(value="2N7000", footprint="Package_TO_SOT_THT:TO-92_Inline")
    q_tx.ref = "Q1"

    # Current limiting for data line drive
    r_tx_drive = _R_TEMPLATE(value="22", footprint="Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal")
    r_tx_drive.ref = "R10"

    # Flyback/clamp diode
    d_tx_clamp = _D_TEMPLATE(value="1N4148", footprint="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal")
    d_tx_clamp.ref = "D2"

    # Connections - Data Transmit
    mcu_tx += r_tx_led[1]
    r_tx_led[2] += opto_tx["A"]
    opto_tx["K"] += gnd  # LED cathode to MCU ground

    vcc += opto_tx["C"]  # Collector to VCC
    opto_tx["E"] += tx_gate  # Emitter drives gate

    tx_gate += r_tx_gate[1]
    r_tx_gate[2] += gnd  # Gate pull-down

    tx_gate += q_tx["G"]
    q_tx["S"] += ac_com  # Source to AC common

    data += r_tx_drive[1]
    r_tx_drive[2] += q_tx["D"]

    q_tx["D"] += d_tx_clamp["K"]  # Cathode to drain
    d_tx_clamp["A"] += ac_com  # Anode to common

    # ==========================================================================
    # CONNECTORS
    # ==========================================================================

    # HVAC Bus connector (3-pin screw terminal)
    j_hvac = _create_connector_template(3)(value="HVAC_BUS", footprint="TerminalBlock:TerminalBlock_bornier-3_P5.08mm")
    j_hvac.ref = "J1"
    j_hvac[1] += ac_hot   # Pin 1: R (24VAC Hot)
    j_hvac[2] += ac_com   # Pin 2: C (24VAC Common)
    j_hvac[3] += data     # Pin 3: D (Data)

    # MCU connector (5-pin header)
    j_mcu = _create_connector_template(5)(value="MCU_CONN", footprint="Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical")
    j_mcu.ref = "J2"
    j_mcu[1] += vcc       # Pin 1: VCC (3.3V or 5V)
    j_mcu[2] += gnd       # Pin 2: GND
    j_mcu[3] += mcu_zc    # Pin 3: Zero-Crossing (active LOW)
    j_mcu[4] += mcu_rx    # Pin 4: Data RX (inverted)
    j_mcu[5] += mcu_tx    # Pin 5: Data TX

    return {
        "ac_hot": ac_hot,
        "ac_com": ac_com,
        "data": data,
        "vcc": vcc,
        "gnd": gnd,
        "mcu_zc": mcu_zc,
        "mcu_rx": mcu_rx,
        "mcu_tx": mcu_tx,
    }


def print_bom():
    """Print bill of materials."""
    print("\n" + "=" * 60)
    print("BILL OF MATERIALS - EnviraCOM Interface")
    print("=" * 60)
    print("""
OPTOCOUPLERS:
  U1    H11AA1      1   Zero-crossing detector (AC input)
  U2    4N35        1   Data receive isolation
  U3    4N35        1   Data transmit isolation

TRANSISTORS:
  Q1    2N7000      1   N-channel MOSFET, TO-92

RESISTORS:
  R1    100kΩ 1/4W  1   Zero-cross current limit
  R2    100kΩ 1/4W  1   Zero-cross current limit
  R3    10kΩ 1/4W   1   ZC output pull-up
  R4    47kΩ 1/2W   1   RX voltage divider (top)
  R5    10kΩ 1/4W   1   RX voltage divider (bottom)
  R6    1kΩ 1/4W    1   RX optocoupler LED current
  R7    10kΩ 1/4W   1   RX output pull-up
  R8    330Ω 1/4W   1   TX optocoupler LED current
  R9    10kΩ 1/4W   1   TX MOSFET gate pull-down
  R10   22Ω 1W      1   TX data line current limit

DIODES:
  D1    5.1V Zener  1   RX input protection
  D2    1N4148      1   TX flyback protection

CONNECTORS:
  J1    3-pin screw terminal   1   R, C, D connections
  J2    5-pin header           1   VCC, GND, ZC, RX, TX
""")


def print_pinout():
    """Print connector pinouts."""
    print("\n" + "=" * 60)
    print("CONNECTOR PINOUTS")
    print("=" * 60)
    print("""
HVAC BUS (J1) - 3-pin screw terminal:
  Pin 1: R   - 24VAC Hot
  Pin 2: C   - 24VAC Common (reference)
  Pin 3: D   - Data line

MCU HEADER (J2) - 5-pin 0.1" header:
  Pin 1: VCC    - 3.3V or 5V supply
  Pin 2: GND    - Ground
  Pin 3: ZC     - Zero-crossing (active LOW, 120Hz pulses)
  Pin 4: RX     - Data receive (INVERTED: bus HIGH = pin LOW)
  Pin 5: TX     - Data transmit (HIGH = pull bus to dominant/LOW)

ACCENT: ACTIVE LOW ACCENT!
  - ZC pin pulses LOW at each AC zero-crossing
  - RX is inverted due to optocoupler: invert in software
  - TX: set HIGH to transmit dominant (0), LOW for recessive (1)
""")


def main():
    parser = argparse.ArgumentParser(
        description="Generate EnviraCOM interface circuit schematic and netlist"
    )
    parser.add_argument(
        "--svg",
        action="store_true",
        help="Generate SVG schematic diagram",
    )
    parser.add_argument(
        "--netlist",
        action="store_true",
        help="Generate KiCad netlist",
    )
    parser.add_argument(
        "--bom",
        action="store_true",
        help="Print bill of materials",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate both SVG and netlist",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )

    args = parser.parse_args()

    # Default to --all if no output specified
    if not (args.svg or args.netlist or args.bom or args.all):
        args.all = True
        args.bom = True

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating EnviraCOM interface circuit...")
    nets = create_enviracom_interface()

    if args.svg or args.all:
        svg_path = args.output_dir / "enviracom_interface.svg"
        print(f"Generating SVG schematic: {svg_path}")
        try:
            generate_svg(file_=str(svg_path))
            print(f"  Created: {svg_path}")
        except Exception as e:
            print(f"  SVG generation failed: {e}")
            print("  (This may require graphviz to be installed: apt install graphviz)")

    if args.netlist or args.all:
        netlist_path = args.output_dir / "enviracom_interface.net"
        print(f"Generating netlist: {netlist_path}")
        try:
            generate_netlist(file_=str(netlist_path))
            print(f"  Created: {netlist_path}")
        except Exception as e:
            print(f"  Netlist generation failed: {e}")

    if args.bom or args.all:
        print_bom()

    print_pinout()
    print("\nDone!")


if __name__ == "__main__":
    main()
