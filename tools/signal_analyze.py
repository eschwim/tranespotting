#!/usr/bin/env python3
"""
Signal Analysis Tool

Helps determine the physical layer type (EnviraCOM vs RS-485) and
analyze captured waveforms from logic analyzers or oscilloscopes.

Supports:
- Saleae Logic exports (CSV)
- PulseView/sigrok exports (CSV)
- Raw sample data
"""

import csv
import statistics
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def load_csv_samples(filepath: Path, time_col: int = 0, data_col: int = 1) -> list[tuple[float, float]]:
    """Load time/value pairs from CSV file."""
    samples = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        # Skip header if present
        first_row = next(reader)
        try:
            float(first_row[time_col])
            # First row is data, not header
            samples.append((float(first_row[time_col]), float(first_row[data_col])))
        except ValueError:
            pass  # Was header row

        for row in reader:
            if len(row) > max(time_col, data_col):
                try:
                    samples.append((float(row[time_col]), float(row[data_col])))
                except ValueError:
                    continue

    return samples


def find_edges(samples: list[tuple[float, float]], threshold: float = 0.5) -> list[tuple[float, str]]:
    """Find rising and falling edges in sample data."""
    edges = []
    prev_state = samples[0][1] > threshold

    for time, value in samples[1:]:
        state = value > threshold
        if state != prev_state:
            edge_type = "rising" if state else "falling"
            edges.append((time, edge_type))
            prev_state = state

    return edges


def analyze_pulse_widths(edges: list[tuple[float, str]]) -> dict:
    """Analyze pulse widths to determine baud rate."""
    if len(edges) < 2:
        return {"error": "Not enough edges"}

    widths = []
    for i in range(len(edges) - 1):
        width = edges[i + 1][0] - edges[i][0]
        widths.append(width)

    if not widths:
        return {"error": "No pulse widths calculated"}

    # Find clusters of similar widths (bit periods)
    widths_sorted = sorted(widths)
    min_width = widths_sorted[0]
    max_width = widths_sorted[-1]
    mean_width = statistics.mean(widths)
    median_width = statistics.median(widths)

    # Estimate baud rate from shortest pulse
    estimated_baud = 1.0 / min_width if min_width > 0 else 0

    return {
        "pulse_count": len(widths),
        "min_width_ms": min_width * 1000,
        "max_width_ms": max_width * 1000,
        "mean_width_ms": mean_width * 1000,
        "median_width_ms": median_width * 1000,
        "estimated_baud": estimated_baud,
        "widths": widths,
    }


def classify_physical_layer(analysis: dict) -> dict:
    """Classify the physical layer based on pulse analysis."""
    if "error" in analysis:
        return {"classification": "unknown", "confidence": 0, "reason": analysis["error"]}

    min_width = analysis["min_width_ms"]
    estimated_baud = analysis["estimated_baud"]

    # EnviraCOM: 120 baud = 8.33ms bit period at 60Hz
    enviracom_bit_period = 8.33  # ms

    # RS-485 common rates
    rs485_rates = {
        9600: 0.104,   # ms
        19200: 0.052,
        38400: 0.026,
        57600: 0.017,
        115200: 0.0087,
    }

    # Check for EnviraCOM (very slow, ~8ms pulses)
    if 6.0 < min_width < 12.0:
        return {
            "classification": "EnviraCOM",
            "confidence": 90,
            "reason": f"Pulse width {min_width:.2f}ms matches EnviraCOM 120 baud (~8.33ms)",
            "estimated_baud": 120,
        }

    # Check for RS-485 (fast pulses)
    if min_width < 1.0:
        # Find closest RS-485 rate
        best_match = None
        best_diff = float("inf")
        for rate, period in rs485_rates.items():
            diff = abs(min_width - period)
            if diff < best_diff:
                best_diff = diff
                best_match = rate

        return {
            "classification": "RS-485",
            "confidence": 80,
            "reason": f"Fast pulses ({min_width:.3f}ms) suggest RS-485",
            "estimated_baud": best_match or int(estimated_baud),
        }

    return {
        "classification": "unknown",
        "confidence": 30,
        "reason": f"Pulse width {min_width:.2f}ms doesn't match known patterns",
        "estimated_baud": int(estimated_baud),
    }


