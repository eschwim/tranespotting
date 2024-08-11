#!/usr/bin/env python3
"""
ComfortLink II Capture Analysis Tool

Analyzes captured bus traffic to help identify protocol patterns.
"""

import struct
from collections import Counter, defaultdict
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .packet import Packet

console = Console()


class CaptureAnalyzer:
    """Analyzes captured ComfortLink II traffic."""

    def __init__(self):
        self.packets: list[Packet] = []
        self.addresses: Counter = Counter()
        self.message_types: Counter = Counter()
        self.conversations: defaultdict = defaultdict(list)

    def load_capture(self, filepath: Path):
        """Load packets from a capture file."""
        console.print(f"[blue]Loading:[/blue] {filepath}")

        with open(filepath, "rb") as f:
            while True:
                # Read timestamp (8 bytes) and length (4 bytes)
                header = f.read(12)
                if len(header) < 12:
                    break

                timestamp, length = struct.unpack("<dI", header)

                # Read packet data
                data = f.read(length)
                if len(data) < length:
                    break

                packet = Packet.from_bytes(data, timestamp)
                self.packets.append(packet)

        console.print(f"[green]Loaded {len(self.packets)} packets[/green]")

    def analyze(self):
        """Run analysis on loaded packets."""
        self.addresses.clear()
        self.message_types.clear()
        self.conversations.clear()

        for packet in self.packets:
            if packet.parse_error:
                continue

            # Count addresses
            self.addresses[packet.src_addr] += 1
            self.addresses[packet.dest_addr] += 1

            # Count message types
            self.message_types[packet.msg_type] += 1

            # Group by conversation (src -> dest)
            conv_key = (packet.src_addr, packet.dest_addr)
            self.conversations[conv_key].append(packet)

    def print_summary(self):
        """Print analysis summary."""
        console.print("\n[bold]Analysis Summary[/bold]\n")

        # Address table
        addr_table = Table(title="Device Addresses")
        addr_table.add_column("Address", style="cyan")
        addr_table.add_column("Hex", style="yellow")
        addr_table.add_column("Packets", style="green")
        addr_table.add_column("Notes", style="dim")

        for addr, count in self.addresses.most_common():
            notes = self._guess_device_type(addr)
            addr_table.add_row(str(addr), f"0x{addr:04X}", str(count), notes)

        console.print(addr_table)

        # Message type table
        type_table = Table(title="\nMessage Types")
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Hex", style="yellow")
        type_table.add_column("Count", style="green")

        for msg_type, count in self.message_types.most_common():
            type_table.add_row(str(msg_type), f"0x{msg_type:02X}", str(count))

        console.print(type_table)

        # Conversation summary
        conv_table = Table(title="\nConversations")
        conv_table.add_column("Source", style="cyan")
        conv_table.add_column("Destination", style="yellow")
        conv_table.add_column("Packets", style="green")

        for (src, dst), packets in sorted(
            self.conversations.items(), key=lambda x: -len(x[1])
        )[:20]:
            conv_table.add_row(f"0x{src:04X}", f"0x{dst:04X}", str(len(packets)))

        console.print(conv_table)

    def _guess_device_type(self, addr: int) -> str:
        """Guess device type based on address patterns.

        Based on Carrier Infinity patterns (may differ for Trane):
        - 0x2001: Thermostat
        - 0x4001: Air Handler
        - 0x5001: Heat Pump / AC
        - 0x1F1F: Broadcast
        """
        guesses = {
            0x1F1F: "Broadcast?",
            0x2001: "Thermostat?",
            0x4001: "Air Handler?",
            0x5001: "Outdoor Unit?",
        }
        return guesses.get(addr, "")

    def find_patterns(self, min_occurrences: int = 3):
        """Find repeating byte patterns in payloads."""
        console.print("\n[bold]Repeating Patterns[/bold]\n")

        # Look for common payload prefixes
        prefixes: Counter = Counter()
        for packet in self.packets:
            if packet.payload and len(packet.payload) >= 4:
                prefix = packet.payload[:4]
                prefixes[prefix] += 1

        pattern_table = Table(title="Common Payload Prefixes (4 bytes)")
        pattern_table.add_column("Pattern", style="cyan")
        pattern_table.add_column("Count", style="green")

        for pattern, count in prefixes.most_common(20):
            if count >= min_occurrences:
                pattern_table.add_row(pattern.hex(" "), str(count))

        console.print(pattern_table)

    def export_packets(self, filepath: Path, format: str = "hex"):
        """Export packets to a readable file."""
        with open(filepath, "w") as f:
            for i, packet in enumerate(self.packets):
                if format == "hex":
                    f.write(f"{i:5d} [{packet.timestamp:10.3f}] {packet.to_hex()}\n")
                else:
                    f.write(f"{i:5d} [{packet.timestamp:10.3f}] {packet}\n\n")

        console.print(f"[green]Exported to:[/green] {filepath}")

    def show_packet(self, index: int):
        """Show detailed view of a single packet."""
        if 0 <= index < len(self.packets):
            packet = self.packets[index]
            console.print(f"\n[bold]Packet {index}[/bold]")
            console.print(f"Timestamp: {packet.timestamp:.3f}")
            console.print(f"Raw ({len(packet.raw)} bytes): {packet.to_hex()}")
            console.print(f"\n{packet}")
        else:
            console.print(f"[red]Invalid packet index: {index}[/red]")

    def filter_by_address(self, addr: int) -> list[Packet]:
        """Filter packets involving a specific address."""
        return [
            p
            for p in self.packets
            if not p.parse_error and (p.src_addr == addr or p.dest_addr == addr)
        ]


@click.command()
@click.argument("capture_file", type=click.Path(exists=True))
@click.option(
    "--export",
    "-e",
    type=click.Path(),
    help="Export packets to file",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["hex", "parsed"]),
    default="parsed",
    help="Export format",
)
@click.option(
    "--packet",
    "-p",
    type=int,
    help="Show specific packet by index",
)
@click.option(
    "--address",
    "-a",
    type=str,
    help="Filter by address (hex, e.g., 0x2001)",
)
def main(capture_file: str, export: str, format: str, packet: int, address: str):
    """Analyze ComfortLink II capture files.

    Example:
        cl2-analyze captures/raw/capture_20240101_120000.bin
        cl2-analyze capture.bin --export packets.txt --format parsed
        cl2-analyze capture.bin --packet 42
    """
    console.print("[bold blue]ComfortLink II Capture Analyzer[/bold blue]\n")

    analyzer = CaptureAnalyzer()
    analyzer.load_capture(Path(capture_file))
    analyzer.analyze()

    if packet is not None:
        analyzer.show_packet(packet)
    elif address:
        addr_int = int(address, 16) if address.startswith("0x") else int(address)
        filtered = analyzer.filter_by_address(addr_int)
        console.print(f"\n[bold]Packets involving 0x{addr_int:04X}:[/bold]")
        for i, p in enumerate(filtered[:50]):
            console.print(f"{i}: {p.format_header()}")
        if len(filtered) > 50:
            console.print(f"... and {len(filtered) - 50} more")
    else:
        analyzer.print_summary()
        analyzer.find_patterns()

    if export:
        analyzer.export_packets(Path(export), format)


if __name__ == "__main__":
    main()
