# 352 device protocol families

This document separates product names from wire-protocol families in the
archived official Android application `352Air 3.2.16`. All findings below are
from static analysis unless a hardware-capture reference is stated explicitly.
No X50, G30, G45, X60, X70, X50S, X83C Plus, or M25 hardware was available for
active validation.

## Product and protocol mapping

The APK uses three related values that must not be conflated:

- `pointType` identifies the product selected in the add-device UI.
- `DeviceType.value` groups products for the pairing flow.
- `Device.deviceType` is the protocol-family byte placed in packet headers.

| `pointType` | Product | Pairing group | Wire `deviceType` | Protocol family |
| ---: | --- | ---: | ---: | --- |
| 1 | M25 | 1 | `01` | M25 detector |
| 2 | X83 | 2 | `02` | X83 |
| 3 | G30 | 3 | `04` | G30 fresh-air fan |
| 4 | X83C | 2 | `02` | X83 |
| 5 | X50 | 5 | `03` | X50 |
| 6 | X50S | 5 | `03` | X50 |
| 7 | X83C Plus | 2 | `02` | X83 |
| 8 | X60 | 5 | `03` | X50 |
| 9 | X70 | 5 | `03` | X50 |
| 10 | G45 | 3 | `04` | G30 fresh-air fan |

`AddDeviceConnectActivity` performs the final pairing-group-to-wire conversion:
group 1 becomes protocol 1, group 2 becomes protocol 2, group 5 becomes
protocol 3, and group 3 becomes protocol 4.

This mapping establishes a shared packet grammar, not automatic model support.
Different products in one family can still have different commands, status
values, or physical features. The integration exposes the APK-derived controls
for experimentation, but only X83C was validated in this work; an exposed
control must not be interpreted as evidence that a model or firmware accepts it.

## Common outer UDP wrapper

`ProtocolHeaderBuilder` wraps device payloads as follows:

```text
A1 04 <MAC:6> <payload-length+7> 00 <outer-sequence:2>
<company-code> <deviceType> <auth-code:2> <payload...>
```

The company code, wire device type, and authentication code come from the
specific `Device` object. They are not universal constants. A local
implementation should learn them from that device's broadcast/status packet
and must not copy X83 values into another family.

The first payload byte is a selector. Known purifier/fan commands use `01`;
X83-family status broadcasts observed on hardware use selector `02` before the
`5A A1` status body.

## X83 family: X83, X83C, X83C Plus

The X83 family uses the short `A5 A0` command body documented in
[`x83c-local-protocol.md`](x83c-local-protocol.md). X83C has been validated on
real hardware. X83 and X83C Plus share wire `deviceType 02` in the APK, but
this project has not independently captured those products.

## X50 family: X50, X50S, X60, X70

The X50 family does **not** use the X83 short control body. Its ordinary
control body is a 15-byte framed command:

```text
F0 72 00 0D 03 04 02 <inner-sequence:2>
03 <command> <value> 00 <crc16:2>
```

The length field is the total inner-frame length minus two. The CRC covers
bytes 2 through 12, initializes to `FFFF`, uses polynomial `1021`, does not
reflect input/output, complements the final value, and stores it big-endian.
That is CRC-16/GENIBUS (`init=FFFF`, `xorout=FFFF`). The inner command sequence
is distinct from the sequence in the outer UDP wrapper.

Static command construction in `X50MainPresenter` is:

| Action | Command | Values |
| --- | ---: | --- |
| Read state | `11` | `11` |
| Mode | `51` | `01` auto, `02` sleep, `03` turbo, `05` purify |
| Speed | `52` | `01`, `02`, `03`, `04`, `05`, `00` |
| PTC | `53` | `00`, `01`, `02` |
| Timer | `54` | `00`, `01`, `02`, `03`, `05`, `08` hours |
| Child lock | `55` | `00` on, `11` off |
| Display | `56` | `00` on, `11` off |
| Power | `5E` | `00` on, `11` off |

The sixth speed position deliberately encodes as `00`; it must not be replaced
with X83's `06`. Mode labels follow the same APK UI order as the X83 family,
but no X50 hardware capture is available to confirm every reported value.

The X50 parser validates an `F0 72` response, removes its first eight bytes and
trailing CRC, and treats the remaining state core as beginning at outer UDP
offset 24:

