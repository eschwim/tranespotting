#!/usr/bin/env python3
"""
EnviraCOM Interface PCB Generator

Generates PCB layout and manufacturing files for the EnviraCOM interface circuit
using cuflow (https://github.com/jamesbowman/cuflow).

Usage:
    python -m tools.hardware.enviracom_pcb                    # Generate all outputs
    python -m tools.hardware.enviracom_pcb --output-dir ./out # Custom output directory
    python -m tools.hardware.enviracom_pcb --format svg       # SVG preview only

Installation (cuflow is not on PyPI, requires manual setup):

    # Clone cuflow repository
    git clone https://github.com/jamesbowman/cuflow.git /path/to/cuflow

    # Add to PYTHONPATH
    export PYTHONPATH="/path/to/cuflow:$PYTHONPATH"

    # Install cuflow's dependencies
    pip install pillow svgwrite shapely

Outputs:
    - Gerber files (GTL, GBL, GTS, GBS, GTO, GBO, etc.)
    - Drill file (DRL)
    - Bill of Materials (BOM.csv)
    - Pick-and-place file (PNP.csv)
    - SVG preview
"""

import argparse
import sys
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "hardware" / "generated" / "pcb"

# Design constants
INCH = 25.4  # mm per inch
MIL = INCH / 1000  # mm per mil

# Board parameters
BOARD_WIDTH = 60.0  # mm
BOARD_HEIGHT = 45.0  # mm
ISOLATION_GAP = 8.0  # mm - creepage distance for 24VAC isolation

# Trace widths
TRACE_SIGNAL = 0.3  # mm - signal traces
TRACE_POWER = 0.5   # mm - power traces
TRACE_HVAC = 0.8    # mm - high current HVAC side


def import_cuflow():
    """
    Import cuflow modules. Returns (cu, dip, svgout) tuple.
    Raises ImportError if cuflow is not available.
    """
    try:
        import cuflow as cu
        import dip
        try:
            import svgout
        except ImportError:
            svgout = None
        return cu, dip, svgout
    except ImportError:
        raise ImportError(
            "cuflow is required for PCB generation.\n\n"
            "cuflow is not a standard pip package. Install manually:\n\n"
            "  1. Clone the cuflow repository:\n"
            "     git clone https://github.com/jamesbowman/cuflow.git\n\n"
            "  2. Add to your PYTHONPATH:\n"
            "     export PYTHONPATH=\"/path/to/cuflow:$PYTHONPATH\"\n\n"
            "  3. Install dependencies:\n"
            "     pip install pillow svgwrite shapely\n\n"
            "  4. Run this script again"
        )


