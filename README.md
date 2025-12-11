homeassistant-qq
================
QQ 控制 Home Assistant 的助手

## 功能

通过 QQ 群聊接收消息，接入 Home Assistant 的对话代理（Ollama）来控制设备和服务。

## 工作原理

```
QQ 消息 → NapCat WebSocket → QQ Bot → HA Conversation API → Ollama 对话代理 → 设备控制
                ↓                                                      ↓
           返回结果 ← QQ 回复 ← HA 响应 ← 执行结果
```

1. 通过 WebSocket 连接到 NapCat（QQ 机器人框架）
2. 接收 QQ 群聊消息
3. 将消息转发到 Home Assistant 的 Conversation API
4. HA 的 Ollama 对话代理处理并执行设备控制
5. 将执行结果返回给 QQ 用户

## 配置

### 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
# NapCat WebSocket 连接地址
NAPCAT_API=ws://napcat:3001

# Home Assistant 配置
HA_URL=http://homeassistant:8123
HA_TOKEN=your_long_lived_access_token_here
HA_AGENT_ID=conversant.ollama_conversation

# QQ 账号（可选）
ACCOUNT=2167634556
```

### 获取 HA Token

1. 登录 Home Assistant
2. 点击个人资料 → 长期访问令牌
3. 创建新令牌并复制

### 配置对话代理

确保 Home Assistant 中已配置 `conversant.ollama_conversation` 对话代理。

## 使用方法

1. 在 QQ 群中发送消息（不需要命令前缀）
2. 机器人会将消息转发给 HA 的对话代理
3. 对话代理处理并执行相应的设备控制
4. 返回执行结果

### 示例

- 用户: "打开客厅的灯"
- 机器人: "已打开客厅的灯"

## 开发

### 安装依赖

```bash
poetry install
```

### 运行

```bash
poetry run python src/meteion/main.py
```

### Docker 运行

```bash
docker-compose up -d
```