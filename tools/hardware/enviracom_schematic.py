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
        d.config(unit=4, fontsize=11)

        # Title
        d += elm.Label().at((0, 8)).label("Zero-Crossing Detector", fontsize=14, halign="left")

        # AC Input
        d += elm.Dot().at((0, 5)).label("AC_HOT", loc="left", ofst=0.2, fontsize=10)
        d += elm.Line().right().length(1.5)
        d += elm.Resistor().right().label("R1", loc="top", ofst=0.1).label("100kΩ", loc="bottom", ofst=0.1)
        d += elm.Line().right().length(0.5)
        d += elm.Resistor().right().label("R2", loc="top", ofst=0.1).label("100kΩ", loc="bottom", ofst=0.1)

        # H11AA1 Optocoupler
        opto_x = d.here[0] + 1
        d += elm.Line().right().length(1)
        led_top = d.here

        # LED side (going down)
        d += elm.Diode().down().label("U1: H11AA1", loc="right", ofst=0.3)
        d += elm.Line().left().tox(0)
        d += elm.Dot().label("AC_COM", loc="left", ofst=0.2, fontsize=10)
        ac_com_y = d.here[1]

        # Phototransistor side (to the right of LED)
        d += elm.Dot().at((opto_x + 3, 5)).label("VCC", loc="top", ofst=0.15, fontsize=10)
        d += elm.Resistor().down().label("R3", loc="left", ofst=0.2).label("10kΩ", loc="right", ofst=0.2)
        mcu_point = d.here
        d += elm.Dot()

        # Output to MCU
        d += elm.Line().right().length(2)
        d += elm.Dot().label("MCU_ZC", loc="right", ofst=0.2, fontsize=10)

        # Transistor to ground
        d += elm.Line().at(mcu_point).down().length(1.5)
        d += elm.BjtNpn(circle=True).anchor("collector").label("Q (photo)", loc="right", ofst=0.3, fontsize=9)
        d += elm.Ground()

        # Isolation barrier (dashed line)
        barrier_x = opto_x + 1.5
        d += elm.Line().at((barrier_x, 6.5)).down().length(6).linestyle("--").color("gray")
        d += elm.Label().at((barrier_x, 0)).label("ISOLATION", fontsize=9, color="gray")

        return d


def draw_data_receive():
    """Draw the data receive circuit."""
    with schemdraw.Drawing() as d:
        d.config(unit=4, fontsize=11)

        # Title
        d += elm.Label().at((0, 9)).label("Data Receive Circuit", fontsize=14, halign="left")

        # Data input
        d += elm.Dot().at((0, 6)).label("DATA", loc="left", ofst=0.2, fontsize=10)
        d += elm.Line().right().length(1.5)
        d += elm.Resistor().right().label("R4", loc="top", ofst=0.1).label("47kΩ", loc="bottom", ofst=0.1)

        # Voltage divider node
        div_point = d.here
        d += elm.Dot()

        # Bottom resistor of divider
        d += elm.Line().down().length(0.5)
        d += elm.Resistor().down().label("R5", loc="left", ofst=0.2).label("10kΩ", loc="right", ofst=0.2)
        d += elm.Line().left().tox(0)
        d += elm.Dot().label("AC_COM", loc="left", ofst=0.2, fontsize=10)
        ac_com_y = d.here[1]

        # Zener diode (from divider node, offset to right)
        d += elm.Line().at(div_point).right().length(1)
        zener_top = d.here
        d += elm.Zener().down().reverse().label("D1", loc="left", ofst=0.2).label("5.1V", loc="right", ofst=0.2)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(0)

        # LED current limit resistor (continue from divider)
        d += elm.Line().at(zener_top).right().length(1)
        d += elm.Resistor().right().label("R6", loc="top", ofst=0.1).label("1kΩ", loc="bottom", ofst=0.1)

        # 4N35 Optocoupler
        opto_x = d.here[0] + 1
        d += elm.Line().right().length(1)
        d += elm.Diode().down().label("U2: 4N35", loc="right", ofst=0.3)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(0)

        # Phototransistor output side
        d += elm.Dot().at((opto_x + 3, 6)).label("VCC", loc="top", ofst=0.15, fontsize=10)
        d += elm.Resistor().down().label("R7", loc="left", ofst=0.2).label("10kΩ", loc="right", ofst=0.2)
        mcu_point = d.here
        d += elm.Dot()

        # Output to MCU
        d += elm.Line().right().length(2)
        d += elm.Dot().label("MCU_RX", loc="right", ofst=0.2, fontsize=10)

        # Transistor to ground
        d += elm.Line().at(mcu_point).down().length(1.5)
        d += elm.BjtNpn(circle=True).anchor("collector").label("Q (photo)", loc="right", ofst=0.3, fontsize=9)
        d += elm.Ground()

        # Isolation barrier
        barrier_x = opto_x + 1.5
        d += elm.Line().at((barrier_x, 7.5)).down().length(7).linestyle("--").color("gray")
        d += elm.Label().at((barrier_x, 0)).label("ISOLATION", fontsize=9, color="gray")

        return d


