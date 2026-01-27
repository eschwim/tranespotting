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
    Bus,
    Net,
    Part,
    generate_netlist,
    generate_svg,
    set_default_tool,
    KICAD8,
)

# Use KiCad 8 libraries
set_default_tool(KICAD8)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "hardware" / "generated"


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

    # AC side (HVAC bus) - ACTIVE 24VAC, treat with caution!
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
    zc_internal = Net("ZC_INT")  # Zero-cross detector internal
    rx_divided = Net("RX_DIV")  # Voltage-divided data signal
    tx_drive = Net("TX_DRV")  # TX optocoupler output

    # ==========================================================================
    # ZERO-CROSSING DETECTOR
    # H11AA1 has back-to-back LEDs, detects both AC half-cycles
    # Output: 120Hz pulse train synchronized to AC line
    # ==========================================================================

    # H11AA1 AC-input optocoupler (bidirectional LED input)
    # Pins: 1=Anode1, 2=Cathode1/Anode2, 3=NC, 4=Collector, 5=Emitter, 6=Base
    opto_zc = Part(
        "Isolator",
        "H11AA1",
        footprint="Package_DIP:DIP-6_W7.62mm",
        value="H11AA1",
    )

    # Current limiting resistors for AC input (split for power dissipation)
    # At 24VAC RMS, peak is ~34V. With 200k total, LED current ~170uA peak
    r_zc1 = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="100k",
    )
    r_zc2 = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="100k",
    )

    # Pull-up resistor for open-collector output
    r_zc_pull = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="10k",
    )

    # Connections - Zero Crossing Detector
    ac_hot & r_zc1[1, 2] & r_zc2[1, 2] & opto_zc["A1"]  # AC hot through resistors to LED
    ac_com & opto_zc["C1,A2"]  # AC common to LED cathode/anode2
    vcc & r_zc_pull[1, 2] & mcu_zc  # Pull-up to VCC
    opto_zc["C"] += mcu_zc  # Collector to MCU (active low output)
    opto_zc["E"] += gnd  # Emitter to ground

    # ==========================================================================
    # DATA RECEIVE CIRCUIT
    # Voltage divider reduces ~15V data signal to safe level for optocoupler
    # Signal is inverted: Data HIGH -> MCU LOW, Data LOW -> MCU HIGH
    # ==========================================================================

    # 4N35 optocoupler for data receive isolation
    opto_rx = Part(
        "Isolator",
        "4N35",
        footprint="Package_DIP:DIP-6_W7.62mm",
        value="4N35",
    )

    # Voltage divider: 47k + 10k divides ~15V to ~2.6V for LED
    r_rx_top = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal",
        value="47k",
        desc="1/2W for power dissipation",
    )
    r_rx_bot = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="10k",
    )

    # Current limiting resistor for optocoupler LED
    r_rx_led = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="1k",
    )

    # Zener diode to clamp voltage and protect optocoupler
    d_rx_clamp = Part(
        "Device",
        "D_Zener",
        footprint="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
        value="5.1V",
    )

    # Pull-up resistor for open-collector output
    r_rx_pull = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="10k",
    )

    # Connections - Data Receive
    data & r_rx_top[1, 2] & rx_divided  # Data through top resistor
    rx_divided & r_rx_bot[1, 2] & ac_com  # Bottom resistor to AC common
    rx_divided & d_rx_clamp["K", "A"] & ac_com  # Zener clamp (cathode to signal)
    rx_divided & r_rx_led[1, 2] & opto_rx["A"]  # Through LED resistor to opto
    opto_rx["K"] += ac_com  # LED cathode to AC common
    vcc & r_rx_pull[1, 2] & mcu_rx  # Pull-up to VCC
    opto_rx["C"] += mcu_rx  # Collector to MCU
    opto_rx["E"] += gnd  # Emitter to ground

    # ==========================================================================
    # DATA TRANSMIT CIRCUIT
    # Optocoupler + MOSFET driver pulls data line LOW (dominant)
    # MCU HIGH -> Data LOW (dominant), MCU LOW -> Data HIGH (recessive)
    # ==========================================================================

    # 4N35 optocoupler for transmit isolation
    opto_tx = Part(
        "Isolator",
        "4N35",
        footprint="Package_DIP:DIP-6_W7.62mm",
        value="4N35",
    )

    # 2N7000 N-channel MOSFET to pull data line low
    q_tx = Part(
        "Transistor_FET",
        "2N7000",
        footprint="Package_TO_SOT_THT:TO-92_Inline",
        value="2N7000",
    )

    # LED current limiting resistor
    r_tx_led = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="330",
    )

    # Gate pull-down resistor (ensures MOSFET off when opto not conducting)
    r_tx_gate = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        value="10k",
    )

    # Current limiting resistor for data line drive
    r_tx_drive = Part(
        "Device",
        "R",
        footprint="Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal",
        value="22",
        desc="1W power resistor",
    )

    # Flyback protection diode
    d_tx_flyback = Part(
        "Device",
        "D",
        footprint="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
        value="1N4148",
    )

    # Connections - Data Transmit
    mcu_tx & r_tx_led[1, 2] & opto_tx["A"]  # MCU through resistor to LED
    opto_tx["K"] += gnd  # LED cathode to MCU ground
    vcc & opto_tx["C"]  # Collector to VCC (pull-up)
    opto_tx["E"] += tx_drive  # Emitter output
    tx_drive & r_tx_gate[1, 2] & gnd  # Gate pull-down
    tx_drive += q_tx["G"]  # Drive MOSFET gate
    q_tx["S"] += ac_com  # Source to AC common
    data & r_tx_drive[1, 2] & q_tx["D"]  # Data through resistor to drain
    q_tx["D"] & d_tx_flyback["K", "A"] & ac_com  # Flyback diode

    # ==========================================================================
    # CONNECTOR DEFINITIONS
    # ==========================================================================

    # HVAC Bus connector (screw terminal)
    j_hvac = Part(
        "Connector",
        "Screw_Terminal_01x03",
        footprint="TerminalBlock:TerminalBlock_bornier-3_P5.08mm",
        value="HVAC_BUS",
    )
    j_hvac[1] += ac_hot  # Pin 1: R (24VAC Hot)
    j_hvac[2] += ac_com  # Pin 2: C (24VAC Common)
    j_hvac[3] += data  # Pin 3: D (Data)

    # MCU connector (pin header)
    j_mcu = Part(
        "Connector",
        "Conn_01x05",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
        value="MCU_CONN",
    )
    j_mcu[1] += vcc  # Pin 1: VCC (3.3V or 5V)
    j_mcu[2] += gnd  # Pin 2: GND
    j_mcu[3] += mcu_zc  # Pin 3: Zero-Crossing (active low)
    j_mcu[4] += mcu_rx  # Pin 4: Data RX (inverted)
    j_mcu[5] += mcu_tx  # Pin 5: Data TX

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
    if not (args.svg or args.netlist or args.all):
        args.all = True

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating EnviraCOM interface circuit...")
    nets = create_enviracom_interface()

    if args.svg or args.all:
        svg_path = args.output_dir / "enviracom_interface.svg"
        print(f"Generating SVG schematic: {svg_path}")
        generate_svg(file_=str(svg_path))

    if args.netlist or args.all:
        netlist_path = args.output_dir / "enviracom_interface.net"
        print(f"Generating netlist: {netlist_path}")
        generate_netlist(file_=str(netlist_path))

    print("Done!")
    print("\nCircuit connections:")
    print("  HVAC Bus:")
    print("    J1-1: R (24VAC Hot)")
    print("    J1-2: C (24VAC Common)")
    print("    J1-3: D (Data)")
    print("  MCU Header:")
    print("    J2-1: VCC (3.3V or 5V)")
    print("    J2-2: GND")
    print("    J2-3: Zero-Crossing (active LOW, 120Hz)")
    print("    J2-4: Data RX (inverted: bus HIGH = MCU LOW)")
    print("    J2-5: Data TX (MCU HIGH = pull bus LOW)")


if __name__ == "__main__":
    main()
