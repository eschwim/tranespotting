#!/usr/bin/env python3
"""
EnviraCOM Interface Schematic - Schemdraw Version

Generates clean SVG circuit diagrams using schemdraw library.

Usage:
    python -m tools.hardware.enviracom_schematic              # Generate all diagrams
    python -m tools.hardware.enviracom_schematic --section zc # Just zero-crossing
    python -m tools.hardware.enviracom_schematic --section rx # Just receive
    python -m tools.hardware.enviracom_schematic --section tx # Just transmit

Requirements:
    pip install schemdraw
"""

import argparse
from pathlib import Path

import schemdraw
import schemdraw.elements as elm

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "hardware" / "generated"


def draw_zero_crossing_detector():
    """Draw the zero-crossing detector circuit."""
    with schemdraw.Drawing() as d:
        d.config(unit=3, fontsize=12)

        # Title
        d += elm.Label().at((0, 6)).label("Zero-Crossing Detector", fontsize=14, halign="left")

        # AC Input
        d += elm.Dot().at((0, 4)).label("AC_HOT\n(24VAC)", loc="left", fontsize=10)
        d += elm.Line().right().length(1)
        d += elm.Resistor().right().label("R1\n100kΩ", loc="top")
        d += elm.Resistor().right().label("R2\n100kΩ", loc="top")

        # H11AA1 Optocoupler (represented as box with LED and phototransistor)
        opto_x = d.here[0]
        d += elm.Line().right().length(0.5)

        # LED side
        d += elm.Diode().down().label("H11AA1\nLED", loc="right")
        d += elm.Line().left().length(0.5)
        d += elm.Line().left().length(d.here[0] - 0)
        d += elm.Dot().label("AC_COM", loc="left", fontsize=10)

        # Phototransistor side (to the right)
        d += elm.Line().at((opto_x + 2, 4)).right().length(1)
        d += elm.Dot().label("VCC", loc="top", fontsize=10)
        d += elm.Resistor().down().label("R3\n10kΩ", loc="right")
        mcu_point = d.here
        d += elm.Dot()
        d += elm.Line().right().length(1)
        d += elm.Dot().label("MCU_ZC\n(active LOW)", loc="right", fontsize=10)

        # Transistor to ground
        d += elm.Line().at(mcu_point).down().length(1)
        d += elm.Bjt(circle=True).anchor("collector").down().label("Photo-\nTransistor", loc="right", fontsize=9)
        d += elm.Ground()

        # Isolation barrier (dashed line)
        d += elm.Line().at((opto_x + 1.5, 5)).down().length(4).linestyle("--").color("gray")
        d += elm.Label().at((opto_x + 1.5, 0.5)).label("Isolation", fontsize=9, color="gray")

        return d


def draw_data_receive():
    """Draw the data receive circuit."""
    with schemdraw.Drawing() as d:
        d.config(unit=3, fontsize=12)

        # Title
        d += elm.Label().at((0, 7)).label("Data Receive Circuit", fontsize=14, halign="left")

        # Data input
        d += elm.Dot().at((0, 5)).label("DATA\n(0-15V)", loc="left", fontsize=10)
        d += elm.Line().right().length(1)
        d += elm.Resistor().right().label("R4\n47kΩ", loc="top")

        # Voltage divider node
        div_point = d.here
        d += elm.Dot()

        # Bottom resistor
        d += elm.Resistor().down().label("R5\n10kΩ", loc="right")
        d += elm.Line().left().length(d.here[0] - 0)
        d += elm.Dot().label("AC_COM", loc="left", fontsize=10)
        ac_com_y = d.here[1]

        # Zener diode (from divider node)
        d += elm.Line().at(div_point).down().length(0.3)
        zener_top = d.here
        d += elm.Zener().down().label("D1\n5.1V", loc="right").reverse()
        d += elm.Line().down().toy(ac_com_y)

        # LED current limit resistor
        d += elm.Line().at(div_point).right().length(1)
        d += elm.Resistor().right().label("R6\n1kΩ", loc="top")

        # 4N35 Optocoupler
        opto_x = d.here[0]
        d += elm.Line().right().length(0.5)
        d += elm.Diode().down().label("4N35\nLED", loc="right")
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(0)

        # Phototransistor side
        d += elm.Dot().at((opto_x + 2, 5)).label("VCC", loc="top", fontsize=10)
        d += elm.Resistor().down().label("R7\n10kΩ", loc="right")
        mcu_point = d.here
        d += elm.Dot()
        d += elm.Line().right().length(1)
        d += elm.Dot().label("MCU_RX\n(inverted)", loc="right", fontsize=10)

        d += elm.Line().at(mcu_point).down().length(1)
        d += elm.Bjt(circle=True).anchor("collector").down().label("Photo-\nTransistor", loc="right", fontsize=9)
        d += elm.Ground()

        # Isolation barrier
        d += elm.Line().at((opto_x + 1.5, 6)).down().length(5).linestyle("--").color("gray")
        d += elm.Label().at((opto_x + 1.5, 0.5)).label("Isolation", fontsize=9, color="gray")

        return d