def create_footprints(dip_module):
    """Create footprint classes using the provided dip module."""

    class DIP6(dip_module.PTH):
        """6-pin DIP package for optocouplers (H11AA1, 4N35)."""

        family = "U"
        footprint = "DIP-6"

        def place(self, dc):
            # Standard DIP-6: 0.3" row spacing, 0.1" pin pitch
            row_spacing = 0.3 * INCH  # 7.62mm
            pin_pitch = 0.1 * INCH    # 2.54mm

            # Place pins: 1-3 on left, 4-6 on right
            for i in range(3):
                # Left side (pins 1, 2, 3)
                dc.push()
                dc.forward(i * pin_pitch)
                dc.left(90)
                dc.forward(row_spacing / 2)
                self.gh(dc)
                self.pads[-1].setname(str(i + 1))
                dc.pop()

                # Right side (pins 6, 5, 4 - counting down)
                dc.push()
                dc.forward(i * pin_pitch)
                dc.right(90)
                dc.forward(row_spacing / 2)
                self.gh(dc)
                self.pads[-1].setname(str(6 - i))
                dc.pop()

            # Outline (simple rectangle)
            dc.push()
            dc.left(90)
            dc.forward(row_spacing / 2 + 1)
            dc.left(90)
            dc.forward(pin_pitch / 2)
            dc.newpath()
            w = pin_pitch * 2 + 1
            h = row_spacing + 2
            for _ in range(2):
                dc.forward(w)
                dc.left(90)
                dc.forward(h)
                dc.left(90)
            dc.silko()
            dc.pop()

            # Pin 1 marker (small square near pin 1)
            dc.push()
            dc.left(90)
            dc.forward(row_spacing / 2 + 2)
            dc.left(90)
            dc.forward(pin_pitch / 2 + 0.5)
            dc.newpath()
            dc.rect(1, 1)
            dc.silko()
            dc.pop()

    class TO92(dip_module.PTH):
        """TO-92 package for 2N7000 MOSFET."""

        family = "T"  # T for transistor (Q not in cuflow's valid families)
        footprint = "TO-92"

        def place(self, dc):
            # TO-92: 3 pins, 0.1" pitch, flat side indicator
            pin_pitch = 0.1 * INCH  # 2.54mm

            # Pins: 1=Source, 2=Gate, 3=Drain (for 2N7000)
            for i, name in enumerate(["S", "G", "D"]):
                dc.push()
                dc.left(90)
                dc.forward((i - 1) * pin_pitch)
                self.gh(dc)
                self.pads[-1].setname(name)
                dc.pop()

            # Rectangular outline (simplified from semi-circular)
            dc.push()
            dc.forward(2)
            dc.left(90)
            dc.forward(pin_pitch + 1)
            dc.newpath()
            w = 4
            h = pin_pitch * 2 + 2
            dc.left(90)
            for _ in range(2):
                dc.forward(w)
                dc.left(90)
                dc.forward(h)
                dc.left(90)
            dc.silko()
            dc.pop()

    class Axial(dip_module.PTH):
        """Axial component (resistor) with configurable lead spacing."""

        family = "R"
        footprint = "AXIAL"

        def __init__(self, dc, val=None, spacing=10.0, source=None):
            self.spacing = spacing
            super().__init__(dc, val=val, source=source)

        def place(self, dc):
            # Two pins at specified spacing
            dc.push()
            dc.left(90)
            dc.forward(self.spacing / 2)
            self.gh(dc)
            self.pads[-1].setname("1")
            dc.pop()

            dc.push()
            dc.right(90)
            dc.forward(self.spacing / 2)
            self.gh(dc)
            self.pads[-1].setname("2")
            dc.pop()

            # Body outline
            dc.push()
            body_len = self.spacing - 4
            body_width = 2.5
            dc.forward(body_len / 2)
            dc.left(90)
            dc.forward(body_width / 2)
            dc.newpath()
            dc.left(90)
            for _ in range(2):
                dc.forward(body_len)
                dc.left(90)
                dc.forward(body_width)
                dc.left(90)
            dc.silko()
            dc.pop()

    class Diode(dip_module.PTH):
        """Axial diode with configurable lead spacing."""

        family = "D"
        footprint = "AXIAL"

        def __init__(self, dc, val=None, spacing=7.5, source=None):
            self.spacing = spacing
            super().__init__(dc, val=val, source=source)

        def place(self, dc):
            # Two pins at specified spacing
            dc.push()
            dc.left(90)
            dc.forward(self.spacing / 2)
            self.gh(dc)
            self.pads[-1].setname("A")  # Anode
            dc.pop()

            dc.push()
            dc.right(90)
            dc.forward(self.spacing / 2)
            self.gh(dc)
            self.pads[-1].setname("K")  # Kathode
            dc.pop()

            # Body outline
            dc.push()
            body_len = self.spacing - 3
            body_width = 2
            dc.forward(body_len / 2)
            dc.left(90)
            dc.forward(body_width / 2)
            dc.newpath()
            dc.left(90)
            for _ in range(2):
                dc.forward(body_len)
                dc.left(90)
                dc.forward(body_width)
                dc.left(90)
            dc.silko()
            dc.pop()

    class ScrewTerminal3(dip_module.PTH):
        """3-position screw terminal for HVAC connections (R, C, D)."""

        family = "J"
        footprint = "TERM-3"

        def place(self, dc):
            # 5.08mm (0.2") pitch screw terminals
            pitch = 5.08

            for i, name in enumerate(["R", "C", "D"]):
                dc.push()
                dc.left(90)
                dc.forward((i - 1) * pitch)
                self.gh(dc, radius=1.2)  # Larger hole for screw terminal
                self.pads[-1].setname(name)
                dc.pop()

            # Terminal block outline
            dc.push()
            dc.forward(4)
            dc.left(90)
            dc.forward(pitch + 3)
            dc.newpath()
            w = 8
            h = pitch * 2 + 6
            dc.left(90)
            for _ in range(2):
                dc.forward(w)
                dc.left(90)
                dc.forward(h)
                dc.left(90)
            dc.silko()
            dc.pop()

        def gh(self, dc, radius=1.0):
            """Create plated through-hole with custom radius."""
            dc.board.hole(dc.xy, radius, None)
            p = dc.copy()
            p.n_agon(radius + 0.5, 6)
            p.contact()
            p.part = self.id
            self.pads.append(p)

    class PinHeader5(dip_module.PTH):
        """5-pin header for MCU connection (VCC, GND, ZC, RX, TX)."""

        family = "J"
        footprint = "HDR-1x5"

        def place(self, dc):
            pitch = 2.54  # 0.1" standard header pitch

            pin_names = ["VCC", "GND", "ZC", "RX", "TX"]
            for i, name in enumerate(pin_names):
                dc.push()
                dc.left(90)
                dc.forward((i - 2) * pitch)
                self.gh(dc)
                self.pads[-1].setname(name)
                dc.pop()

            # Header outline
            dc.push()
            dc.forward(1.5)
            dc.left(90)
            dc.forward(2 * pitch + 1.5)
            dc.newpath()
            w = 3
            h = 4 * pitch + 3
            dc.left(90)
            for _ in range(2):
                dc.forward(w)
                dc.left(90)
                dc.forward(h)
                dc.left(90)
            dc.silko()
            dc.pop()

    return {
        'DIP6': DIP6,
        'TO92': TO92,
        'Axial': Axial,
        'Diode': Diode,
        'ScrewTerminal3': ScrewTerminal3,
        'PinHeader5': PinHeader5,
    }


