"""
模块名称：自定义异常层次结构

功能说明：
    - 定义应用所有自定义异常，按模块分层继承
    - 爬虫引擎异常：NetworkError、ParseError、CookieExpiredError 等
    - 导出/配置异常：ExportError、ConfigError

设计原则：
    - 所有异常继承 TourCrawlerError，上层只需捕获一个基类
    - 异常分类细致，便于不同层级采取不同处理策略
"""


class TourCrawlerError(Exception):
    """
    应用基础异常，所有自定义异常继承此类。

    捕获此异常可覆盖所有应用定义的错误场景。
    """
    pass


# ==================== 爬取引擎异常 ====================

class CrawlError(TourCrawlerError):
    """爬取过程异常基类"""
    pass


class NetworkError(CrawlError):
    """
    网络请求错误。

    触发条件：连接超时、DNS 解析失败、SSL 握手失败等。
    处理策略：自动重试，按指数退避（1s → 3s → 9s）。
    """
    pass


class ParseError(CrawlError):
    """
    页面/JSON 解析错误。

    触发条件：网站结构变化、字段缺失、HTML 格式错误等。
    处理策略：记录警告后跳过当前页，继续下一页。
    """
    pass


class CookieExpiredError(CrawlError):
    """
    Cookie 过期或失效。

    触发条件：服务器返回 302 重定向到登录页。
    处理策略：暂停任务，弹窗通知用户重新获取 Cookie。
    """
    pass


class CaptchaDetectedError(CrawlError):
    """
    检测到验证码，需要人工介入。

    触发条件：响应中出现验证码关键词或验证码图片。
    处理策略：暂停任务，弹窗提示用户手动完成验证。
    """
    pass


class RateLimitError(CrawlError):
    """
    请求频率过高被限制。

    触发条件：HTTP 429 状态码。
    处理策略：自动增大请求间隔至 30s，冷却后恢复。
    """
    pass


# ==================== 导出异常 ====================

class ExportError(TourCrawlerError):
    """数据导出过程异常"""
    pass


class ExportPermissionError(ExportError):
    """导出文件写入权限不足"""
    pass


class ExportFormatError(ExportError):
    """不支持的导出格式"""
    pass


# ==================== 配置异常 ====================

class ConfigError(TourCrawlerError):
    """配置错误（无效设置、缺失必填项等）"""
    pass


# ==================== Cookie 异常 ====================

class CookieError(TourCrawlerError):
    """Cookie 操作异常"""
    pass


class CookieExtractError(CookieError):
    """从浏览器提取 Cookie 失败"""
    pass
