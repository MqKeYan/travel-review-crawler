# Security Policy / 安全策略

## Supported Versions / 支持的版本

当前项目处于早期开发阶段，以下版本正在接受安全更新。

The project is in early development. The following versions are currently receiving security updates.

| Version / 版本 | Supported / 支持状态  |
| -------------- | --------------------- |
| 0.2.x          | :white_check_mark:    |
| 0.1.x          | :x:                   |

## Reporting a Vulnerability / 报告漏洞

如果您发现安全漏洞，请通过以下方式私下报告，**不要**公开提交 Issue。

If you discover a security vulnerability, please report it privately. **Do NOT** open a public Issue.

- **邮箱 / Email**: [填写你的联系方式]
- **加密 / Encryption**: 如有 PGP/GPG 公钥，请在此附上 / Attach your public key if available.

### 处理流程 / Handling Process

| 阶段 / Stage | 说明 / Description |
| ------------ | ------------------ |
| 确认收到 / Acknowledgement | 48 小时内确认收到报告 / We will acknowledge receipt within 48 hours. |
| 评估 / Assessment | 7 天内完成漏洞严重性评估 / Vulnerability severity assessment completed within 7 days. |
| 修复 / Resolution | 根据严重程度，尽快发布修复版本 / Fix released as soon as possible depending on severity. |
| 披露 / Disclosure | 修复发布后协调公开披露 / Coordinated public disclosure after the fix is released. |

### 漏洞评估标准 / Vulnerability Assessment

| 严重程度 / Severity | 说明 / Description |
| ------------------- | ------------------ |
| 严重 / Critical     | 可导致远程代码执行或敏感数据泄露 / Remote code execution or sensitive data exposure. |
| 高危 / High         | 可绕过安全机制或获取未授权数据 / Security mechanism bypass or unauthorized data access. |
| 中危 / Medium       | 影响部分功能安全但不直接造成数据泄露 / Partial security impact without direct data exposure. |
| 低危 / Low          | 配置问题或边缘场景 / Configuration issues or edge cases. |

## Security Best Practices / 安全最佳实践

使用本项目时,请遵循以下安全建议：

When using this project, please follow these security guidelines:

1. **不要硬编码凭证 / Do not hardcode credentials** — API 密钥、账号密码等敏感信息请使用环境变量或配置文件管理，并确保配置文件已加入 `.gitignore`。Use environment variables or config files for API keys and passwords, and ensure config files are in `.gitignore`.

2. **Cookie 安全 / Cookie security** — Cookie 文件包含登录态信息，请妥善保管，切勿分享给他人。本项目 `cookies/` 目录已加入 `.gitignore`。Cookie files contain session information, keep them private. The `cookies/` directory is in `.gitignore`.

3. **遵守目标网站的规则 / Respect target websites** — 请遵守目标网站的 `robots.txt` 和使用条款，合理设置请求频率，避免对目标服务造成负担。Respect the target website's `robots.txt` and terms of service. Configure reasonable request intervals to avoid overloading target services.

4. **数据存储安全 / Data storage security** — 采集的数据可能包含敏感信息，请确保导出文件存储在安全位置。Collected data may contain sensitive information, ensure export files are stored securely.

5. **依赖安全 / Dependency security** — 定期检查并更新项目依赖，防止使用存在已知漏洞的第三方库。Regularly check and update project dependencies to avoid using libraries with known vulnerabilities.

6. **网络安全 / Network security** — 在可信网络环境中运行本项目，避免在公共 Wi-Fi 等不安全网络下传输敏感数据。Run this project in a trusted network environment, avoid transmitting sensitive data over insecure networks like public Wi-Fi.