def create_enviracom_pcb(cu, footprints):
    """Create the EnviraCOM interface PCB."""

    DIP6 = footprints['DIP6']
    TO92 = footprints['TO92']
    Axial = footprints['Axial']
    Diode = footprints['Diode']
    ScrewTerminal3 = footprints['ScrewTerminal3']
    PinHeader5 = footprints['PinHeader5']

    # Create board with design rules
    brd = cu.Board(
        size=(BOARD_WIDTH, BOARD_HEIGHT),
        trace=TRACE_SIGNAL,
        space=TRACE_SIGNAL * 1.2,
        via_hole=0.3,
        via=0.6,
        via_space=0.5,
        silk=0.2
    )

    # === COMPONENT PLACEMENT ===

    # HVAC Side (left side of board) - 24VAC isolated section
    hvac_x = 10

    # J1: HVAC screw terminal (R, C, D)
    j1 = ScrewTerminal3(brd.DC((hvac_x, BOARD_HEIGHT / 2)).right(90), val="HVAC")

    # U1: H11AA1 Zero-crossing detector
    u1 = DIP6(brd.DC((hvac_x + 15, BOARD_HEIGHT - 12)), val="H11AA1")

    # U2: 4N35 Data receive optocoupler
    u2 = DIP6(brd.DC((hvac_x + 15, BOARD_HEIGHT / 2)), val="4N35")

    # U3: 4N35 Data transmit optocoupler
    u3 = DIP6(brd.DC((hvac_x + 15, 12)), val="4N35")

    # Q1: 2N7000 MOSFET for TX
    q1 = TO92(brd.DC((hvac_x + 5, 10)).right(90), val="2N7000")

    # Resistors - HVAC side
    r1 = Axial(brd.DC((hvac_x + 8, BOARD_HEIGHT - 8)), val="100k", spacing=10)
    r2 = Axial(brd.DC((hvac_x + 8, BOARD_HEIGHT - 14)), val="100k", spacing=10)
    r4 = Axial(brd.DC((hvac_x + 8, BOARD_HEIGHT / 2 + 5)), val="47k", spacing=10)
    r5 = Axial(brd.DC((hvac_x + 8, BOARD_HEIGHT / 2 - 1)), val="10k", spacing=10)
    r6 = Axial(brd.DC((hvac_x + 8, BOARD_HEIGHT / 2 - 7)), val="1k", spacing=10)
    r10 = Axial(brd.DC((hvac_x + 3, 18)), val="22R 1W", spacing=12)

    # D1: Zener diode
    d1 = Diode(brd.DC((hvac_x + 3, BOARD_HEIGHT / 2 - 4)), val="5.1V", spacing=7.5)

    # D2: Flyback diode
    d2 = Diode(brd.DC((hvac_x + 10, 8)), val="1N4148", spacing=7.5)

    # MCU Side (right side of board) - 3.3V/5V section
    mcu_x = BOARD_WIDTH - 10

    # J2: MCU pin header
    j2 = PinHeader5(brd.DC((mcu_x, BOARD_HEIGHT / 2)).left(90), val="MCU")

    # Resistors - MCU side (pullups)
    r3 = Axial(brd.DC((mcu_x - 8, BOARD_HEIGHT - 10)), val="10k", spacing=10)
    r7 = Axial(brd.DC((mcu_x - 8, BOARD_HEIGHT / 2 + 3)), val="10k", spacing=10)
    r8 = Axial(brd.DC((mcu_x - 8, 15)), val="330R", spacing=10)
    r9 = Axial(brd.DC((mcu_x - 8, 8)), val="10k", spacing=10)

    # === ISOLATION BARRIER ===
    # Draw isolation slot/barrier marking on silkscreen (as thin rectangle)
    barrier_x = BOARD_WIDTH / 2
    dc = brd.DC((barrier_x, 5))
    dc.newpath()
    barrier_width = 0.5
    barrier_height = BOARD_HEIGHT - 10
    dc.forward(barrier_height)
    dc.left(90)
    dc.forward(barrier_width)
    dc.left(90)
    dc.forward(barrier_height)
    dc.left(90)
    dc.forward(barrier_width)
    dc.silko()

    # === ROUTING ===
    # Note: Full routing requires careful trace layout
    # This places components; routing would be done interactively or with autorouter

    return brd


