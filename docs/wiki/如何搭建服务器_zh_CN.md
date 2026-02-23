# 如何搭建 MorseLink 服务器（中文版）

> 本文档用于指导你快速部署一个可用于 MorseLink 客户端连接的 MQTT 服务器。

## 1. 部署方式概览

MorseLink 客户端本质上通过 MQTT 协议进行在线收发，因此你需要准备：

- 一台云服务器（Linux 推荐 Ubuntu 22.04）
- 一个可访问的公网 IP 或域名
- MQTT Broker（推荐 EMQX）

---

## 2. 使用 Docker 安装 EMQX（推荐）

```bash
docker run -d \
  --name emqx \
  -p 1883:1883 \
  -p 8883:8883 \
  -p 18083:18083 \
  --restart unless-stopped \
  emqx/emqx:latest
```

端口说明：

- `1883`：MQTT 明文连接（mqtt）
- `8883`：MQTT TLS 连接（mqtts）
- `18083`：EMQX 控制台管理页面

---

## 3. 防火墙与安全组

请确保服务器放行以下端口：

- TCP `1883`（至少）
- TCP `8883`（建议，启用 TLS 时需要）
- TCP `18083`（仅管理员使用，可限制为白名单 IP）

---

## 4. 在客户端中配置服务器地址

MorseLink 客户端对应配置项：

- `server/scheme`：`mqtt` 或 `mqtts`
- `server/host`：你的服务器 IP 或域名
- `server/active_port`：1883 或 8883
- `server/customized_endpoints`：例如 `mqtt://example.com:1883`

示例：

- 明文连接：`mqtt://your-server-ip:1883`
- TLS 连接：`mqtts://your-domain:8883`

---

## 5. 建议的生产环境配置

- 优先使用 `mqtts`（TLS）
- 启用认证（用户名/密码）
- 定期更新 EMQX 版本
- 对管理端口 `18083` 做 IP 白名单
- 配置监控与日志备份

---

## 6. 快速排查

### 无法连接服务器

1. 检查端口是否开放（安全组/防火墙）
2. 检查 EMQX 容器是否运行：`docker ps`
3. 检查客户端地址是否填写正确（scheme、host、port）

### 能连接但无法通信

1. 确认频道/主题一致
2. 检查是否开启了认证且凭据错误
3. 查看 EMQX 控制台连接日志

---

## 7. 英文版文档

如果你需要英文版，请查看：

- [How to Deploy a MorseLink Server (English)](./How-to-Deploy-a-MorseLink-Server_en.md)
