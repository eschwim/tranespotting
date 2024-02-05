"""Tests for packet parsing."""

import pytest

from tools.packet import Packet


class TestPacket:
    """Tests for Packet class."""

    def test_packet_too_short(self):
        """Packets under 12 bytes should fail."""
        data = bytes([0x00] * 10)
        packet = Packet.from_bytes(data)
        assert packet.parse_error is not None
        assert "too short" in packet.parse_error.lower()

    def test_packet_minimum_size(self):
        """Minimum valid packet is 12 bytes (10 header + 2 checksum)."""
        # 10 byte header + 2 byte checksum, 0 byte payload
        data = bytes([0x20, 0x01, 0x40, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        packet = Packet.from_bytes(data)
        assert packet.parse_error is None
        assert packet.dest_addr == 0x2001
        assert packet.src_addr == 0x4001

    def test_packet_with_payload(self):
        """Test parsing packet with payload."""
        # Header with payload_length = 4
        header = bytes([0x20, 0x01, 0x40, 0x01, 0x01, 0x00, 0x04, 0x00, 0x00, 0x00])
        payload = bytes([0x48, 0x56, 0x41, 0x43])  # "HVAC"
        checksum = bytes([0x00, 0x00])

        data = header + payload + checksum
        packet = Packet.from_bytes(data)

        assert packet.parse_error is None
        assert packet.payload_length == 4
        assert packet.payload == payload

    def test_to_hex(self):
        """Test hex string output."""
        data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        packet = Packet(raw=data)
        assert packet.to_hex() == "de ad be ef"
        assert packet.to_hex(separator="") == "deadbeef"

    def test_format_header(self):
        """Test header formatting."""
        data = bytes([0x20, 0x01, 0x40, 0x01, 0x05, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        packet = Packet.from_bytes(data)

        header_str = packet.format_header()
        assert "4001" in header_str  # src addr
        assert "2001" in header_str  # dest addr
        assert "05" in header_str.lower()  # msg type

    def test_format_payload_ascii(self):
        """Test payload formatting shows ASCII."""
        header = bytes([0x00] * 10)
        payload = bytes([0x48, 0x45, 0x4C, 0x4C, 0x4F])  # "HELLO"
        checksum = bytes([0x00, 0x00])

        # Manually set payload for this test
        packet = Packet(raw=header + payload + checksum)
        packet.payload = payload

        formatted = packet.format_payload()
        assert "HELLO" in formatted


class TestPacketTimestamp:
    """Tests for packet timestamps."""

    def test_timestamp_preserved(self):
        """Timestamp should be preserved through parsing."""
        data = bytes([0x00] * 12)
        timestamp = 1234567890.123

        packet = Packet.from_bytes(data, timestamp=timestamp)
        assert packet.timestamp == timestamp


# Placeholder for checksum tests once algorithm is determined
class TestChecksum:
    """Tests for checksum calculation."""

    @pytest.mark.skip(reason="Checksum algorithm not yet determined")
    def test_checksum_calculation(self):
        """Test checksum calculation once algorithm is known."""
        pass

    @pytest.mark.skip(reason="Checksum algorithm not yet determined")
    def test_checksum_validation(self):
        """Test checksum validation once algorithm is known."""
        pass
