# 352 Legacy Local

> [!IMPORTANT]
> This repository is no longer maintained and has been archived. Use the clean-room rewrite at
> [jack16683/ha-352air-legacy-local](https://github.com/jack16683/ha-352air-legacy-local) instead.

[简体中文](README.md) | English

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

A local Home Assistant integration for legacy 352 air purifiers and air
quality monitors. It communicates over the LAN UDP protocol and does not sign
in to a 352 account or depend on the discontinued legacy cloud service.

`Legacy` means that this project covers models found in the archived
`352Air 3.2.16` Android application. It does not claim support for newer 352
products.

## Acknowledgements and origin

Thanks to [yymonday/ha-352-airpurifier](https://github.com/yymonday/ha-352-airpurifier)
for the original Home Assistant implementation and its X83/X50 foundation,
and to the users in the
[Hassbian community thread](https://bbs.hassbian.com/thread-32155-1-1.html)
for their hardware reports. This project uses a different integration domain,
so it can coexist with the original integration. Do not add the same physical
device to both integrations.

Devices purchased around 2019 can still work correctly even though the legacy
official app can no longer complete login. Static analysis shows that login,
token verification, and the device list depend on `352.yunext.com`. On
2026-08-17, that domain no longer resolved through public DNS. To keep working
hardware useful, this project analyzed an archived APK and validated its local
protocol with captures from an owned X83C and router.

The analysis also explains why older integrations could read some X83C units
but could not control them. The old implementation fixed the authentication
code at `0504`, while the tested X83C advertises `0403` in its status packets.
This integration learns the actual authentication code from the device and
uses a separate command format for each protocol family.

## Device support

Availability in the configuration form does not mean that a model has been
tested on real hardware.

| Model | Current support | Evidence and confidence |
| --- | --- | --- |
| X83C | State, power, six speeds, auto/sleep/turbo/manual modes, display, shutdown timer, and child lock | **Every exposed control was validated with X83C captures** |
| X83 | X83-family state and controls | **Reported working by the original project**; not retested here on X83 hardware |
| X50 | State plus experimental F072 controls | **Community hardware reports confirm readable state**; new controls are APK-derived and untested |
| X83C Plus | Experimental X83-family state and controls | APK family mapping only; may not work |
| X50S / X60 / X70 | Experimental F072 state and controls | APK family mapping only; may not work |
| G30 / G45 | Environmental state plus experimental airflow, mode, display, timer, child-lock, and PTC controls | Static APK analysis only; may not work |
| M25 | PM2.5, linkage and backlight state, plus experimental backlight control | Static APK analysis only; M25 is not a purifier |

X83, X50, G30, and M25 use different inner frame formats. The integration
does not send X83 `A5 A0` control frames to another family. Untested controls
may still be ignored or interpreted differently by particular firmware, so
experiment only when the device can be observed and power-cycled if needed.

## Home Assistant features

- LAN discovery and manual configuration by IP, MAC address, and model.
- One fan entity for power, percentage speed, and operating mode, suitable for
  HomeKit Bridge.
- Display light, child lock, shutdown timer, and experimental PTC controls.
- PM2.5, air-quality class, timer remaining, filter type code, current-run air
  volume, lifetime purified-air volume, and other available state.
- Simplified Chinese UI with English fallback for every other HA language.
- Read-only discovery that does not reproduce the old app's device-lock or
  Wi-Fi provisioning writes.

## Install with HACS

1. Open HACS in Home Assistant.
2. Open the top-right menu and select **Custom repositories**.
3. Enter `https://github.com/jack16683/ha-352-legacy-local`.
4. Select **Integration** as the category and add the repository.
5. Find and download **352 Legacy Local** in HACS.
6. Restart Home Assistant.
7. Open **Settings → Devices & services → Add integration** and search for
   **352 Legacy Local**.
8. Try LAN discovery first. If it fails, enter the device IP, MAC address, and
   model manually.

A fixed DHCP lease is recommended. Discovery can identify the protocol family
and authentication fields, but it cannot always distinguish retail models in
the same family. Confirm the model during setup.

### Manual installation

Copy `custom_components/air_352_legacy` into `custom_components` under the Home
Assistant configuration directory, restart HA, and add the integration from
Devices & services.

## Clear recurring schedules left by the old app

Recurring power schedules configured by the old app were not necessarily sent
from the cloud every day. APK analysis and hardware validation show four
recurring schedule slots stored in the purifier MCU. A schedule written in
2019, such as “turn on every day at 07:00,” can therefore keep running even
when the account can no longer log in and the app cannot remove it.

The standalone
[`tools/352_schedule_manager/schedule_manager.py`](tools/352_schedule_manager/schedule_manager.py)
can query, set, disable, or clear these slots without contacting the 352 cloud.
It uses only the Python standard library and supports Windows, Linux, and
macOS.

```bash
cd tools/352_schedule_manager
python3 schedule_manager.py
```

Enter `2` at the language prompt for English, then choose LAN discovery or
manual IP entry. After selecting a device, the tool immediately queries and
shows all four slots. Review them and choose **Clear all schedules** if they
are no longer wanted. Destructive clearing requires typing `CLEAR`.

The command-line form is also available. These addresses are placeholders:

```bash
# Query all four slots
python3 schedule_manager.py query \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c

# Clear all four device-side recurring schedule slots
python3 schedule_manager.py clear \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c
```

See the
[`schedule manager documentation`](tools/352_schedule_manager/README.md) for
interactive input, day/time formats, routed-network parameters, and discovery
details. Schedule reads and writes are hardware-validated on X83C. Other
purifier families use a shared APK schedule builder but remain experimental.

## Recommended: let Home Assistant manage schedules

After clearing legacy device schedules, create separate Home Assistant on and
off automations. Use a time trigger and call the turn-on or turn-off action on
this integration's fan entity. The schedules are then visible, editable, and
easy to disable in one place without depending on the discontinued 352 app.

HA automations require the Home Assistant host and LAN to be available at the
trigger time. Device-side schedules continue to run while HA is offline. If an
offline fallback is required, use the included tool to write an intentional
device schedule, but avoid keeping duplicate HA and device schedules for the
same action.

## Protocol and reverse-engineering notes

- [APK static analysis and legacy service outage](docs/apk-static-analysis.md)
- [Product models and four protocol families](docs/device-protocol-families.md)
- [X83C LAN protocol and hardware validation](docs/x83c-local-protocol.md)

Published code and documentation contain no personal MAC address, private LAN
IP, Home Assistant token, APK file, or raw packet capture. Sanitized hardware
validation reports for other supported models are welcome.

## License

This project retains the original project's [GNU GPL v2](LICENSE). Everyone is
welcome to use, copy, modify, redistribute, and build upon it. Distributions of
modified versions must retain the license and provide the corresponding source
as required by GPL v2.
