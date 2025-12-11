homeassistant-qq
================
QQ 控制 Home Assistant 的助手

## 功能

通过 QQ 群聊接收消息并控制 Home Assistant 设备和服务。

## 工作原理

- 通过 WebSocket 连接到 NapCat（QQ 机器人框架）
- 接收 QQ 群聊消息
- 解析命令并调用 Home Assistant API 控制设备

## TODO

- 实现 Home Assistant 设备控制命令
- 实现设备状态查询
- 支持更多消息类型