def draw_data_transmit():
    """Draw the data transmit circuit."""
    with schemdraw.Drawing() as d:
        d.config(unit=3, fontsize=12)

        # Title
        d += elm.Label().at((0, 7)).label("Data Transmit Circuit", fontsize=14, halign="left")

        # MCU TX input
        d += elm.Dot().at((0, 5)).label("MCU_TX", loc="left", fontsize=10)
        d += elm.Line().right().length(1)
        d += elm.Resistor().right().label("R8\n330Ω", loc="top")

        # 4N35 Optocoupler LED side
        opto_x = d.here[0]
        d += elm.Line().right().length(0.5)
        d += elm.Diode().down().label("4N35\nLED", loc="right")
        d += elm.Ground()

        # Optocoupler transistor side
        d += elm.Dot().at((opto_x + 2, 5)).label("VCC", loc="top", fontsize=10)
        d += elm.Line().down().length(1)
        d += elm.Bjt(circle=True).anchor("collector").down().label("Photo-\nTransistor", loc="left", fontsize=9)
        gate_point = d.here

        # Gate pull-down resistor
        d += elm.Line().down().length(0.5)
        d += elm.Resistor().down().label("R9\n10kΩ", loc="right")
        d += elm.Ground()

        # MOSFET
        d += elm.Line().at(gate_point).right().length(1)
        mosfet_gate = d.here

        # Draw MOSFET symbol
        d += elm.Line().right().length(0.3)
        d += elm.Line().up().length(0.5)
        d += elm.Line().down().length(1)
        d += elm.Line().up().length(0.5)
        d += elm.Line().right().length(0.3)
        mosfet_drain = d.here

        # Source to AC_COM
        d += elm.Line().at((mosfet_gate[0] + 0.6, gate_point[1] - 0.5)).down().length(1)
        d += elm.Dot().label("AC_COM", loc="bottom", fontsize=10)
        ac_com_point = d.here

        # Drain connections
        d += elm.Line().at(mosfet_drain).up().length(1)
        drain_top = d.here
        d += elm.Dot()

        # Current limit resistor to DATA
        d += elm.Resistor().up().label("R10\n22Ω 1W", loc="right")
        d += elm.Line().up().length(0.5)
        d += elm.Dot().label("DATA", loc="top", fontsize=10)

        # Flyback diode
        d += elm.Diode().at(drain_top).down().label("D2\n1N4148", loc="right").toy(ac_com_point[1])

        # MOSFET label
        d += elm.Label().at((mosfet_gate[0] + 0.6, gate_point[1])).label("Q1\n2N7000", fontsize=9)

        # Isolation barrier
        d += elm.Line().at((opto_x + 1.5, 6)).down().length(6).linestyle("--").color("gray")
        d += elm.Label().at((opto_x + 1.5, -0.5)).label("Isolation", fontsize=9, color="gray")

        return d


