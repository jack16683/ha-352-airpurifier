# 352 Legacy Local

> [!IMPORTANT]
> 此仓库已停止维护并归档。请改用全新重写的
> [jack16683/ha-352air-legacy-local](https://github.com/jack16683/ha-352air-legacy-local)。

简体中文 | [English](README_EN.md)

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

面向 352 旧款空气净化器和检测仪的 Home Assistant 本地集成。项目只使用
局域网 UDP 协议，不登录 352 账号，也不依赖已经失效的旧云服务。

`Legacy` 表示本项目只覆盖旧版 `352Air 3.2.16` APK 中出现的型号，不代表
兼容 352 后续推出的新设备。

## 致谢与项目起因

感谢 [yymonday/ha-352-airpurifier](https://github.com/yymonday/ha-352-airpurifier)
提供最初的 Home Assistant 实现和 X83/X50 支持基础，也感谢
[Hassbian 社区讨论](https://bbs.hassbian.com/thread-32155-1-1.html) 中的实机反馈。
本项目使用新的 integration domain，可以与原项目同时安装；同一台实体设备
不要同时添加到两个集成中。

2019 年前后购买的设备本身仍能正常工作，但旧版官方 App 已无法完成登录。
静态分析确认 App 的登录、令牌校验和设备列表依赖 `352.yunext.com`；在
2026-08-17 检查时该域名已无法从公共 DNS 解析。为了继续使用仍然完好的
硬件，本项目对归档 APK 进行了静态分析，并在自有 X83C 和路由器上抓取、
验证局域网协议。

这也解释了旧集成在部分 X83C 上“能读取、不能控制”的原因：旧实现固定使用
鉴权码 `0504`，实测 X83C 状态包通告的是 `0403`。本项目从设备响应学习实际
鉴权码，并为不同协议族分别构造命令。

## 设备支持程度

“可以在配置页选择”不代表已经经过对应型号实机验证。

| 型号 | 当前支持 | 证据与可靠程度 |
| --- | --- | --- |
| X83C | 状态、电源、1–6 档风量、自动/睡眠/极速/手动、屏幕、关机定时、童锁 | **已在 X83C 上逐项抓包验证** |
| X83 | X83 协议族状态与控制 | **原项目声明实机可用**；本项目未重新测试 X83 硬件 |
| X50 | 状态及实验性 F072 控制 | **社区实机确认状态可读**；新版控制来自 APK，未经实机验证 |
| X83C Plus | 实验性 X83 协议族状态与控制 | 仅有 APK 同族映射，可能不可用 |
| X50S / X60 / X70 | 实验性 F072 状态与控制 | 仅有 APK 协议族映射，可能不可用 |
| G30 / G45 | 环境状态、风量、模式、屏幕、定时、童锁和 PTC 实验性控制 | 仅有 APK 静态分析，可能不可用 |
| M25 | PM2.5、联动和背光状态，实验性背光控制 | 仅有 APK 静态分析；M25 不是净化器 |

X83、X50、G30 和 M25 使用不同的内部帧格式。项目不会把 X83 的 `A5 A0`
控制帧发给其他协议族。未经实测的控制仍可能被某些固件忽略，建议只在能够
观察设备并方便断电恢复时尝试。

## Home Assistant 功能

- 局域网自动发现，以及手动填写 IP、MAC 和型号。
- 风扇实体统一承载电源、风量百分比和工作模式，适合 HomeKit Bridge。
- 屏幕灯、童锁、关机定时和实验性 PTC 控制。
- PM2.5、空气质量、定时剩余、滤芯类型代码、本次及累计净化空气量等状态。
- 简体中文界面；其他 HA 语言自动使用英文。
- 自动发现只读取设备信息，不执行旧 App 的设备锁定或配网写操作。

## 通过 HACS 安装

1. 在 Home Assistant 中打开 HACS。
2. 进入右上角菜单，选择 **自定义存储库（Custom repositories）**。
3. 填入 `https://github.com/jack16683/ha-352-legacy-local`。
4. 类别选择 **集成（Integration）**，然后添加仓库。
5. 在 HACS 中搜索并下载 **352 Legacy Local**。
6. 重启 Home Assistant。
7. 打开 **设置 → 设备与服务 → 添加集成**，搜索 **352 Legacy Local**。
8. 优先尝试局域网自动发现；如果发现失败，可手动填写设备 IP、MAC 和型号。

建议在路由器中为设备绑定固定 DHCP 地址。自动发现可以识别协议族和设备
鉴权信息，但同一协议族中的具体商品型号不一定能仅凭局域网响应区分，添加时
请核对型号。

### 手动安装

将 `custom_components/air_352_legacy` 复制到 Home Assistant 配置目录下的
`custom_components`，重启 HA，然后从“设备与服务”添加集成。

## 先清理设备里遗留的循环定时

旧 App 设置的自动开关机并不一定由云端每天临时下发。APK 和实机验证表明，
净化器 MCU 内部保存了 4 个循环定时槽；因此即使账号已经无法登录，2019 年
写入的“每天 7 点开机”等计划仍可能继续执行，而用户无法再从 App 中删除。

仓库附带独立工具
[`tools/352_schedule_manager/schedule_manager.py`](tools/352_schedule_manager/schedule_manager.py)，
可以在不连接 352 云服务的情况下查询、设置、停用或清空这些槽位。工具只用
Python 标准库，支持 Windows、Linux 和 macOS。

```bash
cd tools/352_schedule_manager
python3 schedule_manager.py
```

直接回车选择中文，然后选择自动扫描或手动输入 IP。选中设备后会自动查询并
显示 4 个定时槽。推荐先确认内容，再选择“清除全部定时”。清除操作会要求输入
`CLEAR`，避免误删。

也可以直接使用命令行。下面的地址和 MAC 都只是占位示例：

```bash
# 查询
python3 schedule_manager.py query \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c

# 清空 4 个设备端循环定时槽
python3 schedule_manager.py clear \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c
```

完整的交互操作、星期和时间格式、跨网段参数及各平台扫描说明见
[`tools/352_schedule_manager/README.md`](tools/352_schedule_manager/README.md)。定时读写已在
X83C 实机验证；其他净化器协议族来自 APK 共用构造器，仍属于实验性支持。

## 推荐：清空后交给 Home Assistant 管理

清除设备里的旧循环定时后，建议在 Home Assistant 中分别创建开机和关机
自动化：使用“时间”作为触发条件，对本集成的风扇实体执行“打开”或“关闭”。
这样所有计划都集中在 HA 中，能够随时查看、停用和修改，也不会再依赖失效的
352 App。

需要注意，HA 自动化要求 Home Assistant 主机和局域网在触发时正常运行；
设备内部定时即使 HA 离线仍会执行。若需要离线兜底，可以用附带工具重新写入
明确的设备端计划，但不要同时保留含义相同的 HA 和设备定时，以免重复执行。

## 协议与逆向分析

- [APK 静态分析与旧服务失效原因](docs/apk-static-analysis.md)
- [各商品型号与四个协议族的映射](docs/device-protocol-families.md)
- [X83C 局域网协议与实机验证记录](docs/x83c-local-protocol.md)

所有公开文档和代码均不包含用户真实 MAC、内网 IP、Home Assistant token、
APK 文件或原始抓包。欢迎对应型号的设备拥有者提交脱敏后的验证结果。

## 许可证

本项目沿用原项目的 [GNU GPL v2](LICENSE)。欢迎任何人免费使用、复制、修改、
二次开发和再发布；分发修改版时请按 GPL v2 保留许可证并提供对应源代码。
