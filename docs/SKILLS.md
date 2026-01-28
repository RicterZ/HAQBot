# SKILLS: 通过 Webhook 向 QQ 群发送消息

让 AI 在需要主动通知时，通过 HAQBot 内置的 FastAPI Webhook 将文本或多媒体消息推送到指定 QQ 群。

## 快速要点
- 基础 URL：`http://<host>:<WEBHOOK_PORT>`（默认 8080，见环境变量 `WEBHOOK_PORT`）。
- 认证：如设置了 `WEBHOOK_TOKEN`，在请求体的 `token` 字段携带相同值；未设置则无需提供。
- 主要接口：
  - `POST /webhook/notify`：发送纯文本。
  - `POST /webhook/multimodal`：发送文本 + 图片/视频/文件（服务端自动下载 URL）。
- 必填规则：`group_id` 始终必填；`/webhook/notify` 需要 `message`；`/webhook/multimodal` 需要 `message` 或 `url`。
- 健康检查：`GET /health` 返回 `{"status":"ok"}` 即服务可用。

## 调用流程
1) **确认服务可用**  
   ```bash
   curl -s http://<host>:<port>/health
   # 期望 {"status":"ok"}
   ```
2) **发送纯文本消息**  
   ```bash
   curl -X POST http://<host>:<port>/webhook/notify \
     -H "Content-Type: application/json" \
     -d '{
       "group_id": "QQ群号",
       "message": "要发送的文本内容",
       "token": "可选：若设置了 WEBHOOK_TOKEN 则必填"
     }'
   ```
3) **发送多模态消息（文本 + 媒体/文件）**  
   ```bash
   curl -X POST http://<host>:<port>/webhook/multimodal \
     -H "Content-Type: application/json" \
     -d '{
       "group_id": "QQ群号",
       "title": "可选标题",
       "message": "可选文本",
       "url": "http(s)/rtsp/m3u8/文件直链；留空则只发文本",
       "duration": 60,
       "token": "可选：若设置了 WEBHOOK_TOKEN 则必填"
     }'
   ```
   - URL 类型自动识别：图片(`.jpg/.png/...`)、视频/流(`.mp4/.m3u8/rtsp...`)、其他文件将按附件发送。  
   - `duration` 仅对视频流/长视频下载时生效（秒）。

## Python 示例
```python
import requests

base = "http://<host>:<port>"
token = "与 WEBHOOK_TOKEN 相同的值或留空"

def send_text(group_id: str, message: str):
    r = requests.post(f"{base}/webhook/notify", json={
        "group_id": group_id,
        "message": message,
        "token": token or None,
    })
    r.raise_for_status()
    return r.json()

def send_multimodal(group_id: str, message: str = None, url: str = None, title: str = None):
    r = requests.post(f"{base}/webhook/multimodal", json={
        "group_id": group_id,
        "title": title,
        "message": message,
        "url": url,
        "duration": 60,
        "token": token or None,
    })
    r.raise_for_status()
    return r.json()
```

## 常见故障排查
- 401：检查 `token` 是否与 `WEBHOOK_TOKEN` 匹配。
- 400：缺少必填字段（`group_id` 或 `message/url`）。
- 500：可能是 URL 不可访问或 WebSocket 未连接 QQ；检查日志和网络连通性。