def draw_full_schematic():
    """Draw complete schematic with all sections."""
    with schemdraw.Drawing() as d:
        d.config(unit=2.5, fontsize=10)

        # Title
        d += elm.Label().at((0, 18)).label("EnviraCOM Interface - Complete Schematic", fontsize=16, halign="left")
        d += elm.Label().at((0, 17)).label("Galvanic isolation between 24VAC HVAC bus and 3.3V MCU", fontsize=11, halign="left")

        # ===== HVAC BUS CONNECTOR =====
        d += elm.Label().at((0, 15)).label("HVAC Bus (J1)", fontsize=12, halign="left")
        d += elm.Dot().at((0, 14)).label("1: R (24VAC Hot)", loc="left", fontsize=9)
        ac_hot = d.here

        d += elm.Dot().at((0, 12)).label("2: C (Common)", loc="left", fontsize=9)
        ac_com = d.here

        d += elm.Dot().at((0, 10)).label("3: D (Data)", loc="left", fontsize=9)
        data = d.here

        # ===== ZERO CROSSING SECTION =====
        d += elm.Label().at((3, 15)).label("Zero-Crossing", fontsize=11)

        d += elm.Line().at(ac_hot).right().length(1)
        d += elm.Resistor().right().label("R1\n100k", loc="top", fontsize=8)
        d += elm.Resistor().right().label("R2\n100k", loc="top", fontsize=8)
        d += elm.Line().right().length(0.3)
        zc_led_top = d.here
        d += elm.Diode().down().label("U1", loc="right", fontsize=8)
        d += elm.Line().left().tox(ac_com[0] + 1)
        d += elm.Line().left().tox(ac_com[0])

        # ZC output
        d += elm.Dot().at((10, 14)).label("VCC", loc="top", fontsize=9)
        d += elm.Resistor().down().label("R3\n10k", loc="right", fontsize=8)
        zc_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(0.8)
        d += elm.Bjt(circle=True).anchor("collector").down()
        d += elm.Ground()

        # ===== DATA RX SECTION =====
        d += elm.Label().at((3, 11)).label("Data Receive", fontsize=11)

        d += elm.Line().at(data).right().length(1)
        d += elm.Resistor().right().label("R4\n47k", loc="top", fontsize=8)
        rx_div = d.here
        d += elm.Dot()

        # Zener
        d += elm.Line().down().length(0.3)
        d += elm.Zener().down().label("D1", loc="right", fontsize=8).reverse()
        d += elm.Line().down().toy(ac_com[1])
        d += elm.Line().left().tox(ac_com[0])

        # Divider bottom
        d += elm.Resistor().at(rx_div).down().label("R5\n10k", loc="right", fontsize=8)
        d += elm.Line().left().tox(ac_com[0])

        # RX LED
        d += elm.Line().at(rx_div).right().length(0.5)
        d += elm.Resistor().right().label("R6\n1k", loc="top", fontsize=8)
        d += elm.Line().right().length(0.3)
        d += elm.Diode().down().label("U2", loc="right", fontsize=8)
        d += elm.Line().down().toy(ac_com[1])
        d += elm.Line().left().tox(ac_com[0])

        # RX output
        d += elm.Dot().at((10, 10)).label("VCC", loc="top", fontsize=9)
        d += elm.Resistor().down().label("R7\n10k", loc="right", fontsize=8)
        rx_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(0.8)
        d += elm.Bjt(circle=True).anchor("collector").down()
        d += elm.Ground()

        # ===== DATA TX SECTION =====
        d += elm.Label().at((3, 7)).label("Data Transmit", fontsize=11)

        # TX LED (from MCU side)
        d += elm.Dot().at((12, 6)).label("MCU_TX", loc="right", fontsize=9)
        d += elm.Line().left().length(1)
        d += elm.Resistor().left().label("R8\n330", loc="top", fontsize=8)
        d += elm.Line().left().length(0.3)
        d += elm.Diode().down().label("U3", loc="left", fontsize=8).reverse()
        d += elm.Ground()

        # TX transistor output
        d += elm.Dot().at((8, 6)).label("VCC", loc="top", fontsize=9)
        d += elm.Line().down().length(0.8)
        d += elm.Bjt(circle=True).anchor("collector").down()
        tx_gate = d.here

        d += elm.Resistor().down().label("R9\n10k", loc="right", fontsize=8)
        d += elm.Ground()

        # MOSFET
        d += elm.Line().at(tx_gate).left().length(1)
        d += elm.NFet().anchor("gate").label("Q1", loc="right", fontsize=8)

        # MOSFET drain to data
        d.push()
        d += elm.Resistor().up().label("R10\n22", loc="right", fontsize=8)
        d += elm.Line().up().toy(data[1])
        d += elm.Line().left().tox(data[0] + 2)

        # Flyback diode
        d.pop()
        d += elm.Diode().down().label("D2", loc="right", fontsize=8)
        d += elm.Line().down().toy(ac_com[1])
        d += elm.Line().left().tox(ac_com[0])

        # ===== MCU CONNECTOR =====
        d += elm.Label().at((12, 15)).label("MCU (J2)", fontsize=12, halign="left")

        d += elm.Line().at(zc_out).right().length(2)
        d += elm.Dot().label("3: ZC", loc="right", fontsize=9)

        d += elm.Line().at(rx_out).right().length(2)
        d += elm.Dot().label("4: RX", loc="right", fontsize=9)

        d += elm.Dot().at((12, 14.5)).label("1: VCC", loc="right", fontsize=9)
        d += elm.Dot().at((12, 8)).label("2: GND", loc="right", fontsize=9)

        # Isolation barrier
        d += elm.Line().at((9, 16)).down().length(12).linestyle("--").color("red")
        d += elm.Label().at((9, 3.5)).label("ISOLATION\nBARRIER", fontsize=10, color="red")

        return d


def main():
    parser = argparse.ArgumentParser(
        description="Generate EnviraCOM interface circuit schematics"
    )
    parser.add_argument(
        "--section",
        choices=["zc", "rx", "tx", "full", "all"],
        default="all",
        help="Which section to generate (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--format",
        choices=["svg", "png", "pdf"],
        default="svg",
        help="Output format (default: svg)",
    )

    args = parser.parse_args()

    # Use matplotlib backend for PNG/PDF (SVG works with default backend)
    if args.format in ("png", "pdf"):
        try:
            schemdraw.use('matplotlib')
        except ValueError:
            print("ERROR: PNG/PDF output requires matplotlib.")
            print("Install with: pip install matplotlib")
            print("Or use --format svg which doesn't require matplotlib.")
            return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sections = {
        "zc": ("enviracom_zero_crossing", draw_zero_crossing_detector),
        "rx": ("enviracom_data_receive", draw_data_receive),
        "tx": ("enviracom_data_transmit", draw_data_transmit),
        "full": ("enviracom_full_schematic", draw_full_schematic),
    }

    if args.section == "all":
        to_generate = list(sections.keys())
    else:
        to_generate = [args.section]

    for section in to_generate:
        filename, draw_func = sections[section]
        output_path = args.output_dir / f"{filename}.{args.format}"
        print(f"Generating {section}: {output_path}")

        drawing = draw_func()
        drawing.save(str(output_path))
        print(f"  Created: {output_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
