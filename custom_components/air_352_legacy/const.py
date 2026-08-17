DOMAIN = "air_352_legacy"
UDP_PORT = 11530

MODELS = {
    "x83c": "352 X83C",
    "x83": "352 X83",
    "x83c_plus": "352 X83C Plus",
    "x50": "352 X50",
    "x50s": "352 X50S",
    "x60": "352 X60",
    "x70": "352 X70",
    "g30": "352 G30",
    "g45": "352 G45",
    "m25": "352 M25",
}

X83_FAMILY_MODELS = frozenset(("x83", "x83c", "x83c_plus"))
X50_FAMILY_MODELS = frozenset(("x50", "x50s", "x60", "x70"))
G30_FAMILY_MODELS = frozenset(("g30", "g45"))
PURIFIER_CONTROL_MODELS = X83_FAMILY_MODELS | X50_FAMILY_MODELS | G30_FAMILY_MODELS
CONTROL_MODELS = PURIFIER_CONTROL_MODELS | frozenset(("m25",))

MODE_LABELS = {action: action for action in ("auto", "sleep", "turbo", "manual", "purify")}
MODE_ACTION_BY_LABEL = {
    **{action: action for action in MODE_LABELS},
    "自动": "auto",
    "睡眠": "sleep",
    "极速": "turbo",
    "手动": "manual",
    "极净": "purify",
}
MODE_CODE_LABELS = {1: "auto", 2: "sleep", 3: "turbo", 4: "manual", 5: "purify"}

# The APK preserves this device field as raw values 1/2/3 without attaching
# labels. This monotonic mapping is inferred from the ordering and an X83C
# reporting value 1 at PM2.5=0; keep the raw value as a sensor attribute.
AIR_QUALITY_LABELS = {1: "excellent", 2: "good", 3: "poor"}

# G30/G45 expose a 16-bit air-volume value rather than six discrete speeds.
# The APK passes the value through unchanged; these product-rated maxima are
# used only to translate Home Assistant's 1-100% fan control.
G30_AIR_VOLUME_RANGE = {"g30": (40, 300), "g45": (40, 450)}
G30_AIR_VOLUME_STEP = 5

MODEL_DEVICE_TYPE = {
    "m25": 0x01,
    "x83": 0x02,
    "x83c": 0x02,
    "x83c_plus": 0x02,
    "x50": 0x03,
    "x50s": 0x03,
    "x60": 0x03,
    "x70": 0x03,
    "g30": 0x04,
    "g45": 0x04,
}

COMMANDS = {
    "on":        "5E35",  "off":       "5E11",
    "speed_1":   "5201",  "speed_2":   "5202",  "speed_3": "5203",
    "speed_4":   "5204",  "speed_5":   "5205",  "speed_6": "5206",
    "light_on":  "5600",  "light_off": "5611",
    "auto":      "5101",  "sleep":     "5102",  "turbo":     "5103",
    "purify":    "5105",
    "timer_off": "5400",  "timer_1h":   "5401",  "timer_2h":  "5402",
    "timer_3h":  "5403",  "timer_5h":   "5405",  "timer_8h":  "5408",
    "child_lock_on": "5511", "child_lock_off": "5500",
    "query":     "1111"
}

TIMER_OPTION_TO_ACTION = {
    "off": (0, "timer_off"),
    "1_hour": (1, "timer_1h"),
    "2_hours": (2, "timer_2h"),
    "3_hours": (3, "timer_3h"),
    "5_hours": (5, "timer_5h"),
    "8_hours": (8, "timer_8h"),
}
