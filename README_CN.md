# HAQBot

[English](README.md) | [中文](README_CN.md)

通过自然语言对话控制 Home Assistant 设备的 QQ 机器人。

## 功能特性

- **自然语言控制**：在 QQ 群中通过文本或语音消息控制 Home Assistant 设备
- **直接命令控制**：通过命令（`/turnon`、`/turnoff`、`/toggle`、`/script`）快速控制设备，无需 LLM 处理
- **Webhook 通知**：Home Assistant 可通过 webhook API 主动向 QQ 群发送通知
- **语音识别**：使用腾讯云 ASR API 自动转录音频消息（可选）
- **多模态支持**：通过 webhook 发送文本消息及文件或视频流
- **实体缓存**：内存缓存实现快速实体查找，避免重复 API 调用
- **权限控制**：通过环境变量限制特定 QQ 用户控制设备
- **国际化支持**：支持中文和英文

## 快速开始

### 前置要求

- 已配置对话代理（Ollama）的 Home Assistant
- NapCat QQ 机器人框架
- （可选）腾讯云 ASR 凭证，用于语音识别

### 安装

1. 克隆此仓库
2. 复制 `.env.default` 到 `.env` 并配置你的设置
3. 使用 Docker Compose 运行：

```bash
docker-compose up -d
```

或直接运行：

```bash
poetry install
poetry run python src/maid/main.py
```

## 配置

### 环境变量

创建 `.env` 文件（参考 `.env.default`）：

```env
# NapCat WebSocket 连接地址
NAPCAT_API=ws://napcat:3001

# Home Assistant 配置
HA_URL=http://homeassistant:8123
HA_TOKEN=你的长期访问令牌
HA_AGENT_ID=conversant.ollama_conversation

# QQ 账号（必需）- 机器人的 QQ 号
ACCOUNT=your_qq_account_number

# 显示昵称（可选，默认：メイド）
DISPLAY_NICKNAME=メイド

# 权限控制（可选）
# 允许控制设备的 QQ 号码，用逗号或空格分隔
# 如果为空，所有用户都可以控制设备
ALLOWED_SENDERS=123456789 987654321

# 语言设置（可选，默认：zh_CN）
LANGUAGE=zh_CN

# 调试模式（可选，默认：false）
DEBUG=false

# Webhook 配置（可选）
WEBHOOK_PORT=8080
WEBHOOK_TOKEN=你的webhook令牌

# 腾讯云 ASR（可选，用于语音识别）
TENCENT_SECRET_ID=你的腾讯云密钥ID
TENCENT_SECRET_KEY=你的腾讯云密钥
TENCENT_ASR_ENGINE=16k_zh
TENCENT_ASR_REGION=
```

### 配置指南

#### Home Assistant 令牌

1. 登录 Home Assistant
2. 进入 个人资料 → 长期访问令牌
3. 创建新令牌并复制到 `HA_TOKEN`

#### 对话代理

确保在 Home Assistant 中配置了 `conversant.ollama_conversation` 对话代理。

---

## 模块 1：命令接口

机器人支持两种方式控制 Home Assistant 设备：**直接命令**和**自然语言消息**。

### 自然语言消息

只需在 QQ 群中发送消息（无需命令前缀或 @）。机器人将：
1. 将消息转发到 Home Assistant 的对话代理
2. 处理并执行设备控制命令
3. 返回执行结果

**示例：**
- 用户："打开客厅的灯"
- 机器人："客厅的灯已打开"

**语音消息：**
- 在群中发送语音消息
- 机器人自动转录并处理（需要配置语音识别模块）
- 返回响应

> **注意**：如果语音识别失败，机器人将静默跳过该消息以避免刷屏。

### 直接命令

机器人支持直接命令，无需 LLM 处理即可快速控制设备：

#### 设备控制命令

- `/turnon <entity_id> [<entity_id2> ...]` - 打开设备
  - 支持实体 ID（如 `light.living_room`）、友好名称或别名
  - 可同时控制多个设备
  - 示例：`/turnon 客厅灯` 或 `/turnon light.living_room light.bedroom`
  - 支持带空格的引号名称：`/turnon "Apple TV"`

- `/turnoff <entity_id> [<entity_id2> ...]` - 关闭设备
  - 与 `/turnon` 相同，但用于关闭设备

- `/toggle <entity_id> [<entity_id2> ...]` - 切换设备状态
  - 切换指定设备的状态

- `/script <script_id>` - 执行 Home Assistant 脚本
  - 通过脚本 ID 或实体 ID 执行 Home Assistant 脚本
  - 示例：`/script my_script` 或 `/script script.my_script`

