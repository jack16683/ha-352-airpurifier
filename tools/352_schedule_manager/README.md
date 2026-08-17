# 352 本机循环定时管理器

这是一个独立的 Python 命令行小工具，用于查看和管理 352 净化器 MCU
内部保存的 4 个循环开关机定时槽。它只访问所选局域网设备的 UDP
`11530`，不登录、连接或修改 352 云服务，也不依赖 Home Assistant。

已通过旧版 APK 静态分析确认定时查询和写入帧格式；X83C 已实机验证
自动扫描、仅 IP 连接、查询、设置、启用、停用和清除全部定时。写入功能
带有写前查询、单次写入和连续两次回读校验，校验失败时不会自动重发。
X83/X83C Plus、X50 系列及 G30/G45 共用 APK 中的定时构造器，但除
X83C 外尚无对应实机验证，可能不可用。

## 要求

- Python 3.10 或更高版本
- Windows、Linux 或 macOS
- 电脑与净化器之间能够双向传递 UDP `11530`
- 自动扫描或仅填写 IP 时，电脑通常需要和设备处于同一二层网段

EasyTier、Tailscale 等三层 VPN 常常只能转发单播 IP，不能转发设备回到
UDP `11530` 的广播/定向回包。这种情况下建议把工具复制到家庭局域网内
的电脑、OpenWrt 或 Home Assistant 终端运行。跨网段手动连接时至少同时
填写 `--host` 和 `--mac`。

工具只使用 Python 标准库，无需安装依赖：

```bash
cd tools/352_schedule_manager
python3 schedule_manager.py
```

不带参数会进入中文交互菜单，可选择扫描或手动输入 IP。
操作失败时不会结束程序：设备连接错误会返回设备选择，查询、设置或
清除错误会返回当前设备菜单，可直接换选项重试。

## 命令行用法

扫描当前 `/24` 网段，也可用 `--subnet` 明确指定：

```bash
python3 schedule_manager.py scan
python3 schedule_manager.py scan --subnet 192.168.1.0/24
```

查询设备的 4 个定时槽：

```bash
python3 schedule_manager.py query \
  --host 192.168.1.50 \
  --mac AA:BB:CC:DD:EE:FF \
  --model x83c
```

同网段能从 ARP/邻居表取得 MAC 时可以省略 `--mac`。示例中的地址均为
占位符，不对应真实设备。

设置 1 号槽为每天 19:00 开机、23:00 关机：

```bash
python3 schedule_manager.py set \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c \
  --slot 1 --on 19:00 --off 23:00 --days all
```

只设置开机或关机时，另一项填 `-`。星期支持英文缩写或中文，例如
`--days mon,wed,fri`、`--days 周一,周三,周五`。

启用、停用指定槽：

```bash
python3 schedule_manager.py enable  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c --slot 1
python3 schedule_manager.py disable --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c --slot 1
```

清除全部定时：

```bash
python3 schedule_manager.py clear \
  --host 192.168.1.50 --mac AA:BB:CC:DD:EE:FF --model x83c
```

所有写操作默认要求二次确认。自动化脚本可以显式添加 `--yes`，但建议
先执行 `query` 并保存当前结果。

## 发现与手动参数

扫描会先填充系统邻居表，只对厂家 OUI `00:95:69` 的候选地址发送 APK
定义的只读 `0x23` 定向发现包，同时监听设备状态广播。Windows 使用
`arp -a`，Linux 使用 `/proc/net/arp`、`ip neigh` 和 `arp`，macOS 使用
`arp -n -a`；不同平台的输出格式均已覆盖。发现响应会提供实际协议族、
company 和设备鉴权码。

如果系统不允许 Python 读取邻居表，工具会监听最长 22 秒，从净化器的
周期状态广播直接学习 IP、MAC、协议族和鉴权码。因此自动扫描和仅填写
IP 不会只依赖某一个操作系统命令；主动发现成功时会提前结束等待。

如果 VPN 或防火墙使发现回包不可达，可以手动提供型号；工具会使用该
型号的已知默认协议族和鉴权码。需要覆盖时可传 `--company` 与 `--auth`
（十六进制）。手动默认值只是兼容回退，可靠性低于设备发现响应。

支持的型号参数：`x83`、`x83c`、`x83c-plus`、`x50`、`x50s`、`x60`、
`x70`、`g30`、`g45`。M25 是检测仪，APK 中没有净化器循环定时协议，
因此只会被扫描列出，不允许执行定时读写。
