"""Helpers for assembling the 352 local UDP protocol."""

from __future__ import annotations

from .const import MODEL_DEVICE_TYPE


READ_STATE_COMMAND = "1111"
DISCOVERY_AUTH_CODE = 0xCB76
MODE_BY_CODE = {
    1: "auto",
    2: "sleep",
    3: "turbo",
    # X83C status captures report manual as 4. Older X83 protocol tables use 5.
    4: "manual",
    5: "manual",
}

TIMER_HOURS_BY_CODE = {
    0x00: 0,
    0x01: 1,
    0x02: 2,
    0x03: 3,
    0x05: 5,
    0x08: 8,
}


def _apk_scaled_value(exponent: int, base_value: int) -> int:
    """Apply the decimal scaling used by the archived Android application."""
    if exponent < 4:
        return base_value * (10**exponent)
    return base_value


def parse_x83_state(data: bytes) -> dict[str, object]:
    """Parse stable X83-family state fields from a complete UDP datagram.

    The offsets and accepted values mirror the archived 352Air 3.2.16 parser.
    Unknown enum values are omitted so a malformed or newer packet cannot
    replace the last known-good Home Assistant state with invented data.
    """
    if (
        len(data) < 44
        or data[0] != 0xA1
        or data[13] != 0x02
        or data[16:19] != b"\x02\x5A\xA1"
    ):
        return {}

    state: dict[str, object] = {}
    mode_and_filter = data[19]

    mode = MODE_BY_CODE.get(mode_and_filter & 0x0F)
    if mode is not None:
        state["mode"] = mode

    speed = data[20]
    if 1 <= speed <= 6:
        state["speed"] = speed

    timer_code = data[21]
    timer_hours = TIMER_HOURS_BY_CODE.get(timer_code)
    if timer_hours is not None:
        state["timer_hours"] = timer_hours
        state["timer_remaining_minutes"] = int.from_bytes(data[26:28], "big")

    # The APK parser accepts three air-quality classes. Keep the wire value as
    # an integer until its presentation labels are independently confirmed.
    air_quality_level = data[22]
    if air_quality_level in (1, 2, 3):
        state["air_quality_level"] = air_quality_level

    child_lock = data[23]
    if child_lock in (0x00, 0x11):
        state["child_lock"] = child_lock == 0x11

    display = data[24]
    if display in (0x00, 0x11):
        state["light"] = display == 0x00

    power = data[25]
    if power in (0x00, 0x11):
        state["power"] = "ON" if power == 0x00 else "OFF"

    state["pm25"] = int.from_bytes(data[28:30], "big")

    filter_type = (mode_and_filter & 0xF0) >> 4
    state["filter_installed"] = "已安装" if filter_type in (1, 2) else "未安装"

    total_air = _apk_scaled_value(data[37], int.from_bytes(data[38:40], "big"))
    if total_air < 9_999_999:
        state["total_air"] = total_air

    total_purification = _apk_scaled_value(
        data[40], int.from_bytes(data[41:43], "big")
    )
    if total_purification < 9_999_999:
        state["total_purification"] = total_purification

    return state


def parse_f072_state(data: bytes, g30_family: bool = False) -> dict[str, object]:
    """Parse the statically mapped X50/G30 F072 state family."""
    if len(data) < 51 or data[16:18] != b"\xF0\x72":
        return {}

    base = 24
    state: dict[str, object] = {}
    mode_and_filter = data[base + 3]
    mode = MODE_BY_CODE.get(mode_and_filter & 0x0F)
    if mode is not None:
        state["mode"] = mode

    state["speed"] = data[base + 4]
    timer_code = data[base + 5]
    if timer_code in TIMER_HOURS_BY_CODE:
        state["timer_hours"] = TIMER_HOURS_BY_CODE[timer_code]
        state["timer_remaining_minutes"] = int.from_bytes(
            data[base + 10:base + 12], "big"
        )

    if data[base + 6] in (1, 2, 3):
        state["air_quality_level"] = data[base + 6]
    if data[base + 7] in (0x00, 0x11):
        state["child_lock"] = data[base + 7] == 0x11
    if data[base + 8] in (0x00, 0x11):
        state["light"] = data[base + 8] == 0x00
    if data[base + 9] in (0x00, 0x11):
        state["power"] = "ON" if data[base + 9] == 0x00 else "OFF"

    state["pm25"] = int.from_bytes(data[base + 12:base + 14], "big")
    state["filter_installed"] = (
        "已安装" if ((mode_and_filter & 0xF0) >> 4) in (1, 2) else "未安装"
    )
    state["total_air"] = _apk_scaled_value(
        data[base + 21], int.from_bytes(data[base + 22:base + 24], "big")
    )
    state["total_purification"] = _apk_scaled_value(
        data[base + 24], int.from_bytes(data[base + 25:base + 27], "big")
    )

    if g30_family and len(data) >= 54:
        state.update(
            {
                "temperature": data[base + 14],
                "humidity": data[base + 15],
                "co2": int.from_bytes(data[base + 16:base + 18], "big"),
                "ptc": data[base + 18],
                "air_volume": int.from_bytes(data[base + 27:base + 29], "big"),
                "linkage_state": data[base + 29],
            }
        )
    elif len(data) >= 54:
        state["linkage_state"] = data[base + 29]

    return state