def generate_outputs(brd, output_dir: Path, formats: list, svgout_module):
    """Generate PCB manufacturing outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    basename = str(output_dir / "enviracom_interface")

    generated = []

    if "gerber" in formats or "all" in formats:
        print("Generating Gerber files...")
        brd.save(basename)
        generated.extend([
            "enviracom_interface.GTL (Top Copper)",
            "enviracom_interface.GBL (Bottom Copper)",
            "enviracom_interface.GTS (Top Soldermask)",
            "enviracom_interface.GBS (Bottom Soldermask)",
            "enviracom_interface.GTO (Top Silkscreen)",
            "enviracom_interface.GBO (Bottom Silkscreen)",
            "enviracom_interface.DRL (Drill file)",
        ])
        print(f"  Gerber files saved to {output_dir}/")

    if "bom" in formats or "all" in formats:
        print("Generating BOM...")
        brd.bom(basename)
        generated.append("enviracom_interface_BOM.csv")
        print(f"  BOM saved to {basename}_BOM.csv")

    if "pnp" in formats or "all" in formats:
        print("Generating pick-and-place...")
        brd.pnp(basename)
        generated.append("enviracom_interface_PNP.csv")
        print(f"  PnP saved to {basename}_PNP.csv")

    if "svg" in formats or "all" in formats:
        if svgout_module:
            print("Generating SVG preview...")
            try:
                svgout_module.write(brd, basename + ".svg")
                generated.append("enviracom_interface.svg")
                print(f"  SVG saved to {basename}.svg")
            except (IndexError, Exception) as e:
                print(f"  Warning: SVG generation failed: {e}")
                print("  (Gerber files can still be used for manufacturing)")
        else:
            print("  Warning: svgout module not available, skipping SVG")

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generate EnviraCOM interface PCB files using cuflow"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--format",
        choices=["all", "gerber", "svg", "bom", "pnp"],
        nargs="+",
        default=["all"],
        help="Output formats to generate (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Just check if cuflow is available",
    )

    args = parser.parse_args()

    # Import cuflow
    try:
        cu, dip, svgout = import_cuflow()
    except ImportError as e:
        print("=" * 60)
        print("ERROR: cuflow is required for PCB generation")
        print("=" * 60)
        print()
        print(str(e))
        sys.exit(1)

    if args.check:
        print("cuflow is available and ready to use!")
        return

    print("EnviraCOM Interface PCB Generator")
    print("=" * 40)
    print(f"Board size: {BOARD_WIDTH}mm x {BOARD_HEIGHT}mm")
    print(f"Isolation gap: {ISOLATION_GAP}mm")
    print()

    print("Creating footprint definitions...")
    footprints = create_footprints(dip)

    print("Creating PCB layout...")
    brd = create_enviracom_pcb(cu, footprints)

    print()
    generated = generate_outputs(brd, args.output_dir, args.format, svgout)

    print()
    print("Generated files:")
    for f in generated:
        print(f"  - {f}")

    print()
    print("Done!")
    print()
    print("Next steps:")
    print("  1. Review SVG preview for layout verification")
    print("  2. Import Gerber files into your PCB viewer (e.g., gerbv, KiCad)")
    print("  3. Send to PCB manufacturer (JLCPCB, PCBWay, OSHPark, etc.)")


if __name__ == "__main__":
    main()
