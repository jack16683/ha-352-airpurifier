"""Constants for the 352 X83-family integration."""

DOMAIN = "air_352_x83"
UDP_PORT = 11530

MODELS = {
    "x83c": "352 X83C",
    "x83": "352 X83",
    "x50": "352 X50（实验性控制，APK 分析）",
}

CONTROL_MODELS = frozenset(("x83", "x83c", "x50"))
X83_FAMILY_MODELS = frozenset(("x83", "x83c"))
X50_FAMILY_MODELS = frozenset(("x50",))

MODEL_DEVICE_TYPE = {
    "x83": 0x02,
    "x83c": 0x02,
    "x50": 0x03,
}

COMMANDS = {
    "on": "5E35",
    "off": "5E11",
    "speed_1": "5201",
    "speed_2": "5202",
    "speed_3": "5203",
    "speed_4": "5204",
    "speed_5": "5205",
    "speed_6": "5206",
    "light_on": "5600",
    "light_off": "5611",
    "auto": "5101",
    "sleep": "5102",
    "turbo": "5103",
    "timer_off": "5400",
    "timer_1h": "5401",
    "timer_2h": "5402",
    "timer_3h": "5403",
    "timer_5h": "5405",
    "timer_8h": "5408",
    "child_lock_on": "5511",
    "child_lock_off": "5500",
    "query": "1111",
}

TIMER_OPTION_TO_ACTION = {
    "关闭": (0, "timer_off"),
    "1 小时": (1, "timer_1h"),
    "2 小时": (2, "timer_2h"),
    "3 小时": (3, "timer_3h"),
    "5 小时": (5, "timer_5h"),
    "8 小时": (8, "timer_8h"),
}
