"""Helpers for assembling and parsing the 352 local UDP protocol."""

from __future__ import annotations

from .const import MODEL_DEVICE_TYPE


READ_STATE_COMMAND = "1111"
DISCOVERY_AUTH_CODE = 0xCB76
MODE_BY_CODE = {
    1: "auto",
    2: "sleep",
    3: "turbo",
    # X83C reports manual as 4; older X83 protocol tables use 5.
    4: "manual",
    5: "manual",
}
F072_MODE_BY_CODE = {
    1: "auto",
    2: "sleep",
    3: "turbo",
    5: "purify",
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
    """Parse stable X83-family fields from a complete UDP datagram."""
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

    # The APK accepts three values, but their presentation labels are unknown.
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


def parse_x50_state(data: bytes) -> dict[str, object]:
    """Parse the APK-defined X50 F072 state frame."""
    if len(data) < 51 or data[13] != 0x03 or data[16:18] != b"\xF0\x72":
        return {}

    inner_length = int.from_bytes(data[18:20], "big") + 2
    if inner_length < 15 or len(data) < 16 + inner_length:
        return {}
    inner = data[16 : 16 + inner_length]
    if crc16_genibus(inner[2:-2]) != int.from_bytes(inner[-2:], "big"):
        return {}

    base = 24
    state: dict[str, object] = {}
    mode_and_filter = data[base + 3]

    mode_code = mode_and_filter & 0x0F
    state["mode_code"] = mode_code
    mode = F072_MODE_BY_CODE.get(mode_code)
    if mode is not None:
        state["mode"] = mode

    state["speed"] = data[base + 4]
    timer_code = data[base + 5]
    if timer_code in TIMER_HOURS_BY_CODE:
        state["timer_hours"] = TIMER_HOURS_BY_CODE[timer_code]
        state["timer_remaining_minutes"] = int.from_bytes(
            data[base + 10 : base + 12], "big"
        )

    if data[base + 6] in (1, 2, 3):
        state["air_quality_level"] = data[base + 6]
    if data[base + 7] in (0x00, 0x11):
        state["child_lock"] = data[base + 7] == 0x00
    if data[base + 8] in (0x00, 0x11):
        state["light"] = data[base + 8] == 0x00
    if data[base + 9] in (0x00, 0x11):
        state["power"] = "ON" if data[base + 9] == 0x00 else "OFF"

    state["pm25"] = int.from_bytes(data[base + 12 : base + 14], "big")
    state["filter_installed"] = (
        "已安装" if ((mode_and_filter & 0xF0) >> 4) in (1, 2) else "未安装"
    )
    state["total_air"] = _apk_scaled_value(
        data[base + 21], int.from_bytes(data[base + 22 : base + 24], "big")
    )
    state["total_purification"] = _apk_scaled_value(
        data[base + 24], int.from_bytes(data[base + 25 : base + 27], "big")
    )
    return state


def parse_discovery_response(data: bytes) -> dict[str, object] | None:
    """Parse the APK's 27-byte local discovery response."""
    if (
        len(data) < 27
        or data[0:2] != b"\xA1\x06"
        or data[16] != 0x23
        or data[2:8] != data[21:27]
    ):
        return None

    device_type = data[13]
    auth_code = int.from_bytes(data[14:16], "big")
    if device_type == 0x02:
        # X83 and X83C share type 02. Auth 0403 identifies the tested X83C;
        # the confirmation form permits correction for other products.
        model = "x83c" if auth_code == 0x0403 else "x83"
    elif device_type == 0x03:
        model = "x50"
    else:
        return None

    return {
        "host": ".".join(str(part) for part in data[17:21]),
        "mac": data[2:8].hex().upper(),
        "model": model,
        "device_type": device_type,
        "company_code": data[12],
        "auth_code": auth_code,
    }


def crc16_genibus(data: bytes) -> int:
    """Return the CRC-16/GENIBUS used by X50 F072 commands."""
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ 0x1021) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return crc ^ 0xFFFF


def build_f072_command(
    sequence: int,
    command: int,
    value: int,
) -> bytes:
    """Build the APK's unverified 15-byte X50 MCU command."""
    if not 0 <= value <= 0xFF:
        raise ValueError("command value is outside its wire range")
    inner = bytearray(15)
    inner[0:4] = b"\xF0\x72\x00\x0D"
    inner[4:7] = b"\x03\x04\x02"
    inner[7:9] = (sequence & 0xFFFF).to_bytes(2, "big")
    inner[9:13] = bytes((0x03, command, value, 0x00))
    inner[13:15] = crc16_genibus(bytes(inner[2:13])).to_bytes(2, "big")
    return bytes(inner)


def assemble_inner_packet(
    mac: str,
    model: str,
    sequence: int,
    inner: bytes,
    *,
    company_code: int = 0xF1,
    auth_code: int = 0x0504,
) -> bytes:
    """Wrap an APK-style selector and F072 command in the UDP header."""
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError("MAC address must contain exactly six bytes")
    if model != "x50":
        raise ValueError(f"F072 control is not implemented for model: {model}")
    if not 0 <= company_code <= 0xFF:
        raise ValueError("company code must fit in one byte")
    if not 0 <= auth_code <= 0xFFFF:
        raise ValueError("auth code must fit in two bytes")

    payload = b"\x01" + inner
    header = b"\xA1\x04" + mac_bytes + bytes((len(payload) + 7, 0))
    return (
        header
        + (sequence & 0xFFFF).to_bytes(2, "big")
        + bytes((company_code, 0x03))
        + auth_code.to_bytes(2, "big")
        + payload
    )


def build_device_command(command: str) -> bytes:
    """Build an X83-family MCU command and its one-byte checksum."""
    command_bytes = bytes.fromhex(command)
    if len(command_bytes) != 2:
        raise ValueError("a device command must contain exactly two bytes")

    payload = bytes.fromhex("A5A0") + command_bytes + b"\x00"
    if command == READ_STATE_COMMAND:
        return payload + b"\x00"
    return payload + bytes((sum(payload) & 0xFF,))


def _device_type(model: str) -> int:
    """Return the outer protocol type for a configured product."""
    try:
        return MODEL_DEVICE_TYPE[model]
    except KeyError as err:
        raise ValueError(f"Unsupported model: {model}") from err


def assemble_discovery_packet(mac: str, model: str, sequence: int = 0) -> bytes:
    """Build the APK's read-only local discovery packet."""
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
    company_code: int = 0xF1,
    auth_code: int = 0x0504,
) -> bytes:
    """Wrap an inner X83-family command in the UDP packet header."""
    if model not in ("x83", "x83c"):
        raise ValueError(f"Control is not implemented for model: {model}")

    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError("MAC address must contain exactly six bytes")
    if not 0 <= auth_code <= 0xFFFF:
        raise ValueError("auth code must fit in two bytes")
    if not 0 <= company_code <= 0xFF:
        raise ValueError("company code must fit in one byte")

    header = b"\xA1\x04" + mac_bytes + b"\x0E\x00"
    sequence_bytes = (sequence & 0xFFFF).to_bytes(2, "big")
    body = bytes((company_code, 0x02)) + auth_code.to_bytes(2, "big") + b"\x01"
    return header + sequence_bytes + body + build_device_command(command)