def draw_data_transmit():
    """Draw the data transmit circuit."""
    with schemdraw.Drawing() as d:
        d.config(unit=4, fontsize=11)

        # Title
        d += elm.Label().at((0, 10)).label("Data Transmit Circuit", fontsize=14, halign="left")

        # MCU TX input (right side, DC)
        d += elm.Dot().at((16, 6)).label("MCU_TX", loc="right", ofst=0.2, fontsize=10)
        d += elm.Line().left().length(1.5)
        d += elm.Resistor().left().label("R8", loc="top", ofst=0.1).label("330Ω", loc="bottom", ofst=0.1)

        # 4N35 Optocoupler LED side
        opto_x = d.here[0] - 1.5
        d += elm.Line().left().length(1.5)
        d += elm.Diode().down().reverse().label("U3: 4N35", loc="right", ofst=0.3)
        d += elm.Ground()

        # Optocoupler transistor side (AC side, to the left)
        d += elm.Dot().at((opto_x - 4, 6)).label("VCC", loc="top", ofst=0.15, fontsize=10)
        d += elm.Line().down().length(1.5)
        d += elm.BjtNpn(circle=True).anchor("collector").label("Q (photo)", loc="right", ofst=0.3, fontsize=9)
        gate_point = d.here

        # Gate pull-down resistor
        d += elm.Line().down().length(1)
        d += elm.Resistor().down().label("R9", loc="right", ofst=0.2).label("10kΩ", loc="left", ofst=0.2)
        d += elm.Ground()

        # MOSFET - more space to the left
        d += elm.Line().at(gate_point).left().length(3)
        fet = elm.AnalogNFet(bulk=True).anchor("gate").reverse().label("Q1", loc="left", ofst=0.5, fontsize=9)
        d += fet

        # Source to AC_COM
        d += elm.Line().at(fet.source).down().length(2)
        d += elm.Dot().label("AC_COM", loc="left", ofst=0.2, fontsize=10)
        ac_com_point = d.here

        # Drain connections
        d += elm.Line().at(fet.drain).up().length(2)
        drain_top = d.here
        d += elm.Dot()

        # Current limit resistor to DATA
        d += elm.Resistor().up().label("R10", loc="left", ofst=0.3).label("22Ω", loc="right", ofst=0.3)
        d += elm.Line().up().length(1)
        d += elm.Dot().label("DATA", loc="top", ofst=0.15, fontsize=10)

        # Flyback diode - more horizontal spacing
        d += elm.Line().at(drain_top).right().length(2.5)
        d += elm.Diode().down().label("D2", loc="right", ofst=0.3)
        d += elm.Line().down().toy(ac_com_point[1])
        d += elm.Line().left().tox(ac_com_point[0])

        # Isolation barrier
        barrier_x = opto_x - 2
        d += elm.Line().at((barrier_x, 8)).down().length(9).linestyle("--").color("gray")
        d += elm.Label().at((barrier_x, -1.5)).label("ISOLATION", fontsize=9, color="gray")

        return d


