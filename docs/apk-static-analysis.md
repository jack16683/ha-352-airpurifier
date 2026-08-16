# 352Air 3.2.16 APK static analysis

This document records static findings from the archived official Android APK.
The APK was not installed or executed, and the analysis did not send packets to
the purifier.

## Artifact

- Package: `com.bugull.threefivetwoaircleaner`
- Version: `3.2.16` (`versionCode 30216`)
- APK SHA-256:
  `9463447c889ff84df41d6d7b66a7b58a8f7d585a5d9b5aeed6f056999ee4176f`
- Signing certificate SHA-1:
  `02b0ec07460dfe8aba353c175514c685345a23fa`

## Product model versus wire protocol

The APK has two different model-number namespaces. They must not be treated as
the same field.

`ui/device/data/DeviceType.pointType` identifies the product selected in the
UI. Its separate `value` field groups products for pairing and is not the
number in this table:

| `pointType` | Model |
| ---: | --- |
| 1 | M25 |
| 2 | X83 |
| 3 | G30 |
| 4 | X83C |
| 5 | X50 |
| 6 | X50S |
| 7 | X83C Plus |
| 8 | X60 |
| 9 | X70 |
| 10 | G45 |

`model/CleanerDeviceType` identifies the wire protocol family:

| Protocol value | Family |
| ---: | --- |
| 1 | M25 |
| 2 | X83 |
| 3 | X50 |
| 4 | G30 |

`AddDeviceConnectActivity` explicitly converts both product X83 (`pointType
2`) and product X83C (`pointType 4`) to protocol-family value `2`. Its
analytics helper also labels protocol value `2` as `X83(X83C)`. Therefore an
X83C advertising outer device type `02` is expected; it does not make the
product an X83.

For Home Assistant this means the device identity should remain `X83C`, while
packet assembly and parsing should use the shared X83-family wire format.

The complete mapping for X83C Plus, X50/X50S/X60/X70, G30/G45, and M25,
including their distinct command frames and current support boundary, is in
[`device-protocol-families.md`](device-protocol-families.md).

## X83-family state parser

`network/wifi/b/g` dispatches outer device type `02` to
`network/wifi/b/b`, whose 33-byte state payload starts with `5A A1`.
The outer packet places this payload at offset 16.

| Inner offset | Outer offset | Meaning |
| ---: | ---: | --- |
| 3 | 19 | high nibble: filter type; low nibble: operating mode |
| 4 | 20 | wind-speed level, 1 through 6 |
| 5 | 21 | timer selection |
| 6 | 22 | air-quality class |
| 7 | 23 | child lock (`00`/`11`) |
| 8 | 24 | display light (`00` on, `11` off) |
| 9 | 25 | purifier power (`00` on, `11` off) |
| 10-11 | 26-27 | remaining timer, big-endian |
| 12-13 | 28-29 | PM2.5, big-endian |
| 19-20 | 35-36 | total online time base value |
| 21 | 37 | total-air-value decimal exponent |
| 22-23 | 38-39 | total-air-value base value |
| 24 | 40 | total-purification decimal exponent |
| 25-26 | 41-42 | total-purification base value |
| 27 | 43 | linkage state |

The parser accepts low-nibble modes `01`, `02`, `03`, `04`, and `05` and
stores each value directly. This independently confirms that X83C's observed
manual status `04` is valid. The APK's outgoing mode table is
`[01, 02, 03, 05]`, so its manual command still sends `05`; incoming values
`04` and `05` are both understood.

## Command construction

`DeviceCommandBuilder` constructs the same six-byte inner commands used by the
integration:

- mode: command `51`, values `[01, 02, 03, 05]`
- wind speed: command `52`, values `01` through `06`
- light: command `56`, values `[00, 11]`
- power: command `5E`, values `[35, 11]`
- fixed state query: `A5 A0 11 11 00 00`

