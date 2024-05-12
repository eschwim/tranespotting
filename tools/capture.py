#!/usr/bin/env python3
"""
ComfortLink II Bus Capture Tool

Captures raw RS-485 traffic from the ComfortLink II bus for analysis.
"""

import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import click
import serial
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()


class BusCapture:
    """Captures and logs RS-485 bus traffic."""

    def __init__(
        self,
        port: str,
        baud_rate: int,
        output_dir: Path,
        data_bits: int = 8,
        parity: str = "N",
        stop_bits: int = 1,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.serial_config = {
            "port": port,
            "baudrate": baud_rate,
            "bytesize": data_bits,
            "parity": parity[0].upper() if parity else "N",
            "stopbits": stop_bits,
            "timeout": 0.1,
        }

        self.running = False
        self.packets_captured = 0
        self.bytes_captured = 0
        self.start_time = None
        self.capture_file = None
        self.serial_conn = None

    def _generate_filename(self) -> Path:
        """Generate a timestamped capture filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"capture_{timestamp}.bin"

    def _open_capture_file(self):
        """Open a new capture file."""
        filepath = self._generate_filename()
        self.capture_file = open(filepath, "wb")
        console.print(f"[green]Writing to:[/green] {filepath}")
        return filepath

    def _write_packet(self, timestamp: float, data: bytes):
        """Write a packet to the capture file with timestamp."""
        if self.capture_file:
            # Format: [8-byte timestamp][4-byte length][data]
            import struct

            ts_bytes = struct.pack("<d", timestamp)
            len_bytes = struct.pack("<I", len(data))
            self.capture_file.write(ts_bytes + len_bytes + data)
            self.capture_file.flush()

    def start(self):
        """Start capturing bus traffic."""
        self.running = True
        self.start_time = time.time()
        self.packets_captured = 0
        self.bytes_captured = 0

        try:
            self.serial_conn = serial.Serial(**self.serial_config)
            console.print(f"[green]Connected to {self.port} at {self.baud_rate} baud[/green]")
        except serial.SerialException as e:
            console.print(f"[red]Failed to open serial port:[/red] {e}")
            sys.exit(1)

        self._open_capture_file()

        # Buffer for accumulating data
        buffer = bytearray()
        last_data_time = time.time()
        packet_timeout = 0.05  # 50ms gap indicates packet boundary

        console.print("[yellow]Capturing... Press Ctrl+C to stop[/yellow]\n")

        try:
            with Live(self._make_status_table(), refresh_per_second=4) as live:
                while self.running:
                    # Read available data
                    if self.serial_conn.in_waiting:
                        data = self.serial_conn.read(self.serial_conn.in_waiting)
                        buffer.extend(data)
                        last_data_time = time.time()

                    # Check for packet boundary (gap in data)
                    elif buffer and (time.time() - last_data_time) > packet_timeout:
                        # We have a complete packet
                        packet_data = bytes(buffer)
                        timestamp = time.time()

                        self._write_packet(timestamp, packet_data)
                        self._print_packet(timestamp, packet_data)

                        self.packets_captured += 1
                        self.bytes_captured += len(packet_data)

                        buffer.clear()

                    live.update(self._make_status_table())
                    time.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop capturing and clean up."""
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
        if self.capture_file:
            self.capture_file.close()

        duration = time.time() - self.start_time if self.start_time else 0
        console.print(f"\n[green]Capture complete![/green]")
        console.print(f"  Packets: {self.packets_captured}")
        console.print(f"  Bytes: {self.bytes_captured}")
        console.print(f"  Duration: {duration:.1f}s")

    def _make_status_table(self) -> Table:
        """Create a status table for live display."""
        table = Table(title="ComfortLink II Capture")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        duration = time.time() - self.start_time if self.start_time else 0
        table.add_row("Port", self.port)
        table.add_row("Baud Rate", str(self.baud_rate))
        table.add_row("Packets", str(self.packets_captured))
        table.add_row("Bytes", str(self.bytes_captured))
        table.add_row("Duration", f"{duration:.1f}s")

        return table

    def _print_packet(self, timestamp: float, data: bytes):
        """Print a packet in hex format."""
        rel_time = timestamp - self.start_time
        hex_str = data.hex(" ")

        # Truncate long packets for display
        if len(hex_str) > 80:
            hex_str = hex_str[:77] + "..."

        console.print(f"[dim]{rel_time:8.3f}s[/dim] [{len(data):3d}] {hex_str}")


@click.command()
@click.option(
    "-p",
    "--port",
    default="/dev/ttyUSB0",
    help="Serial port for RS-485 adapter",
    show_default=True,
)
@click.option(
    "-b",
    "--baud",
    default=19200,
    type=int,
    help="Baud rate",
    show_default=True,
)
@click.option(
    "-o",
    "--output",
    default="./captures/raw",
    type=click.Path(),
    help="Output directory for captures",
    show_default=True,
)
@click.option(
    "--data-bits",
    default=8,
    type=click.Choice(["5", "6", "7", "8"]),
    help="Data bits",
    show_default=True,
)
@click.option(
    "--parity",
    default="none",
    type=click.Choice(["none", "even", "odd"]),
    help="Parity",
    show_default=True,
)
@click.option(
    "--stop-bits",
    default=1,
    type=click.Choice(["1", "2"]),
    help="Stop bits",
    show_default=True,
)
def main(port: str, baud: int, output: str, data_bits: str, parity: str, stop_bits: str):
    """Capture ComfortLink II bus traffic.

    Connect your RS-485 adapter to the communication bus (A/B lines) on your
    HVAC system and run this tool to capture traffic for analysis.

    Example:
        cl2-capture -p /dev/ttyUSB0 -b 19200
    """
    console.print("[bold blue]ComfortLink II Bus Capture Tool[/bold blue]\n")

    capture = BusCapture(
        port=port,
        baud_rate=baud,
        output_dir=Path(output),
        data_bits=int(data_bits),
        parity=parity,
        stop_bits=int(stop_bits),
    )

    # Handle signals for clean shutdown
    def signal_handler(sig, frame):
        capture.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    capture.start()


if __name__ == "__main__":
    main()
