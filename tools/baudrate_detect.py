#!/usr/bin/env python3
"""
Baud Rate Detection Tool

Attempts to auto-detect the baud rate of the ComfortLink II bus
by trying common rates and looking for valid packet patterns.
"""

import time

import click
import serial
from rich.console import Console
from rich.progress import Progress

console = Console()

# Common HVAC baud rates to try
COMMON_BAUD_RATES = [
    9600,
    19200,
    38400,
    57600,
    115200,
    4800,
    2400,
    1200,
]


def try_baud_rate(port: str, baud: int, sample_time: float = 2.0) -> tuple[int, bytes]:
    """Try a baud rate and return byte count and sample data."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=0.1,
        )

        # Collect data for sample_time seconds
        data = bytearray()
        start = time.time()
        while time.time() - start < sample_time:
            if ser.in_waiting:
                data.extend(ser.read(ser.in_waiting))
            time.sleep(0.01)

        ser.close()
        return len(data), bytes(data)

    except serial.SerialException as e:
        console.print(f"[red]Error at {baud} baud:[/red] {e}")
        return 0, b""


def analyze_data_quality(data: bytes) -> dict:
    """Analyze data to guess if baud rate is correct."""
    if not data:
        return {"score": 0, "reason": "No data received"}

    # Count printable ASCII vs garbage
    printable = sum(1 for b in data if 32 <= b < 127)
    printable_ratio = printable / len(data)

    # Count 0x00 and 0xFF (often indicates wrong baud rate)
    nulls = data.count(0x00)
    ones = data.count(0xFF)
    noise_ratio = (nulls + ones) / len(data)

    # Look for repeating patterns (good sign)
    has_patterns = False
    for pattern_len in [10, 12, 14, 16]:  # Common packet sizes
        for i in range(len(data) - pattern_len * 2):
            if data[i : i + pattern_len] == data[i + pattern_len : i + pattern_len * 2]:
                has_patterns = True
                break

    # Calculate score
    score = 50
    if noise_ratio > 0.3:
        score -= 30
    if 0.05 < printable_ratio < 0.5:
        score += 20  # Some ASCII is good, too much might be wrong
    if has_patterns:
        score += 30

    reason = []
    if noise_ratio > 0.3:
        reason.append(f"High noise ({noise_ratio:.0%} 0x00/0xFF)")
    if has_patterns:
        reason.append("Repeating patterns found")
    if 0.05 < printable_ratio < 0.5:
        reason.append(f"Some ASCII ({printable_ratio:.0%})")

    return {
        "score": max(0, min(100, score)),
        "reason": ", ".join(reason) if reason else "Inconclusive",
        "printable_ratio": printable_ratio,
        "noise_ratio": noise_ratio,
        "has_patterns": has_patterns,
    }


@click.command()
@click.option("-p", "--port", default="/dev/ttyUSB0", help="Serial port")
@click.option(
    "--sample-time",
    default=3.0,
    type=float,
    help="Seconds to sample at each baud rate",
)
@click.option("--all", "try_all", is_flag=True, help="Try all rates even after finding good match")
def main(port: str, sample_time: float, try_all: bool):
    """Auto-detect ComfortLink II bus baud rate.

    Tries common baud rates and analyzes the received data to
    determine which rate produces valid-looking packets.

    Example:
        cl2-baudrate -p /dev/ttyUSB0 --sample-time 5
    """
    console.print("[bold blue]ComfortLink II Baud Rate Detection[/bold blue]\n")
    console.print(f"[dim]Port: {port}[/dim]")
    console.print(f"[dim]Sample time: {sample_time}s per rate[/dim]\n")

    results = []

    with Progress() as progress:
        task = progress.add_task("Testing baud rates...", total=len(COMMON_BAUD_RATES))

        for baud in COMMON_BAUD_RATES:
            progress.update(task, description=f"Testing {baud} baud...")
            byte_count, data = try_baud_rate(port, baud, sample_time)

            if byte_count > 0:
                analysis = analyze_data_quality(data)
                results.append(
                    {
                        "baud": baud,
                        "bytes": byte_count,
                        "data": data,
                        **analysis,
                    }
                )

                # Show sample
                sample = data[:40].hex(" ") if data else ""
                console.print(
                    f"  [cyan]{baud:6d}[/cyan] baud: "
                    f"{byte_count:5d} bytes, "
                    f"score: {analysis['score']:3d} "
                    f"[dim]({analysis['reason']})[/dim]"
                )
                console.print(f"    [dim]Sample: {sample}...[/dim]")

                # Stop early if we found a good match
                if analysis["score"] >= 80 and not try_all:
                    console.print(f"\n[green]Good match found at {baud} baud![/green]")
                    break
            else:
                console.print(f"  [dim]{baud:6d} baud: No data[/dim]")

            progress.advance(task)

    # Summary
    if results:
        console.print("\n[bold]Results Summary:[/bold]")
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        best = sorted_results[0]
        console.print(f"\n[green]Best match: {best['baud']} baud[/green]")
        console.print(f"  Score: {best['score']}")
        console.print(f"  Bytes received: {best['bytes']}")
        console.print(f"  Analysis: {best['reason']}")

        if best["score"] < 50:
            console.print(
                "\n[yellow]Warning: Low confidence. Consider using an oscilloscope "
                "to measure the actual baud rate.[/yellow]"
            )
    else:
        console.print("\n[red]No data received at any baud rate.[/red]")
        console.print("Check your wiring and ensure the HVAC system is powered on.")


if __name__ == "__main__":
    main()
