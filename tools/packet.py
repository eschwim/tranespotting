"""
ComfortLink II Packet Parser

Based on Net485 protocol structure:
- 10-byte header
- 0-240 byte payload
- 2-byte checksum
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class MessageType(IntEnum):
    """Known message types (to be populated during reverse engineering)."""

    UNKNOWN = 0x00
    # Add discovered message types here
    # READ = 0x01
    # WRITE = 0x02
    # ACK = 0x03
    # etc.


@dataclass
class Packet:
    """Represents a ComfortLink II packet."""

    raw: bytes
    timestamp: float = 0.0

    # Parsed header fields (10 bytes based on Net485)
    # These field names are tentative - update as protocol is understood
    dest_addr: int = 0
    src_addr: int = 0
    msg_type: int = 0
    sequence: int = 0
    payload_length: int = 0
    header_extra: bytes = field(default_factory=bytes)

    # Payload and checksum
    payload: bytes = field(default_factory=bytes)
    checksum: int = 0
    checksum_valid: bool = False

    # Parsing status
    parse_error: Optional[str] = None

    @classmethod
    def from_bytes(cls, data: bytes, timestamp: float = 0.0) -> "Packet":
        """Parse a packet from raw bytes."""
        packet = cls(raw=data, timestamp=timestamp)

        if len(data) < 12:  # Minimum: 10 header + 2 checksum
            packet.parse_error = f"Packet too short: {len(data)} bytes"
            return packet

        try:
            # Parse header (tentative field assignments)
            # These are guesses based on similar protocols - adjust as you learn more
            packet.dest_addr = (data[0] << 8) | data[1]
            packet.src_addr = (data[2] << 8) | data[3]
            packet.msg_type = data[4]
            packet.sequence = data[5]
            packet.payload_length = data[6]
            packet.header_extra = data[7:10]

            # Extract payload
            payload_end = 10 + packet.payload_length
            if payload_end > len(data) - 2:
                packet.parse_error = f"Payload length mismatch: expected {packet.payload_length}, available {len(data) - 12}"
                packet.payload = data[10:-2]
            else:
                packet.payload = data[10:payload_end]

            # Extract checksum (last 2 bytes)
            packet.checksum = (data[-2] << 8) | data[-1]

            # Validate checksum
            packet.checksum_valid = packet._verify_checksum()

        except Exception as e:
            packet.parse_error = f"Parse error: {e}"

        return packet

    def _verify_checksum(self) -> bool:
        """Verify the packet checksum.

        The actual algorithm is unknown - this is a placeholder.
        Common options to try:
        - CRC-16 (various polynomials)
        - Simple sum
        - XOR-based
        """
        # TODO: Implement once checksum algorithm is determined
        # For now, return True to not reject packets
        return True

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """Calculate checksum for data.

        Placeholder - implement once algorithm is known.
        """
        # Common algorithms to try:
        # 1. CRC-16-CCITT
        # 2. CRC-16-IBM
        # 3. Simple 16-bit sum
        # 4. Fletcher-16

        # Placeholder: simple sum modulo 65536
        return sum(data) & 0xFFFF

    def to_hex(self, separator: str = " ") -> str:
        """Return packet as hex string."""
        return self.raw.hex(separator)

    def format_header(self) -> str:
        """Format header for display."""
        return (
            f"[{self.src_addr:04X} -> {self.dest_addr:04X}] "
            f"Type:{self.msg_type:02X} Seq:{self.sequence:02X} Len:{self.payload_length}"
        )

    def format_payload(self) -> str:
        """Format payload for display, showing both hex and ASCII."""
        if not self.payload:
            return "(empty)"

        hex_part = self.payload.hex(" ")
        # Show printable ASCII characters
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in self.payload)

        return f"{hex_part}  |{ascii_part}|"

    def __str__(self) -> str:
        if self.parse_error:
            return f"[ERROR] {self.parse_error}: {self.to_hex()}"

        checksum_status = "OK" if self.checksum_valid else "BAD"
        return f"{self.format_header()} CRC:{checksum_status}\n  Payload: {self.format_payload()}"


def find_packet_boundaries(data: bytes) -> list[tuple[int, int]]:
    """Attempt to find packet boundaries in a data stream.

    This is heuristic-based and will need refinement as the protocol
    is better understood.

    Returns list of (start, end) byte offsets.
    """
    # Placeholder - implement as protocol structure becomes clear
    # For now, return the entire buffer as one packet
    return [(0, len(data))]