- `/climate <entity_id> [模式] [温度]` - 控制空调设备
  - 设置模式：`cool`/`heat`/`fan_only`/`off` 或 制冷/制热/通风/关闭
  - 设置温度：直接指定数字或使用 `temp <数字>`
  - 示例：
    - `/climate 客厅空调 制冷 26` - 设置为制冷模式，温度 26°C
    - `/climate living_room_ac cool 26` - 设置为制冷模式，温度 26°C（英文）
    - `/climate 客厅空调 temp 25` - 仅设置温度为 25°C
    - `/climate 客厅空调 关闭` - 关闭空调

#### 信息查询命令

- `/info` - 获取 Home Assistant 环境信息
  - 显示开启的灯光、空调设备、环境温度（按区域分组）、湿度、空气质量、日耗电量、天气和其他重要状态

- `/light` - 列出所有灯光设备
  - 按区域分组设备
  - 显示设备名称和状态摘要

- `/switch` - 列出所有开关设备
  - 与 `/light` 相同，但用于开关设备

- `/search <关键词>` - 模糊搜索实体
  - 通过实体 ID、友好名称或别名搜索实体（不区分大小写，支持部分匹配）
  - 返回匹配的实体及其实体 ID 和友好名称
  - 示例：`/search 灯` 或 `/search light`

- `/help` - 显示所有支持的命令和描述

#### 命令特性

- **实体查找**：命令支持三种方式识别设备：
  1. 实体 ID：`light.living_room`
  2. 友好名称：`客厅灯`
  3. 别名：Home Assistant 中配置的任何别名

- **多设备控制**：在一个命令中通过空格分隔控制多个设备

- **引号名称**：使用引号包裹带空格的实体名称：`/turnon "Living Room Light"`

- **权限控制**：如果设置了 `ALLOWED_SENDERS`，只有指定的 QQ 用户可以使用控制命令。

- **重复别名警告**：如果多个实体共享相同的别名，机器人会警告你，但仍会控制第一个匹配项

---

## 模块 2：Webhook API

机器人提供 Webhook 接口，供 Home Assistant 主动向 QQ 群发送通知。你可以自定义消息内容，并发送多模态内容（文本 + 视频/文件）。

### 配置

1. **设置 Webhook 端口**（可选，默认：8080）：
   ```env
   WEBHOOK_PORT=8080
   ```

2. **设置 Webhook 令牌**（可选，用于安全）：
   ```env
   WEBHOOK_TOKEN=你的webhook令牌
   ```

3. **访问 Webhook**：Webhook 服务器运行在 `http://homeassistant-qq:8080`（或你配置的端口）

### 文本通知

向 QQ 群发送简单的文本消息。

**接口**：`POST http://homeassistant-qq:8080/webhook/notify`

**请求体**：
```json
{
  "group_id": "123456789",
  "message": "你的通知消息",
  "token": "可选的webhook令牌"
}
```

**参数**：
- `group_id`（必需）：QQ 群号
- `message`（必需）：消息文本
- `token`（可选）：认证令牌（如果设置了 `WEBHOOK_TOKEN`）

**响应**：
```json
{
  "status": "ok",
  "message": "通知已发送"
}
```

### 多模态通知

发送带视频流或文件的文本消息。支持 HLS/m3u8 视频流（通过 ffmpeg 下载）。

**接口**：`POST http://homeassistant-qq:8080/webhook/multimodal`

**请求体**：
```json
{
  "group_id": "123456789",
  "message": "可选的文本消息",
  "url": "http://example.com/video_stream.m3u8",
  "token": "可选的webhook令牌",
  "duration": 60
}
```

**参数**：
- `group_id`（必需）：QQ 群号
- `message`（可选）：消息文本
- `url`（可选）：视频流 URL（支持 HLS/m3u8，通过 ffmpeg 下载）
- `token`（可选）：认证令牌
- `duration`（可选）：视频录制时长（秒，默认：60）

> **注意**：`message` 和 `url` 至少需要提供一个。

**响应**：
```json
{
  "status": "ok",
  "message": "多模态通知已发送",
  "file_path": "/tmp/video_xxx.mp4"
}
```

### Home Assistant 集成

#### 配置 REST 命令

在 `configuration.yaml` 中添加：

```yaml
rest_command:
  homeassistant_qq:
    url: "http://homeassistant-qq:8080/webhook/notify"
    method: POST
    content_type: "application/json"
    payload: |
      {
        "group_id": "123456789",
        "message": "{{ message }}",
        "token": "{{ token | default('') }}"
      }
  
  homeassistant_qq_multimodal:
    url: "http://homeassistant-qq:8080/webhook/multimodal"
    method: POST
    content_type: "application/json"
    payload: |
      {
        "group_id": "123456789",
        "message": "{{ message }}",
        "url": "{{ video_url }}",
        "token": "{{ token | default('') }}",
        "duration": {{ duration | default(60) }}
      }
```

#### 自动化示例

**简单文本通知：**
```yaml
automation:
  - alias: "洗衣机完成通知"
    trigger:
      - platform: state
        entity_id: sensor.washing_machine_status
        to: "completed"
    action:
      - service: rest_command.homeassistant_qq
        data:
          message: "🧺 洗衣机已完成！"
```

