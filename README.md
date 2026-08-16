# 352 Air Purifier for Home Assistant

![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

专为 352 品牌智能空气净化器打造的 Home Assistant 局域网本地集成插件。
X83/X83C 控制不依赖已失效的 352 云服务，直接使用局域网 UDP 协议。

## ✨ 型号与证据等级 (Models and confidence)

| 型号 | 当前行为 | 把握程度 |
| --- | --- | --- |
| X83C | 状态、风机/模式/风量、屏幕、定时、童锁控制 | **高：本机逐项抓包验证** |
| X83 | X83 协议族状态与控制 | 中：APK 明确同族，未用 X83 硬件复测 |
| X83C Plus | 实验性被动状态，不发控制 | 低：仅 APK 协议族映射 |
| X50 | 实验性 F072 被动状态，不主动查询/控制 | 低：仅 APK 静态解析 |
| X50S / X60 / X70 | 实验性 F072 被动状态，不主动查询/控制 | **很低：纯协议族推断，可能不可用** |
| G30 / G45 | 实验性温湿度、CO2、PM2.5、PTC、风量被动状态 | **很低：纯静态推断，可能不可用** |
| M25 | 实验性 PM2.5、联动、背光被动状态 | **很低：纯静态推断，可能不可用** |

“可在配置页选择”不等于已经验证。除 X83/X83C 外，集成不会主动发送
查询或控制帧，以免把错误协议发给未验证设备。

## 🚀 核心特性 (Features)
* ⚡ **X83 系列完全本地化**：不依赖 352 官方云服务器，断网依然可用。
* ⚡ **局域网状态同步**：采用 UDP 广播/单播机制。
* 🌬️ **X83 系列风机控制**：支持开关机、1-6 档风速调节。
* 🎛️ **X83 系列模式切换**：支持自动、睡眠、极速、手动模式。
* ⏲️ **硬件关机定时**：支持关闭、1、2、3、5、8 小时，状态来自设备回包。
* 💡 **X83 系列灯光控制**：屏幕灯光开关。
* 📊 **丰富传感器**：实时 PM2.5、空气质量等级、滤芯安装状态、定时剩余分钟、累计空气量和累计净化空气量。
* 🔒 **童锁控制**：开关实体同时控制并显示净化器童锁状态。

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
   * **设备型号 (Model)**: 选择实际型号；除 X83/X83C 外均为实验性只读
   * **设备 IP (Host)**: 填入净化器在局域网内的 IP (建议在路由器绑定静态 IP)
   * **设备 MAC 地址**: 净化器的 MAC 地址 (格式如 `00:11:22:33:44:55`)
4. X83/X83C 会生成风扇、屏幕灯、关机定时、童锁和状态传感器；
   其他型号只生成对应的实验性被动状态传感器。

## 📝 贡献与支持
本项目通过 APK 静态分析和路由器侧实机抓包还原 352 官方协议。X83C
协议说明、验证帧与分析边界见
[`docs/x83c-local-protocol.md`](docs/x83c-local-protocol.md) 和
[`docs/apk-static-analysis.md`](docs/apk-static-analysis.md)。其他型号的协议族、
长帧 CRC 和支持边界见
[`docs/device-protocol-families.md`](docs/device-protocol-families.md)。
