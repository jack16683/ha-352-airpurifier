# X83C local control notes

These notes describe the local UDP control path confirmed against an X83C and
the archived Android application `352Air 3.2.16` (`versionCode 30216`). The APK
was analyzed statically and was not installed or executed.

## Packet layout

Simple X83-family commands use UDP port `11530` and this packet layout:

```text
A1 04 <MAC:6> 0E 00 <sequence:2>
F1 <device-type> <auth-code:2> 01
A5 A0 <command:2> 00 <checksum>
```

- `device-type` is `02` for X83-family devices. X50 advertises type `03`, but
  its controls use a different F072/CRC-16 inner frame and are not compatible
  with the simple layout shown here.
- `auth-code` must be learned from bytes 14-15 of the device's status packet.
  It is not constant across models. The pre-existing integration's hard-coded
  `05 04` value therefore prevents control of X83C units advertising another
  value.
- For control commands, `checksum` is the low eight bits of the sum of the five
  preceding inner-command bytes.
- The fixed read-state inner command is the exception: `A5 A0 11 11 00 00`.
- The broadcast discovery command is another distinct packet type. APK 3.2.16
  uses fixed app authentication code `CB 76` and command `23`; it does not use
  the device-specific authentication code in this packet.

Examples:

| Action | Command | Complete inner command |
| --- | --- | --- |
| Power on | `5E 35` | `A5 A0 5E 35 00 D8` |
| Power off | `5E 11` | `A5 A0 5E 11 00 B4` |
| Display on | `56 00` | `A5 A0 56 00 00 9B` |
| Display off | `56 11` | `A5 A0 56 11 00 AC` |
| Read state | `11 11` | `A5 A0 11 11 00 00` |
| Child lock on | `55 11` | `A5 A0 55 11 00 AB` |
| Child lock off | `55 00` | `A5 A0 55 00 00 9A` |
| Timer 1 hour | `54 01` | `A5 A0 54 01 00 9A` |
| Timer off | `54 00` | `A5 A0 54 00 00 99` |

The display on/off commands and dynamic authentication code were validated on
real hardware by observing the subsequent status broadcast.

## Clean hardware validation

Two router-side captures contain one command at a time and its subsequent
device broadcast. The purifier copies the request sequence into the response,
which makes the command/response pairs unambiguous.

| Sequence | Action | Request suffix | Confirming response | Delay |
| --- | --- | --- | --- | ---: |
| `0003` | Display on | `F1 02 04 03 01 A5 A0 56 00 00 9B` | byte 24 = `00` | 322 ms |
| `0004` | Display off | `F1 02 04 03 01 A5 A0 56 11 00 AC` | byte 24 = `11` | 236 ms |
| `0005` | Speed 2 | `F1 02 04 03 01 A5 A0 52 02 00 99` | mode/filter byte = `24`, speed = `02` | 576 ms |
| `0006` | Auto | `F1 02 04 03 01 A5 A0 51 01 00 97` | mode/filter byte = `21`, speed = `01` | 686 ms |

Capture hashes:

```text
9601343a1a28d27c883252f2dcd4005d1aab33db78198298ce8e36f5f98f9b1e  x83c-local-control-clean.pcap
cda69255d2b35f0febd1fc9e43a9a7f5331d0d4c8d47aeca93b057dfefb534d9  x83c-speed-auto-clean.pcap
```

Additional hardware tests confirmed these zero-based offsets in the complete
49-byte X83C status datagram:

| Offset | State | Validated values |
| ---: | --- | --- |
| 21 | timer selection | `00` off, `01` one hour |
| 22 | air-quality class | APK accepts `01`, `02`, `03`; HA displays inferred `优`, `良`, `差` and retains the raw code |
| 23 | child lock | `00` off, `11` on |
| 26-27 | timer remaining | big-endian minutes; one hour began at `003C` |
| 28-29 | PM2.5 | big-endian integer |
| 37 | total-air decimal exponent | APK scaling rules |
| 38-39 | total-air base | big-endian integer |
| 40 | total-purification decimal exponent | APK scaling rules |
| 41-42 | total-purification base | big-endian integer |

The high nibble at offset 19 is the APK's `filterType`, not a filter-presence
or remaining-life flag. Values 0, 1 and 2 select different airflow tables in
the application. The tested X83C currently reports type 2. Filter lifetime is
managed separately by filter records and is not present in this ordinary
49-byte local status frame.

The tested X83C currently reports its lifetime purification counter as
`04 01 0E`: exponent 4 and base 270, or 2,700,000 m³. The archived APK only
implemented exponent branches 0 through 3 and therefore displayed 270 for
this newer/larger counter value. The integration handles the observed
exponent-4 form as ordinary base-10 scaling.

The timer-off restore was sent from OpenWrt with sequence `0010`; the device
responded with the same sequence, timer selection `00`, and remaining time
`0000`. Home Assistant intentionally gives semantic names only to fields with
stable parser or hardware evidence. The linkage byte is exposed as a raw
numeric diagnostic because its meaning has not been established; the
online-time field remains hidden because its unit is also unknown.

## Complete reversible setting validation

A later single-socket capture validated every setting exposed by the Home
Assistant integration. Requests used increasing sequences `0014` through
`0027`, and each accepted response echoed its request sequence.

- modes: sleep reported `02`, turbo `03`, auto `01`;
- speeds 1 through 6 each reported the requested speed and manual mode `04`;
- shutdown timers `01`, `02`, `03`, `05`, `08` reported respectively 60,
  120, 180, 300, and 480 remaining minutes;
- timer `00` restored both selection and remaining minutes to zero;
- child lock `11` produced state `11`, then `00` restored state `00`.

The APK's outgoing purify command `51 05` and an exploratory `51 04` were both
ignored by this X83C. A speed command is the validated way to enter manual
mode, so the fan entity implements its manual preset by re-sending the current
1-6 speed instead of either ineffective mode command.

The local discovery request `23` was also verified independently. The X83C
returned a 27-byte `A1 06` response containing its MAC, IPv4 address, protocol
family `02`, authentication code `0403`, and the echoed sequence. Discovery is
read-only; the integration never sends the old APK's subsequent lock command.

In X83C status packets, the low nibble of byte 19 is the operating mode. A
physical-button capture confirmed `01` auto, `02` sleep, `03` turbo, and `04`
manual. APK resources label `05` as purify, so it is not aliased to manual.
The tested X83C ignored both outgoing `51 05` and the separately tested
`51 04`; manual therefore uses a validated speed command, while purify remains
an APK-derived control that may depend on firmware or model.

## APK provenance

- Package: `com.bugull.threefivetwoaircleaner`
- Version: `3.2.16` (`versionCode 30216`)
- APK SHA-256:
  `9463447c889ff84df41d6d7b66a7b58a8f7d585a5d9b5aeed6f056999ee4176f`
- Signing certificate SHA-1:
  `02b0ec07460dfe8aba353c175514c685345a23fa`

Relevant APK classes include `DeviceCommandBuilder`,
`CleanerWifiCommandBuilder`, `ProtocolHeaderBuilder`, and the obfuscated
`X83MainPresenter`. `DeviceCommandBuilder` appends the one-byte sum through
the application's byte utility before wrapping the command for UDP transport.
