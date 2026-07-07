# 安全策略

## 支持的版本

当前项目处于早期开发阶段，以下版本正在接受安全更新。

| 版本   | 支持状态              |
| ------ | --------------------- |
| 0.2.x  | :white_check_mark:    |
| 0.1.x  | :x:                   |

## 报告漏洞

如果您发现安全漏洞，请通过以下方式私下报告，**不要**公开提交 Issue。

- **邮箱**: [填写你的联系方式]
- **加密**: 如有 PGP/GPG 公钥，请在此附上。

### 处理流程

| 阶段     | 说明                                             |
| -------- | ------------------------------------------------ |
| 确认收到 | 48 小时内确认收到报告                             |
| 评估     | 7 天内完成漏洞严重性评估                          |
| 修复     | 根据严重程度，尽快发布修复版本                    |
| 披露     | 修复发布后协调公开披露                            |

### 漏洞评估标准

| 严重程度 | 说明                                               |
| -------- | -------------------------------------------------- |
| 严重     | 可导致远程代码执行或敏感数据泄露                    |
| 高危     | 可绕过安全机制或获取未授权数据                      |
| 中危     | 影响部分功能安全但不直接造成数据泄露                |
| 低危     | 配置问题或边缘场景                                  |

## 安全最佳实践

使用本项目时，请遵循以下安全建议：

1. **不要硬编码凭证** — API 密钥、账号密码等敏感信息请使用环境变量或配置文件管理，并确保配置文件已加入 `.gitignore`。
2. **Cookie 安全** — Cookie 文件包含登录态信息，请妥善保管，切勿分享给他人。本项目 `cookies/` 目录已加入 `.gitignore`。
3. **遵守目标网站的规则** — 请遵守目标网站的 `robots.txt` 和使用条款，合理设置请求频率，避免对目标服务造成负担。
4. **数据存储安全** — 采集的数据可能包含敏感信息，请确保导出文件存储在安全位置。
5. **依赖安全** — 定期检查并更新项目依赖，防止使用存在已知漏洞的第三方库。
6. **网络安全** — 在可信网络环境中运行本项目，避免在公共 Wi-Fi 等不安全网络下传输敏感数据。

---

# Security Policy

## Supported Versions

The project is in early development. The following versions are currently receiving security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately. **Do NOT** open a public Issue.

- **Email**: [Fill in your contact]
- **Encryption**: Attach your PGP/GPG public key if available.

### Handling Process

| Stage           | Description                                                          |
| --------------- | -------------------------------------------------------------------- |
| Acknowledgement | We will acknowledge receipt within 48 hours.                         |
| Assessment      | Vulnerability severity assessment completed within 7 days.           |
| Resolution      | Fix released as soon as possible depending on severity.              |
| Disclosure      | Coordinated public disclosure after the fix is released.             |

### Vulnerability Assessment

| Severity | Description                                                |
| -------- | ---------------------------------------------------------- |
| Critical | Remote code execution or sensitive data exposure.          |
| High     | Security mechanism bypass or unauthorized data access.     |
| Medium   | Partial security impact without direct data exposure.      |
| Low      | Configuration issues or edge cases.                        |

## Security Best Practices

When using this project, please follow these security guidelines:

1. **Do not hardcode credentials** — Use environment variables or config files for API keys and passwords, and ensure config files are in `.gitignore`.
2. **Cookie security** — Cookie files contain session information, keep them private. The `cookies/` directory is in `.gitignore`.
3. **Respect target websites** — Respect the target website's `robots.txt` and terms of service. Configure reasonable request intervals to avoid overloading target services.
4. **Data storage security** — Collected data may contain sensitive information, ensure export files are stored securely.
5. **Dependency security** — Regularly check and update project dependencies to avoid using libraries with known vulnerabilities.
6. **Network security** — Run this project in a trusted network environment, avoid transmitting sensitive data over insecure networks like public Wi-Fi.
