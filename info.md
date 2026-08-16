# 352 Air Purifier for Home Assistant

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

专为 352 品牌智能空气净化器打造的 Home Assistant 局域网本地集成插件。
**脱离云端，毫秒级响应，完全本地局域网 UDP 控制！**

## ✨ 支持的型号 (Supported Models)
* **352 X83C**：状态与本地控制均已实机验证
* **352 X83**：使用同一协议族，保留原项目的状态与控制支持
* **352 X50**：状态读取有社区实机反馈；F072 控制来自 APK 静态分析，**未实机验证，可能不可用**

## 🚀 核心特性 (Features)
* ⚡ **完全本地化**：不依赖 352 官方云服务器，断网依然可用。
* ⚡ **毫秒级状态同步**：采用 UDP 广播/单播机制，状态秒级反馈。
* 🛡️ **状态护盾机制**：彻底解决 UI 按钮回弹、状态闪烁的痛点。
* 🌬️ **风机控制**：支持开关机、1-6 档无极风速调节。
* 🎛️ **模式切换**：支持自动 (Auto)、睡眠 (Sleep)、极速 (Turbo)、手动 (Manual) 模式。
* ⏲️ **关机定时**：支持关闭、1、2、3、5、8 小时。
* 🔒 **童锁控制**：同步并控制设备童锁。
* 💡 **灯光控制**：屏幕灯光开关（与主机电源智能联动）。
* 📊 **丰富传感器**：实时 PM2.5、滤芯安装状态、定时剩余时间和累计净化量。
* 🔎 **自动发现**：通过 DHCP 候选和只读 UDP 响应识别设备，也可手动填写。

> X50 的电源、1-6 档、模式、屏幕、定时、童锁和 PTC 控制均为实验性。
> 它们使用 APK 中的 F072/CRC-16 帧，不代表任何 X50 固件一定接受。

## 📦 安装方法 (Installation)

### 推荐方法：通过 HACS 安装
1. 打开 Home Assistant，进入 HACS。
2. 点击右上角的三个点 `...` -> **自定义存储库 (Custom repositories)**。
3. 存储库 URL 填入：`https://github.com/yymonday/ha-352-airpurifier`
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
   * **设备型号 (Model)**: 选择 X83C、X83 或 X50
   * **设备 IP (Host)**: 填入净化器在局域网内的 IP (建议在路由器绑定静态 IP)
   * **设备 MAC 地址**: 净化器的 MAC 地址 (格式如 `AA:BB:CC:DD:EE:FF`)
4. 提交后即可自动生成包含风扇、屏幕灯和多个传感器的单一设备卡片！

## 📝 贡献与支持
X83C 的电源、1-6 档风量、自动/睡眠/极速/手动模式、屏幕、童锁和
关机定时均已通过局域网逐项验证；集成不会依赖已经失效的官方云服务。
