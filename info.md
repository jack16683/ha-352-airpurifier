# 352 Air Purifier for Home Assistant

![Version](https://img.shields.io/badge/version-1.3.1-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-success.svg)

专为 352 品牌智能空气净化器打造的 Home Assistant 局域网本地集成插件。
X83/X83C 直接使用局域网 UDP 协议，不依赖已失效的 352 云服务。

## ✨ 支持边界 (Support boundary)
* 352 X83C：状态与全部现有控制均经本机抓包验证
* 352 X83：同协议族实现，未在 X83 硬件上复测
* X83C Plus / X50 / X50S / X60 / X70 / G30 / G45 / M25：仅 APK
  静态分析得到的实验性被动状态，可能不可用，不发送查询或控制

## 🚀 核心特性 (Features)
* ⚡ **X83 系列完全本地化**：不依赖 352 官方云服务器，断网依然可用。
* ⚡ **局域网状态同步**：采用 UDP 广播/单播机制。
* 🛡️ **状态护盾机制**：彻底解决 UI 按钮回弹、状态闪烁的痛点。
* 🌬️ **X83 系列风机控制**：支持开关机、1-6 档风速调节。
* 🎛️ **X83 系列模式切换**：支持自动、睡眠、极速、手动模式。
* ⏲️ **硬件关机定时**：支持关闭、1、2、3、5、8 小时。
* 🔒 **童锁控制**：独立开关实体，状态来自设备回包。
* 💡 **X83 系列灯光控制**：屏幕灯光开关。
* 📊 **丰富传感器**：实时 PM2.5、滤芯安装状态、累计净化空气量。

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
   * **设备型号 (Model)**: 选择实际型号；非 X83/X83C 型号均为实验性只读
   * **设备 IP (Host)**: 填入净化器在局域网内的 IP (建议在路由器绑定静态 IP)
   * **设备 MAC 地址**: 净化器的 MAC 地址 (格式如 `00:11:22:33:44:55`)
4. 也可选择自动发现；发现只识别协议族，同族子型号需在确认页核对。
5. X83/X83C 会生成风扇、屏幕灯、关机定时、童锁和状态传感器；
   其他型号只生成实验性被动状态传感器。

## 📝 贡献与支持
本项目通过 APK 静态分析和路由器侧实机抓包还原 352 官方协议。其他型号在获得真实硬件抓包验证前不会启用控制。
