# 352 Air Purifier for Home Assistant

![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

专为 352 品牌智能空气净化器打造的 Home Assistant 局域网本地集成插件。
控制不依赖已失效的 352 云服务，直接使用局域网 UDP 协议。

## ✨ 型号与证据等级 (Models and confidence)

| 型号 | 当前行为 | 把握程度 |
| --- | --- | --- |
| X83C | 状态、风机/模式/风量、屏幕、定时、童锁控制 | **高：本机逐项抓包验证** |
| X83 | X83 协议族状态与完整控制 | **原项目已声明实机可用**；本分支未复测该硬件 |
| X83C Plus | 实验性 X83 协议族状态与完整控制 | 低：APK 同族映射，未实测，可能不可用 |
| X50 | F072 状态与实验性完整控制 | **社区实机确认状态可读**；新控制仅由 APK 推导，未实测 |
| X50S / X60 / X70 | F072 状态与实验性完整控制 | **很低：纯协议族推断，可能不可用** |
| G30 / G45 | 环境状态、风机/模式/风量、屏幕、定时、童锁、PTC 实验性控制 | **很低：APK 静态推导，可能不可用** |
| M25 | PM2.5、联动、背光状态与实验性背光控制 | **很低：APK 静态推导，可能不可用** |

“可在配置页选择”不等于已经验证。1.4.0 按用户需求开放了所有 APK
型号的本地控制入口，但每个协议族使用各自的帧格式；不会把 X83 的
`A5 A0` 控制帧发给 X50/G30/M25。除 X83C 外的实验性控制有可能无效、
状态不回显，甚至与个别固件的语义不一致，请只在能观察设备且便于断电
恢复时尝试。原项目讨论中 X83 被作为可用机型；X50 用户则明确报告过
“状态可读、旧版控制无效”，因此本版 X50 控制仍不能写成已验证。
[原项目/社区讨论](https://bbs.hassbian.com/thread-32155-1-1.html)

## 🚀 核心特性 (Features)

* ⚡ **完全本地化**：不依赖 352 官方云服务器，断网依然可用。
* ⚡ **局域网状态同步**：采用 UDP 广播/单播机制。
* 🌬️ **风机控制**：X83/X50 家族使用 1-6 档，G30/G45 使用 APK 的 16 位风量命令。
* 🎛️ **模式切换**：X83 支持自动、睡眠、极速、手动；X50 支持自动、睡眠、极速、极净；G30/G45 只开放 APK 页面确认的自动、极净。
* ⏲️ **硬件关机定时**：支持关闭、1、2、3、5、8 小时，状态来自设备回包。
* 💡 **灯光控制**：净化器屏幕灯，以及 M25 的背光。
* 📊 **丰富传感器**：实时 PM2.5、空气质量等级、滤芯安装状态、定时剩余分钟、累计空气量和累计净化空气量。
* 🔒 **童锁与 PTC**：净化器童锁开关；X50/G30 协议族额外提供实验性 PTC 选择器。

为减少 HomeKit Bridge 中的重复配件，电源、1-6 档风量和模式统一由
一个风扇实体承载；关机定时使用选择器，童锁使用开关。只读的风量、
定时设置和童锁副本会在升级时从实体注册表移除。

## 🔎 自动发现与手动配置

- 自动发现先使用 Home Assistant 的 DHCP 设备清单取得候选 IP/MAC，
  再发送 APK 定义的只读 `0x23` 局域网发现包验证设备。
- 发现响应可以可靠识别协议族和鉴权码，但同族子型号通常无法区分；
  配置确认页会给出推断型号，并允许手工修正。
- X83C 的 `0403` 鉴权码已在本机验证；其他同族产品不能保证用鉴权码
  唯一识别。
- 原有手动填写 IP、MAC、型号的路径完整保留。
- 自动发现不会复刻旧 APK 的 `0x24` 锁定操作，不会修改设备状态。

## 📦 安装方法 (Installation)

### 推荐方法：通过 HACS 安装
1. 打开 Home Assistant，进入 HACS。
2. 点击右上角的三个点 `...` -> **自定义存储库 (Custom repositories)**。
3. 存储库 URL 填入：`https://github.com/jack16683/ha-352-airpurifier`
4. 类别选择：**集成 (Integration)**。
5. 点击添加后，在 HACS 中搜索 `352 Air Purifier` 并下载安装。
6. 重启 Home Assistant。

### 手动安装
1. 下载本仓库的代码。
2. 将 `custom_components/air_352_x83` 文件夹放入你 Home Assistant 根目录的 `custom_components` 文件夹中。
3. 重启 Home Assistant。

## ⚙️ 配置使用 (Configuration)
1. 在 Home Assistant 左侧菜单点击 **配置 (Settings)** -> **设备与服务 (Devices & Services)**。
2. 点击右下角 **添加集成 (Add Integration)**，搜索 `352`。
3. 在弹出的配置框中输入：
   * **设备型号 (Model)**: 选择实际型号；除 X83C 和原项目声明可用的 X83 外均为实验性控制
   * **设备 IP (Host)**: 填入净化器在局域网内的 IP (建议在路由器绑定静态 IP)
   * **设备 MAC 地址**: 净化器的 MAC 地址 (格式如 `AA:BB:CC:DD:EE:FF`，仅为占位示例)
4. X83/X50/G30 协议族会生成风扇、屏幕灯、关机定时、童锁和状态传感器；
   X50/G30 协议族另有 PTC，M25 生成传感器和背光灯实体。

## 📝 贡献与支持
本项目通过 APK 静态分析和路由器侧实机抓包还原 352 官方协议。X83C
协议说明、验证帧与分析边界见
[`docs/x83c-local-protocol.md`](docs/x83c-local-protocol.md) 和
[`docs/apk-static-analysis.md`](docs/apk-static-analysis.md)。其他型号的协议族、
长帧 CRC 和支持边界见
[`docs/device-protocol-families.md`](docs/device-protocol-families.md)。
