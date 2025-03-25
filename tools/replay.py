#!/usr/bin/env python3
"""
ComfortLink II Packet Replay Tool

Replays captured packets for testing and protocol exploration.
USE WITH CAUTION - only replay packets you understand.
"""

import struct
import time
from pathlib import Path

import click
import serial
from rich.console import Console
from rich.prompt import Confirm

console = Console()


class PacketReplayer:
    """Replays captured packets to the RS-485 bus."""

    def __init__(self, port: str, baud_rate: int):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_conn = None
        self.packets: list[tuple[float, bytes]] = []

    def load_capture(self, filepath: Path):
        """Load packets from a capture file."""
        self.packets.clear()

        with open(filepath, "rb") as f:
            while True:
                header = f.read(12)
                if len(header) < 12:
                    break

                timestamp, length = struct.unpack("<dI", header)
                data = f.read(length)
                if len(data) < length:
                    break

                self.packets.append((timestamp, data))

        console.print(f"[green]Loaded {len(self.packets)} packets[/green]")

    def connect(self):
        """Connect to the serial port."""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=1.0,
            )
            console.print(f"[green]Connected to {self.port}[/green]")
        except serial.SerialException as e:
            console.print(f"[red]Failed to connect:[/red] {e}")
            raise

    def disconnect(self):
        """Disconnect from serial port."""
        if self.serial_conn:
            self.serial_conn.close()

    def replay_single(self, index: int):
        """Replay a single packet."""
        if not 0 <= index < len(self.packets):
            console.print(f"[red]Invalid packet index: {index}[/red]")
            return

        _, data = self.packets[index]
        console.print(f"[yellow]Sending packet {index}:[/yellow] {data.hex(' ')}")

        if self.serial_conn:
            self.serial_conn.write(data)
            console.print("[green]Sent[/green]")

    def replay_sequence(self, start: int, end: int, preserve_timing: bool = True):
        """Replay a sequence of packets."""
        if start < 0 or end > len(self.packets):
            console.print("[red]Invalid range[/red]")
            return

        console.print(f"[yellow]Replaying packets {start} to {end - 1}[/yellow]")

        first_timestamp = self.packets[start][0]
        for i in range(start, end):
            timestamp, data = self.packets[i]

            if preserve_timing and i > start:
                # Wait for appropriate inter-packet delay
                prev_timestamp = self.packets[i - 1][0]
                delay = timestamp - prev_timestamp
                if delay > 0:
                    time.sleep(delay)

            console.print(f"[dim]{i}:[/dim] {data.hex(' ')[:60]}...")

            if self.serial_conn:
                self.serial_conn.write(data)

        console.print("[green]Sequence complete[/green]")


@click.command()
@click.argument("capture_file", type=click.Path(exists=True))
@click.option("-p", "--port", default="/dev/ttyUSB0", help="Serial port")
@click.option("-b", "--baud", default=19200, type=int, help="Baud rate")
@click.option("--packet", "-n", type=int, help="Replay single packet by index")
@click.option("--start", type=int, default=0, help="Start index for sequence replay")
@click.option("--end", type=int, help="End index for sequence replay")
@click.option("--no-timing", is_flag=True, help="Ignore original packet timing")
@click.option("--dry-run", is_flag=True, help="Show packets without sending")
def main(
    capture_file: str,
    port: str,
    baud: int,
    packet: int,
    start: int,
    end: int,
    no_timing: bool,
    dry_run: bool,
):
    """Replay captured packets to the ComfortLink II bus.

    WARNING: Only replay packets you understand. Sending incorrect
    packets could disrupt your HVAC system operation.

    Example:
        cl2-replay capture.bin --packet 5 --dry-run
        cl2-replay capture.bin --start 10 --end 20
    """
    console.print("[bold red]ComfortLink II Packet Replay Tool[/bold red]\n")
    console.print(
        "[yellow]WARNING: Replaying packets can affect HVAC operation.[/yellow]"
    )
    console.print("[yellow]Only proceed if you understand what you're doing.[/yellow]\n")

    replayer = PacketReplayer(port, baud)
    replayer.load_capture(Path(capture_file))

    if not dry_run:
        if not Confirm.ask("Are you sure you want to send packets to the bus?"):
            console.print("Aborted.")
            return
        replayer.connect()

    try:
        if packet is not None:
            if dry_run:
                _, data = replayer.packets[packet]
                console.print(f"[dim]Would send:[/dim] {data.hex(' ')}")
            else:
                replayer.replay_single(packet)
        else:
            end_idx = end if end is not None else len(replayer.packets)
            if dry_run:
                console.print(f"[dim]Would replay packets {start} to {end_idx - 1}[/dim]")
                for i in range(start, min(end_idx, start + 10)):
                    _, data = replayer.packets[i]
                    console.print(f"  {i}: {data.hex(' ')[:60]}...")
                if end_idx - start > 10:
                    console.print(f"  ... and {end_idx - start - 10} more")
            else:
                replayer.replay_sequence(start, end_idx, preserve_timing=not no_timing)
    finally:
        replayer.disconnect()


if __name__ == "__main__":
    main()
