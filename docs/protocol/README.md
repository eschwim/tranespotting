# ComfortLink II Protocol Documentation

This directory contains documentation of the ComfortLink II protocol
as discovered through reverse engineering.

## Status

**Protocol analysis in progress**

## Protocol Heritage

Trane ComfortLink II is based on **Honeywell EnviraCOM 2.0** protocol.
The XL850/XL950/XL1050 thermostats are manufactured by Honeywell for Trane.

## Physical Layer Options

**IMPORTANT**: There appear to be TWO different physical layers in use:

### Option 1: Native EnviraCOM Bus (3-wire)

The original EnviraCOM physical layer:

| Parameter | Value |
|-----------|-------|
| **Bus type** | 3-wire (R, C, D) |
| **Power** | 24VAC on R and C lines |
| **Data line** | D - modulated 24VAC |
| **Baud rate** | 120 bps @ 60Hz (100 bps @ 50Hz) |
| **Synchronization** | Bit synchronized to AC line half-cycle |
| **Bit encoding** | Dominant/recessive (like CAN bus) |
| **Max length** | 300 ft end-to-end |
| **Topology** | Star wired with stubs |
| **Arbitration** | Collision resolution via arbitration |
| **Error detection** | CRC |

### Option 2: RS-485 Bus (via relay panel)

When using the BAY24VRPAC52DC relay panel, the system may use RS-485:

| Parameter | Value |
|-----------|-------|
| **Bus type** | RS-485 (EIA-485) |
| **Topology** | Multi-drop bus |
| **Baud rate** | TBD - possibly 19200 or 38400 |
| **Data bits** | 8 |
| **Parity** | None |
| **Stop bits** | 1 |

**You need to determine which physical layer your system uses** by:
1. Examining the wiring between thermostat and relay panel
2. Using an oscilloscope to observe the signal characteristics
3. Checking if data line shows 24VAC modulation or RS-485 differential signaling

## Message Format (EnviraCOM)

Based on EnviraCOM documentation, messages follow this format:

```
[Priority]_[MsgType]_[Instance]_[OpType]_[Length]_[Payload]_[Checksum]
```

### Fields

| Field | Values | Description |
|-------|--------|-------------|
| Priority | H, M, L | High, Medium, Low priority |
| MsgType | 4 hex chars | Message type identifier (e.g., 10E0) |
| Instance | 2 hex chars | Zone or instance number |
| OpType | R, Q, C | Report, Query, Change |
| Length | 2 hex chars | Payload byte count |
| Payload | Variable | Up to 8 two-byte fields |
| Checksum | 2 hex chars | CRC value |

### Known Message Types

| Code | Name | Description |
|------|------|-------------|
| 10E0 | Node Identification 1 | Device discovery - contains OS number |
| 10E1 | Node Identification 2 | Additional device info |
| 3E70 | Device Status | Operating status |
| 1260 | DHW Cylinder Temperature | Domestic hot water temp |
| 10A0 | DHW Cylinder Setpoint | Hot water setpoint |
| 10A1 | DHW Setpoint Range | Setpoint limits |
| 30D0 | DHW Demand | Hot water demand |

*Note: Not all message types may be used by HVAC equipment*

## Device Discovery

1. Controller sends Node Identification 1 (10E0) Query to bus
2. All connected devices respond with Report messages
3. Report contains encoded OS Number (unique device ID)
4. Devices may also send Node Identification 2 and 3 reports

## Alternative Packet Structure (RS-485 variant)

If your system uses RS-485 (Net485-style), the packet structure may be:

```
+--------+--------+--------+
| Header | Payload| Chksum |
| 10 B   | 0-240 B| 2 B    |
+--------+--------+--------+
```

### Header (10 bytes) - Tentative

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-1 | 2 | dest_addr | Destination device address |
| 2-3 | 2 | src_addr | Source device address |
| 4 | 1 | msg_type | Message type |
| 5 | 1 | sequence | Sequence number |
| 6 | 1 | payload_len | Payload length |
| 7-9 | 3 | unknown | Unknown / reserved |

## Hardware Interface Options

### W8735A Serial Adapter (Discontinued)

Honeywell made a serial adapter that bridges EnviraCOM to RS-232:
- **RS-232 side**: 19200 baud, 8N1
- **Status**: Discontinued 2013, rarely available

### DIY Interface

For the native EnviraCOM bus, you need circuitry to:
1. Derive power from 24VAC
2. Detect zero-crossing for synchronization
3. Demodulate the 24VAC data signal
4. Handle dominant/recessive bit arbitration

For RS-485 systems:
- Standard USB to RS-485 adapter (FTDI recommended)

## References

- [EnviraCOM GitHub Project](https://github.com/roy-bentley/enviracom)
- [Net485 Project](https://github.com/kpishere/Net485)
- [Bloominglabs EnviraCOM Info](https://www.bloominglabs.org/index.php/Water_Heater_Monitoring_and_Setback_Control)
- US Patent 6373376B1 (EnviraCOM hardware details)

## Files in This Directory

- `addresses.md` - Known device addresses
- `message_types.md` - Message type definitions
- `payloads.md` - Payload structure for each message type
- `checksum.md` - Checksum algorithm documentation
- `sequences.md` - Common message sequences
- `enviracom_physical.md` - EnviraCOM physical layer details