def parse_m25_state(data: bytes) -> dict[str, object]:
    """Parse the APK's short M25 detector frames."""
    if len(data) < 7 or data[1] != 0xF5:
        return {}
    if data[0] in (0xA1, 0xA2) and len(data) == 17:
        return {
            "pm25": int.from_bytes(data[3:5], "big"),
            "linkage_state": data[6],
        }
    if data[0] in (0xA3, 0xA4) and len(data) >= 6:
        return {"backlight": data[5]}
    return {}


def parse_discovery_response(data: bytes) -> dict[str, object] | None:
    """Parse the APK's 27-byte local discovery response."""
    if (
        len(data) < 27
        or data[0:2] != b"\xA1\x06"
        or data[12] != 0xF1
        or data[16] != 0x23
        or data[2:8] != data[21:27]
    ):
        return None

    device_type = data[13]
    auth_code = int.from_bytes(data[14:16], "big")
    if device_type == 0x01:
        model = "m25"
    elif device_type == 0x02:
        # X83/X83C/X83C Plus share type 02. Auth 0403 identifies the tested
        # X83C; the confirmation form permits correction for other products.
        model = "x83c" if auth_code == 0x0403 else "x83"
    elif device_type == 0x03:
        model = "x50"
    elif device_type == 0x04:
        model = "g30"
    else:
        return None

    return {
        "host": ".".join(str(part) for part in data[17:21]),
        "mac": data[2:8].hex().upper(),
        "model": model,
        "device_type": device_type,
        "auth_code": auth_code,
    }


def build_device_command(command: str) -> bytes:
    """Build the inner MCU command used by X83-family purifiers.

    Control commands end in the low byte of the sum of the preceding five
    bytes. The read-state command is the protocol's fixed six-byte query and
    does not use that checksum.
    """
    command_bytes = bytes.fromhex(command)
    if len(command_bytes) != 2:
        raise ValueError("a device command must contain exactly two bytes")

    payload = bytes.fromhex("A5A0") + command_bytes + b"\x00"
    if command == READ_STATE_COMMAND:
        return payload + b"\x00"
    return payload + bytes((sum(payload) & 0xFF,))


def _device_type(model: str) -> int:
    """Return the shared outer protocol type for a configured product."""
    try:
        return MODEL_DEVICE_TYPE[model]
    except KeyError as err:
        raise ValueError(f"Unsupported model: {model}") from err


def assemble_discovery_packet(mac: str, model: str, sequence: int = 0) -> bytes:
    """Build the APK's local broadcast search packet.

    Discovery uses the app authentication code 0xCB76. It does not use the
    device-specific authentication code carried by state and control packets.
    """
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError("MAC address must contain exactly six bytes")

    header = b"\xA1\x04" + mac_bytes + b"\x08\x00"
    sequence_bytes = (sequence & 0xFFFF).to_bytes(2, "big")
    body = (
        bytes((0xF1, _device_type(model)))
        + DISCOVERY_AUTH_CODE.to_bytes(2, "big")
        + b"\x23"
    )
    return header + sequence_bytes + body


def assemble_packet(
    mac: str,
    model: str,
    sequence: int,
    command: str,
    auth_code: int = 0x0504,
) -> bytes:
    """Wrap an inner MCU command in the purifier's UDP packet header."""
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError("MAC address must contain exactly six bytes")

    # X83 and X83C share device type 0x02. X83C differs through its advertised
    # auth code and some reported state values, not the outer device type.
    device_type = _device_type(model)
    header = b"\xA1\x04" + mac_bytes + b"\x0E\x00"
    sequence_bytes = (sequence & 0xFFFF).to_bytes(2, "big")
    if not 0 <= auth_code <= 0xFFFF:
        raise ValueError("auth code must fit in two bytes")
    body = bytes((0xF1, device_type)) + auth_code.to_bytes(2, "big") + b"\x01"
    return header + sequence_bytes + body + build_device_command(command)