**带视频的多模态通知：**
```yaml
automation:
  - alias: "门口有人移动-发送QQ通知"
    trigger:
      - trigger: state
        entity_id:
          - camera.front_door
        attribute: motion_video_time
        for:
          hours: 0
          minutes: 0
          seconds: 20
    action:
      - service: rest_command.homeassistant_qq_multimodal
        data:
          message: "⚠️ 侦测到门口有人"
          url: "{{ state_attr('camera.front_door', 'stream_address') }}"
          duration: 30
```

**使用模板的自定义通知：**
```yaml
automation:
  - alias: "温度警报"
    trigger:
      - platform: numeric_state
        entity_id: sensor.temperature
        above: 30
    action:
      - service: rest_command.homeassistant_qq
        data:
          message: >
            🌡️ 温度警报！
            当前温度：{{ states('sensor.temperature') }}°C
            时间：{{ now().strftime('%Y-%m-%d %H:%M') }}
```

### 安全

如果设置了 `WEBHOOK_TOKEN`，请在 Webhook 请求的 `token` 字段中包含相同的令牌，以防止未授权访问。如果令牌不匹配，机器人将返回 `401 Unauthorized`。

---

## 模块 3：语音识别（可选）

机器人可以使用腾讯云 ASR API 自动转录音频消息。此模块为**可选** - 如果未配置，机器人将仅处理文本消息。

### 配置

1. **获取腾讯云凭证**：
   - 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
   - 进入 **访问管理** → **API 密钥管理**
   - 创建新 API 密钥并复制 `SecretId` 和 `SecretKey`

2. **启用 ASR 服务**：
   - 在腾讯云控制台中启用 **语音识别（ASR）** 服务

3. **配置环境变量**：
   ```env
   TENCENT_SECRET_ID=你的腾讯云密钥ID
   TENCENT_SECRET_KEY=你的腾讯云密钥
   TENCENT_ASR_ENGINE=16k_zh  # 可选，默认：16k_zh
   TENCENT_ASR_REGION=         # 可选，留空使用默认
   ```

### 支持的引擎

- `16k_zh`：16kHz 中文识别（默认）
- `16k_en`：16kHz 英文识别
- `16k_zh_video`：16kHz 中文视频识别
- 腾讯云 ASR 支持的其他引擎

### 工作原理

1. 用户在 QQ 群中发送语音消息
2. 机器人从 NapCat 下载音频文件
3. 机器人将音频转换为 MP3 格式
4. 机器人将音频发送到腾讯云 ASR API
5. 机器人接收转录的文本
6. 机器人将文本作为自然语言消息处理

### 使用方法

只需在 QQ 群中发送语音消息。机器人将：
- 自动转录音频消息
- 将转录的文本作为自然语言命令处理
- 返回响应

**示例：**
- 用户：[发送语音消息说"打开客厅的灯"]
- 机器人："客厅的灯已打开"

### 错误处理

- 如果未配置 ASR 凭证，语音消息将被静默忽略
- 如果 ASR 失败，机器人将记录警告并跳过该消息以避免刷屏
- 仅支持 MP3 格式（从 QQ 语音格式自动转换）

### 费用说明

腾讯云 ASR 是付费服务。查看 [腾讯云定价](https://cloud.tencent.com/product/asr/pricing) 了解详情。机器人使用句子识别 API，按请求计费。

---

## 部署

### Docker Compose

```bash
docker-compose up -d
```

### 手动部署

```bash
# 安装依赖
poetry install

# 运行机器人
poetry run python src/maid/main.py
```

机器人包含两个服务：
- **WebSocket 客户端**：连接到 NapCat 并处理 QQ 消息
- **Webhook 服务器**：FastAPI 服务器，用于接收来自 Home Assistant 的 webhook 请求

两个服务在同一进程中运行。

---

## 开发

### 要求

- Python 3.10+
- Poetry
- Docker & Docker Compose（用于容器化部署）

### 设置

```bash
# 安装依赖
poetry install

# 本地运行
poetry run python src/maid/main.py

# 或使用 Docker
docker-compose up -d
```

### 项目结构

```
src/maid/
├── bot/              # NapCat 的 WebSocket 客户端
├── clients/          # API 客户端（Home Assistant、腾讯 ASR、NapCat）
├── handlers/         # 消息处理器（对话、命令）
├── models/           # 数据模型
├── services/         # 业务逻辑（发送器等）
├── utils/            # 工具（日志、国际化、实体缓存）
└── webhook/          # Webhook API 服务器
```

---

## 许可证

本项目采用 GNU Affero 通用公共许可证 v3.0 (AGPL-3.0) 许可。

详情请参阅 [LICENSE](LICENSE) 文件。

### 附加条款

- **商业使用**：未经作者明确许可，禁止商业使用
- **署名**：所有重新分发和修改必须包含原作者署名
