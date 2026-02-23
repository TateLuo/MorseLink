# How to Deploy a MorseLink Server (English)

> This guide explains how to quickly deploy an MQTT server for MorseLink clients.

## 1. Deployment Overview

MorseLink relies on MQTT for real-time communication. You need:

- A cloud server (Linux, Ubuntu 22.04 recommended)
- A public IP or domain name
- An MQTT broker (EMQX recommended)

---

## 2. Install EMQX with Docker (Recommended)

```bash
docker run -d \
  --name emqx \
  -p 1883:1883 \
  -p 8883:8883 \
  -p 18083:18083 \
  --restart unless-stopped \
  emqx/emqx:latest
```

Port usage:

- `1883`: MQTT plaintext (`mqtt`)
- `8883`: MQTT over TLS (`mqtts`)
- `18083`: EMQX dashboard/admin console

---

## 3. Firewall & Security Group Rules

Open at least these TCP ports:

- `1883` (required)
- `8883` (recommended for TLS)
- `18083` (admin only; ideally restricted by IP allowlist)

---

## 4. Configure Server Endpoint in MorseLink

Relevant client-side settings:

- `server/scheme`: `mqtt` or `mqtts`
- `server/host`: your server IP or domain
- `server/active_port`: 1883 or 8883
- `server/customized_endpoints`: e.g. `mqtt://example.com:1883`

Examples:

- Plain MQTT: `mqtt://your-server-ip:1883`
- TLS MQTT: `mqtts://your-domain:8883`

---

## 5. Recommended Production Practices

- Prefer `mqtts` (TLS)
- Enable authentication (username/password)
- Keep EMQX up to date
- Restrict admin port `18083` by IP
- Set up monitoring and log backups

---

## 6. Quick Troubleshooting

### Cannot connect to server

1. Verify firewall/security group rules.
2. Ensure EMQX container is running: `docker ps`
3. Check endpoint fields in client (`scheme`, `host`, `port`).

### Connected but cannot communicate

1. Confirm channel/topic alignment.
2. Check credentials if authentication is enabled.
3. Inspect connection logs in EMQX dashboard.

---

## 7. Chinese Version

For the Chinese version, see:

- [如何搭建 MorseLink 服务器（中文版）](./如何搭建服务器_zh_CN.md)