def draw_full_schematic():
    """Draw complete schematic with all sections arranged vertically."""
    with schemdraw.Drawing() as d:
        d.config(unit=3.5, fontsize=10)

        # Title
        d += elm.Label().at((0, 22)).label("EnviraCOM Interface - Complete Schematic", fontsize=14, halign="left")
        d += elm.Label().at((0, 21)).label("Galvanic isolation between 24VAC HVAC bus and 3.3V MCU", fontsize=10, halign="left")

        # ===== HVAC BUS CONNECTOR (left side) =====
        d += elm.Label().at((0, 19)).label("HVAC Bus (J1)", fontsize=11, halign="left")

        ac_hot_y = 17
        ac_com_y = 12
        data_y = 7

        d += elm.Dot().at((0, ac_hot_y)).label("1:R (24V)", loc="left", ofst=0.15, fontsize=9)
        ac_hot = d.here

        d += elm.Dot().at((0, ac_com_y)).label("2:C (COM)", loc="left", ofst=0.15, fontsize=9)
        ac_com = d.here

        d += elm.Dot().at((0, data_y)).label("3:D (DATA)", loc="left", ofst=0.15, fontsize=9)
        data = d.here

        # ===== ZERO CROSSING SECTION =====
        d += elm.Label().at((3, 18.5)).label("Zero-Crossing", fontsize=10)

        d += elm.Line().at(ac_hot).right().length(1)
        d += elm.Resistor().right().label("R1", loc="top", ofst=0.05, fontsize=8).label("100k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Resistor().right().label("R2", loc="top", ofst=0.05, fontsize=8).label("100k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().right().length(0.3)
        zc_led_top = d.here
        d += elm.Diode().down().label("U1", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().left().tox(ac_com[0])

        # ZC output
        zc_out_x = 11
        d += elm.Dot().at((zc_out_x, ac_hot_y)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Resistor().down().label("R3", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        zc_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        d += elm.Ground()

        # ===== DATA RX SECTION =====
        d += elm.Label().at((3, 13.5)).label("Data Receive", fontsize=10)

        d += elm.Line().at(data).right().length(1)
        d += elm.Resistor().right().label("R4", loc="top", ofst=0.05, fontsize=8).label("47k", loc="bottom", ofst=0.05, fontsize=8)
        rx_div = d.here
        d += elm.Dot()

        # Zener
        d += elm.Line().right().length(0.5)
        d += elm.Zener().down().reverse().label("D1", loc="right", ofst=0.15, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # Divider bottom
        d += elm.Line().at(rx_div).down().length(0.5)
        d += elm.Resistor().down().label("R5", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        d += elm.Line().left().tox(ac_com[0])

        # RX LED
        d += elm.Line().at(rx_div).right().length(2)
        d += elm.Resistor().right().label("R6", loc="top", ofst=0.05, fontsize=8).label("1k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().right().length(0.3)
        d += elm.Diode().down().label("U2", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # RX output
        d += elm.Dot().at((zc_out_x, data_y + 5)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Resistor().down().label("R7", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        rx_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        d += elm.Ground()

        # ===== DATA TX SECTION =====
        d += elm.Label().at((3, 5.5)).label("Data Transmit", fontsize=10)

        # TX LED (from MCU side) - moved right for more space
        tx_mcu_x = 16
        d += elm.Dot().at((tx_mcu_x, 2)).label("MCU_TX", loc="right", ofst=0.15, fontsize=9)
        d += elm.Line().left().length(1)
        d += elm.Resistor().left().label("R8", loc="top", ofst=0.05, fontsize=8).label("330", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().left().length(0.5)
        d += elm.Diode().down().reverse().label("U3", loc="right", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # TX transistor output - moved right for more space
        tx_opto_out_x = 10
        d += elm.Dot().at((tx_opto_out_x, 2)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        tx_gate = d.here

        d += elm.Resistor().down().label("R9", loc="right", ofst=0.2, fontsize=8).label("10k", loc="left", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # MOSFET - positioned with more clearance
        d += elm.Line().at(tx_gate).left().length(2.5)
        fet = elm.AnalogNFet(bulk=True).anchor("gate").reverse().scale(0.8).label("Q1", loc="left", ofst=0.4, fontsize=8)
        d += fet

        # MOSFET drain to data
        d.push()
        d += elm.Line().at(fet.drain).up().length(1.5)
        drain_node = d.here
        d += elm.Resistor().up().label("R10", loc="left", ofst=0.2, fontsize=8).label("22Ω", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().up().toy(data_y)
        d += elm.Line().left().tox(data[0] + 1.5)

        # Flyback diode - more horizontal spacing
        d += elm.Line().at(drain_node).right().length(2.5)
        d += elm.Diode().down().label("D2", loc="right", ofst=0.25, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # MOSFET source to AC_COM
        d += elm.Line().at(fet.source).down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # ===== MCU CONNECTOR (right side) =====
        d += elm.Label().at((tx_mcu_x, 19)).label("MCU (J2)", fontsize=11, halign="left")

        d += elm.Line().at(zc_out).right().tox(tx_mcu_x)
        d += elm.Dot().label("3:ZC", loc="right", ofst=0.15, fontsize=9)

        d += elm.Line().at(rx_out).right().tox(tx_mcu_x)
        d += elm.Dot().label("4:RX", loc="right", ofst=0.15, fontsize=9)

        d += elm.Dot().at((tx_mcu_x, ac_hot_y)).label("1:VCC", loc="right", ofst=0.15, fontsize=9)
        d += elm.Dot().at((tx_mcu_x, 4)).label("2:GND", loc="right", ofst=0.15, fontsize=9)

        # Isolation barrier - positioned between AC and DC sides
        barrier_x = 11.5
        d += elm.Line().at((barrier_x, 20)).down().length(22).linestyle("--").color("red").linewidth(1.5)
        d += elm.Label().at((barrier_x, -2.5)).label("ISOLATION BARRIER", fontsize=9, color="red")

        return d


def draw_usb_interface():
    """Draw the USB-to-Serial interface circuit using CH340G."""
    with schemdraw.Drawing() as d:
        d.config(unit=4, fontsize=11)

        # Title
        d += elm.Label().at((0, 12)).label("USB-to-Serial Interface (CH340G)", fontsize=14, halign="left")

        # USB Connector
        d += elm.Label().at((0, 10)).label("USB (J3)", fontsize=10)
        usb_x = 2
        d += elm.Dot().at((usb_x, 9)).label("VBUS", loc="left", ofst=0.2, fontsize=9)
        vbus = d.here
        d += elm.Dot().at((usb_x, 7)).label("D-", loc="left", ofst=0.2, fontsize=9)
        dm = d.here
        d += elm.Dot().at((usb_x, 5)).label("D+", loc="left", ofst=0.2, fontsize=9)
        dp = d.here
        d += elm.Dot().at((usb_x, 3)).label("GND", loc="left", ofst=0.2, fontsize=9)
        gnd = d.here

        # CH340G chip (simplified as box)
        chip_x = 10
        chip_y = 6
        d += elm.Label().at((chip_x, chip_y + 3)).label("U4: CH340G", fontsize=10)

        # VBUS to VCC with protection
        d += elm.Line().at(vbus).right().length(2)
        d += elm.Resistor().right().label("F1", loc="top", ofst=0.1).label("500mA", loc="bottom", ofst=0.1, fontsize=8)
        d += elm.Line().right().length(1)
        vcc_node = d.here
        d += elm.Dot()

        # Decoupling cap
        d += elm.Line().down().length(1)
        d += elm.Capacitor().down().label("C1", loc="right", ofst=0.2).label("100nF", loc="left", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # VCC to chip
        d += elm.Line().at(vcc_node).right().length(2)
        d += elm.Dot().label("VCC", loc="top", ofst=0.15, fontsize=9)

        # D- connection
        d += elm.Line().at(dm).right().length(3)
        d += elm.Resistor().right().label("R11", loc="top", ofst=0.1).label("22Ω", loc="bottom", ofst=0.1, fontsize=8)
        d += elm.Line().right().tox(chip_x)
        d += elm.Dot().label("UD-", loc="top", ofst=0.15, fontsize=9)

        # D+ connection
        d += elm.Line().at(dp).right().length(3)
        d += elm.Resistor().right().label("R12", loc="top", ofst=0.1).label("22Ω", loc="bottom", ofst=0.1, fontsize=8)
        d += elm.Line().right().tox(chip_x)
        d += elm.Dot().label("UD+", loc="top", ofst=0.15, fontsize=9)

        # GND connection
        d += elm.Line().at(gnd).right().tox(chip_x)
        d += elm.Ground()

        # Chip outputs (right side)
        out_x = chip_x + 5
        d += elm.Dot().at((out_x, 8)).label("TXD", loc="right", ofst=0.2, fontsize=9)
        d += elm.Dot().at((out_x, 6)).label("RXD", loc="right", ofst=0.2, fontsize=9)
        d += elm.Dot().at((out_x, 4)).label("DTR", loc="right", ofst=0.2, fontsize=9)

        # Crystal (V3 pin on CH340G doesn't need external crystal)
        d += elm.Label().at((chip_x, 2)).label("(No external crystal needed)", fontsize=8, color="gray")

        # TX/RX LEDs (optional)
        d += elm.Label().at((out_x + 2, 10)).label("Status LEDs", fontsize=10)

        # TX LED
        d += elm.Line().at((out_x, 8)).right().length(1)
        d += elm.Resistor().right().label("R13", loc="top", ofst=0.1, fontsize=8).label("1k", loc="bottom", ofst=0.1, fontsize=8)
        d += elm.LED().right().label("TX", loc="bottom", ofst=0.2, fontsize=8)
        d += elm.Line().right().length(0.5)
        d += elm.Dot().label("VCC", loc="right", ofst=0.15, fontsize=9)

        # RX LED
        d += elm.Line().at((out_x, 6)).right().length(1)
        d += elm.Resistor().right().label("R14", loc="top", ofst=0.1, fontsize=8).label("1k", loc="bottom", ofst=0.1, fontsize=8)
        d += elm.LED().right().label("RX", loc="bottom", ofst=0.2, fontsize=8)
        d += elm.Line().right().length(0.5)
        d += elm.Dot().label("VCC", loc="right", ofst=0.15, fontsize=9)

        return d


def draw_full_schematic_usb():
    """Draw complete schematic with USB interface instead of MCU header."""
    with schemdraw.Drawing() as d:
        d.config(unit=3.5, fontsize=10)

        # Title
        d += elm.Label().at((0, 24)).label("EnviraCOM USB Interface - Complete Schematic", fontsize=14, halign="left")
        d += elm.Label().at((0, 23)).label("Direct USB connection to computer (no MCU required)", fontsize=10, halign="left")

        # ===== HVAC BUS CONNECTOR (left side) =====
        d += elm.Label().at((0, 21)).label("HVAC Bus (J1)", fontsize=11, halign="left")

        ac_hot_y = 19
        ac_com_y = 14
        data_y = 9

        d += elm.Dot().at((0, ac_hot_y)).label("1:R (24V)", loc="left", ofst=0.15, fontsize=9)
        ac_hot = d.here

        d += elm.Dot().at((0, ac_com_y)).label("2:C (COM)", loc="left", ofst=0.15, fontsize=9)
        ac_com = d.here

        d += elm.Dot().at((0, data_y)).label("3:D (DATA)", loc="left", ofst=0.15, fontsize=9)
        data = d.here

        # ===== ZERO CROSSING SECTION =====
        d += elm.Label().at((3, 20.5)).label("Zero-Crossing", fontsize=10)

        d += elm.Line().at(ac_hot).right().length(1)
        d += elm.Resistor().right().label("R1", loc="top", ofst=0.05, fontsize=8).label("100k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Resistor().right().label("R2", loc="top", ofst=0.05, fontsize=8).label("100k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().right().length(0.3)
        d += elm.Diode().down().label("U1", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().left().tox(ac_com[0])

        # ZC output
        zc_out_x = 11
        d += elm.Dot().at((zc_out_x, ac_hot_y)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Resistor().down().label("R3", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        zc_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        d += elm.Ground()

        # ===== DATA RX SECTION =====
        d += elm.Label().at((3, 15.5)).label("Data Receive", fontsize=10)

        d += elm.Line().at(data).right().length(1)
        d += elm.Resistor().right().label("R4", loc="top", ofst=0.05, fontsize=8).label("47k", loc="bottom", ofst=0.05, fontsize=8)
        rx_div = d.here
        d += elm.Dot()

        # Zener
        d += elm.Line().right().length(0.5)
        d += elm.Zener().down().reverse().label("D1", loc="right", ofst=0.15, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # Divider bottom
        d += elm.Line().at(rx_div).down().length(0.5)
        d += elm.Resistor().down().label("R5", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        d += elm.Line().left().tox(ac_com[0])

        # RX LED
        d += elm.Line().at(rx_div).right().length(2)
        d += elm.Resistor().right().label("R6", loc="top", ofst=0.05, fontsize=8).label("1k", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().right().length(0.3)
        d += elm.Diode().down().label("U2", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # RX output
        d += elm.Dot().at((zc_out_x, data_y + 5)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Resistor().down().label("R7", loc="right", ofst=0.15, fontsize=8).label("10k", loc="left", ofst=0.15, fontsize=8)
        rx_out = d.here
        d += elm.Dot()
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        d += elm.Ground()

        # ===== DATA TX SECTION =====
        d += elm.Label().at((3, 7.5)).label("Data Transmit", fontsize=10)

        usb_x = 18

        # TX from CH340
        d += elm.Dot().at((usb_x, 4)).label("CH340_TX", loc="right", ofst=0.15, fontsize=9)
        d += elm.Line().left().length(1)
        d += elm.Resistor().left().label("R8", loc="top", ofst=0.05, fontsize=8).label("330", loc="bottom", ofst=0.05, fontsize=8)
        d += elm.Line().left().length(0.5)
        d += elm.Diode().down().reverse().label("U3", loc="right", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # TX transistor output
        tx_opto_out_x = 12
        d += elm.Dot().at((tx_opto_out_x, 4)).label("VCC", loc="top", ofst=0.1, fontsize=9)
        d += elm.Line().down().length(1)
        d += elm.BjtNpn(circle=True).anchor("collector").scale(0.8)
        tx_gate = d.here

        d += elm.Resistor().down().label("R9", loc="right", ofst=0.2, fontsize=8).label("10k", loc="left", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # MOSFET
        d += elm.Line().at(tx_gate).left().length(2.5)
        fet = elm.AnalogNFet(bulk=True).anchor("gate").reverse().scale(0.8).label("Q1", loc="left", ofst=0.4, fontsize=8)
        d += fet

        # MOSFET drain to data
        d.push()
        d += elm.Line().at(fet.drain).up().length(1.5)
        drain_node = d.here
        d += elm.Resistor().up().label("R10", loc="left", ofst=0.2, fontsize=8).label("22Ω", loc="right", ofst=0.2, fontsize=8)
        d += elm.Line().up().toy(data_y)
        d += elm.Line().left().tox(data[0] + 1.5)

        # Flyback diode
        d += elm.Line().at(drain_node).right().length(2.5)
        d += elm.Diode().down().label("D2", loc="right", ofst=0.25, fontsize=8)
        d += elm.Line().down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # MOSFET source to AC_COM
        d += elm.Line().at(fet.source).down().toy(ac_com_y)
        d += elm.Line().left().tox(ac_com[0])

        # ===== USB SECTION (right side) =====
        d += elm.Label().at((usb_x, 21)).label("USB (J2)", fontsize=11, halign="left")

        # USB connector pins
        d += elm.Dot().at((usb_x + 4, 19)).label("VBUS (5V)", loc="right", ofst=0.15, fontsize=9)
        usb_vbus = d.here
        d += elm.Dot().at((usb_x + 4, 17)).label("D-", loc="right", ofst=0.15, fontsize=9)
        usb_dm = d.here
        d += elm.Dot().at((usb_x + 4, 15)).label("D+", loc="right", ofst=0.15, fontsize=9)
        usb_dp = d.here
        d += elm.Dot().at((usb_x + 4, 13)).label("GND", loc="right", ofst=0.15, fontsize=9)
        usb_gnd = d.here

        # CH340G chip label
        d += elm.Label().at((usb_x - 2, 18)).label("U4: CH340G", fontsize=10)

        # VCC from USB with fuse
        d += elm.Line().at(usb_vbus).left().length(1)
        d += elm.Resistor().left().label("F1", loc="top", ofst=0.05, fontsize=8).label("500mA", loc="bottom", ofst=0.05, fontsize=8)
        vcc_node = d.here
        d += elm.Dot()

        # Bulk capacitor
        d += elm.Line().down().length(1)
        d += elm.Capacitor().down().label("C1", loc="right", ofst=0.2, fontsize=8).label("10µF", loc="left", ofst=0.2, fontsize=8)
        d += elm.Ground()

        # VCC distribution
        d += elm.Line().at(vcc_node).left().length(2)
        d += elm.Dot().label("VCC", loc="top", ofst=0.1, fontsize=9)

        # Decoupling cap
        d += elm.Line().down().length(0.5)
        d += elm.Capacitor().down().label("C2", loc="right", ofst=0.15, fontsize=8).label("100nF", loc="left", ofst=0.15, fontsize=8)
        d += elm.Ground()

        # Connect optocoupler outputs to CH340
        d += elm.Line().at(zc_out).right().length(2)
        d += elm.Dot().label("DTR/RTS", loc="top", ofst=0.1, fontsize=8)

        d += elm.Line().at(rx_out).right().length(5)
        d += elm.Dot().label("CH340_RX", loc="right", ofst=0.15, fontsize=9)

        # Isolation barrier
        barrier_x = 13
        d += elm.Line().at((barrier_x, 22)).down().length(24).linestyle("--").color("red").linewidth(1.5)
        d += elm.Label().at((barrier_x, -2.5)).label("ISOLATION BARRIER", fontsize=9, color="red")

        return d


def main():
    parser = argparse.ArgumentParser(
        description="Generate EnviraCOM interface circuit schematics"
    )
    parser.add_argument(
        "--section",
        choices=["zc", "rx", "tx", "usb", "full", "full-usb", "all"],
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
        "usb": ("enviracom_usb_interface", draw_usb_interface),
        "full": ("enviracom_full_schematic", draw_full_schematic),
        "full-usb": ("enviracom_full_schematic_usb", draw_full_schematic_usb),
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
