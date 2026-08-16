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
values, or physical features, so each family requires a real capture before
control is enabled.

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
| Mode | `51` | `01`, `02`, `03`, `05` |
| Speed | `52` | `01`, `02`, `03`, `04`, `05`, `00` |
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

The current Home Assistant integration retains a legacy passive subset of this
parser for X50 broadcasts. It intentionally exposes no X50 fan/light control
entities and sends no active X50 query, because the F072 command path has not
been implemented or verified against hardware.

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
| Mode | `51` | one-byte mode value |
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

G30 and G45 are selectable as experimental passive parsers. They are not
hardware-validated, queried, or controllable by the current integration.

## M25 detector family

M25 is an air detector, not a purifier fan. Its parser handles short frames
whose byte 1 is `F5`:

- types `A1`/`A2`, length 17: PM2.5 at bytes 3-4 and linkage at byte 6;
- types `A3`/`A4`: backlight response/state at byte 5.

The APK can route some M25 operations over TCP and exposes sensor/linkage/light
behavior rather than purifier fan semantics. M25 therefore uses a separate
experimental sensor-only HA entity model. It is selectable, but has not been
validated on hardware and may not work.

## Current support boundary

| Product | Current HA behavior | Evidence |
| --- | --- | --- |
| X83C | Local status, power, speed, modes, display, timer and child lock | APK plus X83C hardware captures |
| X83 | X83-family implementation | APK family mapping; not revalidated in this work |
| X50 | Experimental passive status subset only; no active query/control | APK static parser only |
| X83C Plus | Experimental passive X83-family status | APK family mapping only; may not work |
| X50S, X60, X70 | Experimental passive F072-family status | Family inference only; may not work |
| G30, G45 | Experimental passive environmental state | APK static parser only; may not work |
| M25 | Experimental passive detector state | APK static parser only; may not work |

Before enabling another family, capture at least one state query and one
reversible control action on real hardware, verify the response sequence and
state transition, learn the device-specific company/authentication fields, and
add packet-level regression fixtures.