| Core offset | Outer offset | Meaning |
| ---: | ---: | --- |
| 3 | 27 | filter high nibble and mode low nibble |
| 4 | 28 | speed |
| 5 | 29 | timer selection |
| 6 | 30 | raw three-value air-quality class |
| 7 | 31 | child lock |
| 8 | 32 | display |
| 9 | 33 | power |
| 10-11 | 34-35 | remaining timer, big-endian |
| 12-13 | 36-37 | PM2.5, big-endian |
| 19-26 | 43-50 | accumulated values and decimal exponents |
| 29 | 53 | linkage |

The Home Assistant integration implements this F072 builder and exposes power,
mode, six speed positions, display, timer, and child-lock controls. Community
feedback on the original project confirms that X50 status was readable on real
hardware, while its older X83-style controls did not operate the device. The
new F072 controls come from APK static analysis and have not been hardware
validated.

## G30 family: G30, G45

G30/G45 use the same F072 envelope and CRC as X50, with wire `deviceType 04`:

```text
F0 72 00 0D 04 04 02 <inner-sequence:2>
03 <command> <value-or-high> <zero-or-low> <crc16:2>
```

The APK builds ordinary mode, light, power, child-lock, and timer commands
through this frame. Family-specific controls include:

| Action | Command | Encoding |
| --- | ---: | --- |
| Read state | `11` | value `11` |
| Mode | `51` | `01` auto, `05` purify confirmed by the G30 UI |
| PTC heater | `53` | one-byte value |
| Display | `56` | `00` on, `11` off |
| Air volume / wind | `58` | 16-bit big-endian value |
| Power | `5E` | `00` on, `11` off |

The 16-bit wind value is not interchangeable with the X83/X50 discrete speed
table. The G30 state core also starts at outer offset 24 and adds these fields:

| Core offset | Outer offset | Meaning |
| ---: | ---: | --- |
| 12-13 | 36-37 | PM2.5 |
| 14 | 38 | temperature |
| 15 | 39 | humidity |
| 16-17 | 40-41 | CO2, big-endian |
| 18 | 42 | PTC state |
| 27-28 | 51-52 | 16-bit air volume / wind value |

G30 and G45 expose experimental query, power, mode, display, timer, child lock,
PTC, and 16-bit air-volume controls. The APK slider establishes 40-300 m³/h
for G30 and 40-450 m³/h for G45, in steps of 5. Home Assistant maps nonzero
fan percentages linearly across those ranges and reserves 0% for power-off.
The percentage conversion is an integration design choice; all controls remain
unvalidated on G30/G45 hardware.

## M25 detector family

M25 is an air detector, not a purifier fan. After the selector byte, its parser
handles short frames whose byte 1 is `F5`:

- types `A1`/`A2`, length 17: PM2.5 at bytes 3-4 and linkage at byte 6;
- types `A3`/`A4`: backlight response/state at byte 5.

The APK's local detector query is `FA A0 11 11 00 00`. Backlight writes are
`FA A3 03 01 <00|01> <sum>`, and its separate backlight query is
`FA A4 02 01 A1`. These use route byte `03`, unlike purifier route `01`.
The integration therefore exposes M25 sensors and an
experimental backlight entity, but no invented purifier fan controls. Linkage
pairing depends on another device/cloud-side configuration and is read-only.

## Current support boundary

| Product | Current HA behavior | Evidence |
| --- | --- | --- |
| X83C | Local status, power, speed, modes, display, timer and child lock | APK plus X83C hardware captures |
| X83 | X83-family status and control | Original project declares hardware use; not revalidated in this work |
| X50 | Hardware-reported readable status; experimental F072 controls | Status community-tested; new controls APK-only |
| X83C Plus | Experimental X83-family status and control | APK family mapping only; may not work |
| X50S, X60, X70 | Experimental F072 status and control | Family inference only; may not work |
| G30, G45 | Experimental environmental state and controls | APK static analysis only; may not work |
| M25 | Experimental detector state and backlight control | APK static analysis only; may not work |

For a model to move out of the experimental tier, capture at least one state
query and every exposed reversible control on real hardware, verify response
sequences and state transitions, and learn its device-specific company and
authentication fields.

Original project and community hardware reports are preserved at
<https://bbs.hassbian.com/thread-32155-1-1.html>. They support the X83 claim and
X50 status reading, but they do not validate this integration's new F072
control implementation.
