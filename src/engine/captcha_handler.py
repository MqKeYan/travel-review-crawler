"""
模块名称：验证码检测与通知模块

功能说明：
    - 检测页面中的滑块/人机验证码（阿里系/通用）
    - 检测到验证码时通过 Notifier 通知用户手动处理
    - 轮询等待用户完成验证码后自动继续
    - 不执行自动求解，由用户手动在浏览器中完成

适用平台：
    - 飞猪 / 淘宝 / 天猫（阿里系滑块验证码）
    - 其他使用滑块验证码的网站
"""

import time
import logging

logger = logging.getLogger("tour-crawler.captcha_handler")

# 滑块验证码元素选择器
_SLIDER_SELECTORS = [
    "#nc_1_n1z",
    ".nc_iconfont.btn_slide",
    ".btn_slide",
    "#nocaptcha",
    ".nc_wrapper",
    ".slidetounlock",
    ".slider-captcha",
    "[class*='slide']",
]

# 验证码检测轮询间隔（秒）
_POLL_INTERVAL = 3
# 等待用户手动处理的最大时间（秒），超时后放弃本次任务
_MAX_WAIT_SECONDS = 300


def detect_captcha(driver) -> bool:
    """
    检测当前页面是否存在验证码。

    检测维度：
    1. 页面标题含关键词
    2. DOM 中存在滑块元素
    3. 页面文本含验证码提示

    Args:
        driver: Selenium WebDriver 实例

    Returns:
        True 表示检测到验证码
    """
    try:
        # 方式1：标题检测
        title = driver.title.lower()
        captcha_keywords = ["验证码", "captcha", "verify", "安全验证", "人机验证",
                           "slider", "请按住滑块", "拖动滑块"]
        for kw in captcha_keywords:
            if kw.lower() in title:
                logger.info(f"验证码检测(标题): 匹配关键词 '{kw}'")
                return True

        # 方式2：DOM 元素检测
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException

        for selector in _SLIDER_SELECTORS:
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                logger.info(f"验证码检测(DOM): 找到元素 {selector}")
                return True
            except NoSuchElementException:
                pass

        # 方式3：页面文本检测
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            text_keywords = ["请按住滑块", "拖动滑块", "向右滑动", "slide to",
                           "请完成安全验证", "拖动下方滑块完成拼图"]
            for kw in text_keywords:
                if kw.lower() in body_text:
                    logger.info(f"验证码检测(文本): 匹配 '{kw}'")
                    return True
        except Exception:
            pass

    except Exception as e:
        logger.debug(f"验证码检测异常(忽略): {e}")

    return False


def wait_for_captcha_solved(
    driver,
    notifier=None,
    task_name: str = "",
    timeout: int = _MAX_WAIT_SECONDS,
    progress_callback=None,
) -> bool:
    """
    检测到验证码后，通知用户并轮询等待手动完成。

    流程：
    1. 通过 Notifier 发送弹窗+声音+PushPlus 通知
    2. 每 _POLL_INTERVAL 秒检测一次验证码是否消失
    3. 验证码消失后返回 True
    4. 超时返回 False

    Args:
        driver: Selenium WebDriver 实例
        notifier: Notifier 实例（用于发送通知）
        task_name: 任务名称
        timeout: 最大等待时间（秒）
        progress_callback: 进度回调

    Returns:
        True 表示验证码已通过，False 表示超时
    """
    _prefix = f"任务 [{task_name}] " if task_name else ""
    logger.info(f"{_prefix}检测到验证码，通知用户手动处理...")

    # 发送通知
    if notifier:
        try:
            notifier.notify_captcha(task_name)
        except Exception as e:
            logger.warning(f"{_prefix}验证码通知发送失败: {e}")

    if progress_callback:
        progress_callback(
            page_num=0, count=0, total=0,
            message="检测到验证码，请打开浏览器窗口手动完成验证..."
        )

    # 轮询等待用户完成验证码
    waited = 0
    while waited < timeout:
        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL

        try:
            if not detect_captcha(driver):
                logger.info(f"{_prefix}验证码已通过（等待 {waited} 秒），继续爬取...")
                if progress_callback:
                    progress_callback(
                        page_num=0, count=0, total=0,
                        message="验证码已通过，继续爬取..."
                    )
                time.sleep(1)  # 等待页面恢复正常
                return True
        except Exception:
            # driver 异常时继续等待
            pass

        # 每分钟更新一次进度提示
        if waited % 60 == 0 and progress_callback:
            remaining = timeout - waited
            progress_callback(
                page_num=0, count=0, total=0,
                message=f"等待手动验证中... 已等待 {waited} 秒（剩余 {remaining} 秒）"
            )

    logger.warning(f"{_prefix}等待验证码超时（{timeout} 秒）")
    return False