def check_ac_synchronization(samples: list[tuple[float, float]], ac_freq: float = 60.0) -> dict:
    """Check if edges are synchronized to AC line frequency."""
    edges = find_edges(samples)
    if len(edges) < 10:
        return {"synchronized": False, "reason": "Not enough edges"}

    ac_period = 1.0 / ac_freq
    half_period = ac_period / 2

    # Check if edge times are multiples of half-period
    edge_phases = []
    for edge_time, _ in edges:
        phase = (edge_time % half_period) / half_period
        edge_phases.append(phase)

    # If synchronized, phases should cluster near 0 or 1
    phase_variance = statistics.variance(edge_phases) if len(edge_phases) > 1 else 1.0

    synchronized = phase_variance < 0.1

    return {
        "synchronized": synchronized,
        "phase_variance": phase_variance,
        "ac_frequency": ac_freq,
        "reason": "Edges aligned to AC zero-crossings" if synchronized else "Edges not synchronized to AC",
    }


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--time-col", default=0, help="CSV column index for time")
@click.option("--data-col", default=1, help="CSV column index for data")
@click.option("--threshold", default=0.5, help="Logic level threshold")
@click.option("--ac-freq", default=60.0, help="AC line frequency (Hz)")
def main(input_file: str, time_col: int, data_col: int, threshold: float, ac_freq: float):
    """Analyze captured signal to determine physical layer type.

    Input should be a CSV file with time and voltage/logic level columns.
    Export from Saleae Logic, PulseView, or similar tools.

    Example:
        python -m tools.signal_analyze capture.csv
        python -m tools.signal_analyze scope_data.csv --time-col 0 --data-col 2
    """
    console.print("[bold blue]ComfortLink II Signal Analyzer[/bold blue]\n")

    filepath = Path(input_file)
    console.print(f"[dim]Loading: {filepath}[/dim]")

    samples = load_csv_samples(filepath, time_col, data_col)
    console.print(f"[green]Loaded {len(samples)} samples[/green]")

    if len(samples) < 10:
        console.print("[red]Not enough samples for analysis[/red]")
        return

    # Time range
    duration = samples[-1][0] - samples[0][0]
    console.print(f"[dim]Duration: {duration * 1000:.2f}ms[/dim]\n")

    # Find edges and analyze pulses
    edges = find_edges(samples, threshold)
    console.print(f"Found {len(edges)} edges")

    analysis = analyze_pulse_widths(edges)

    if "error" not in analysis:
        # Pulse statistics table
        stats_table = Table(title="Pulse Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Pulse count", str(analysis["pulse_count"]))
        stats_table.add_row("Min width", f"{analysis['min_width_ms']:.3f} ms")
        stats_table.add_row("Max width", f"{analysis['max_width_ms']:.3f} ms")
        stats_table.add_row("Mean width", f"{analysis['mean_width_ms']:.3f} ms")
        stats_table.add_row("Median width", f"{analysis['median_width_ms']:.3f} ms")

        console.print(stats_table)

    # Classification
    classification = classify_physical_layer(analysis)

    class_table = Table(title="\nPhysical Layer Classification")
    class_table.add_column("Property", style="cyan")
    class_table.add_column("Value", style="green")

    class_table.add_row("Type", classification["classification"])
    class_table.add_row("Confidence", f"{classification['confidence']}%")
    class_table.add_row("Estimated baud", str(classification.get("estimated_baud", "N/A")))
    class_table.add_row("Reason", classification["reason"])

    console.print(class_table)

    # AC synchronization check (for EnviraCOM)
    if classification["classification"] == "EnviraCOM":
        console.print("\n[yellow]Checking AC synchronization...[/yellow]")
        ac_check = check_ac_synchronization(samples, ac_freq)

        if ac_check["synchronized"]:
            console.print(f"[green]Edges ARE synchronized to {ac_freq}Hz AC[/green]")
        else:
            console.print(f"[yellow]Edges NOT clearly synchronized to AC[/yellow]")
        console.print(f"[dim]Phase variance: {ac_check['phase_variance']:.4f}[/dim]")

    # Recommendations
    console.print("\n[bold]Recommendations:[/bold]")
    if classification["classification"] == "EnviraCOM":
        console.print("- You'll need custom hardware to interface with this bus")
        console.print("- See docs/protocol/enviracom_physical.md for circuit designs")
        console.print("- Consider looking for a W8735A serial adapter (discontinued)")
    elif classification["classification"] == "RS-485":
        console.print(f"- Use a USB to RS-485 adapter")
        console.print(f"- Try baud rate: {classification.get('estimated_baud', 19200)}")
        console.print("- Run: python -m tools.capture -b <baud_rate>")
    else:
        console.print("- Capture more data or verify probe connection")
        console.print("- Try different threshold values")


if __name__ == "__main__":
    main()