For normal control commands it forms `A5 A0 <command> <value> 00` and appends
the low byte of their unsigned sum. `ProtocolHeaderBuilder` then writes the
MAC, sequence, company code, protocol device type, and per-device authentication
code into the outer packet. In particular, the authentication code is read
from the `Device` object rather than being a universal constant.

Local discovery is a separate case. `buildDeviceFoundCommand` emits command
`23` with company code `F1`, the selected protocol-family type, and the fixed
app authentication code `CB76`. It does not use an X83/X83C device auth code
such as `0504` or `0403`. The integration therefore uses `CB76` only for its
broadcast discovery/wakeup packet and continues to use the learned per-device
code for state queries and controls.

## Local and cloud routing

The APK is hybrid rather than cloud-only:

- `SenderController.sendData` selects the TCP path for a device marked online.
- Otherwise it selects UDP when `Device.isLocalConnect()` is true and sends to
  the device IP on port `11530`.
- Both paths carry the same wrapped device command, and the response parser
  emits separate `TCP_ACCESSIBLE` and `UDP_ACCESSIBLE` states.

The cloud bootstrap endpoint is hard-coded as `352.yunext.com:11591`. After
connecting, the APK asks the load-balancer for a work server, connects to that
returned address, and joins it using the stored login token. A router-side
capture observed the returned worker `120.27.152.66:11573`.

## TLS behavior

The cloud TCP implementation requests an `SSLContext` named `TLS`, but supplies
a custom `X509TrustManager` whose `checkClientTrusted` and
`checkServerTrusted` methods both return without validating anything. It also
creates a raw `SSLSocket` without hostname verification.

The APK contains `gs_intermediate_ca.crt` and `root.cer`, and `TcpManager`
opens both resources during initialization, but the resulting streams are not
passed to the SSL context. The context is instead initialized with the
trust-all manager. This explains why a runtime capture can accept an expired,
hostname-mismatched certificate.

This cloud weakness is useful for understanding the discontinued service, but
the Home Assistant integration does not need it: the X83C authentication code
is available in local status packets, so local UDP operation can remain fully
independent of the vendor account and cloud.

## Login API and current outage

The old APK builds its Retrofit client with the fixed base URL
`https://352.yunext.com`. Relevant endpoints include:

- `api2/user/loginByPwd`
- `api2/user/loginBySms`
- `api2/verifyToken`
- `api2/device/getDeviceList`

Password login submits `username`, an uppercase MD5 digest of the password,
`appType=1`, `appVersion`, and `sign`. To calculate `sign`, the APK sorts all
parameter names, joins them as `key=value&...`, and signs the UTF-8 bytes with
`SHA1withRSA`. The same PKCS#8 RSA private key is embedded in every copy of the
APK, so this signature is client reproduction rather than meaningful client
authentication.

As checked on 2026-08-17, Google Public DNS over HTTPS returns `NXDOMAIN` for
`352.yunext.com`. The local resolver used during analysis instead synthesized
`28.0.4.45`, but that address closed port 443 before completing a TLS
handshake. Consequently the archived APK cannot reach password login, token
verification, or the device-list API even with valid credentials.

### Minimum offline APK patch

The static control flow suggests that a full fake cloud server is unnecessary:

1. `SplashActivity.a(Long)` sends a stored token to `verifyToken`; an empty or
   rejected token goes to `PasswordLoginActivity`. Its private `t()` method
   starts `MainActivity` directly. A minimal patch can make this decision point
   call `t()` unconditionally.
2. The existing add-device UI converts X83C to protocol type `02` and performs
   local discovery.
3. On a `LOCAL_FOUND` event, the add-device presenter fills the local `Device`
   model and calls `DeviceCollection.addNewDevice` directly. There is no HTTP
   request in this persistence method, so the MAC and advertised auth code can
   be learned and saved without the dead account API.

This still requires rebuilding and re-signing the APK. Cloud history, sharing,
firmware updates, and remote TCP control would remain unavailable, and the
original pairing UI may reconfigure Wi-Fi. Home Assistant is therefore the
safer routine-control path, while an offline APK can be treated as a separate
optional experiment.
