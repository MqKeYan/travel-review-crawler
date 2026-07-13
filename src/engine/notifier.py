"""
模块名称：通知推送模块

功能说明：
    - 任务完成/出错时的多通道通知
    - 支持三种通知方式：系统托盘弹窗、声音提示、PushPlus 微信推送
    - 可针对不同事件（完成/出错）配置不同的通知方式

依赖模块：
    - requests (第三方)
    - PySide6.QtWidgets: QSystemTrayIcon
    - PySide6.QtMultimedia: QSoundEffect
    - logging (标准库)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from src.utils.paths import get_data_dir

logger = logging.getLogger("tour-crawler.notifier")


# PushPlus API 端点
PUSHPLUS_API_URL = "http://www.pushplus.plus/send"


@dataclass
class NotificationSettings:
    """
    通知系统设置。

    Attributes:
        desktop_popup: 是否启用桌面弹窗
        sound_enabled: 是否启用声音提示
        sound_file: 提示音文件路径，"default" 使用内置音
        pushplus_token: PushPlus 推送 token
        pushplus_channel: 推送渠道（wechat / sms / mail）
    """
    desktop_popup: bool = True
    sound_enabled: bool = True
    sound_file: str = "default"
    pushplus_token: str = ""
    pushplus_channel: str = "wechat"
    # 验证码通知独立设置
    captcha_popup: bool = True
    captcha_sound: bool = False
    captcha_pushplus_token: str = ""


class Notifier:
    """
    通知器，管理所有通知通道。

    Usage:
        notifier = Notifier(settings)
        notifier.notify_complete("携程-黄山", 200)
        notifier.notify_error("携程-故宫", "网络连接失败")
    """

    def __init__(self, settings: NotificationSettings | None = None):
        """
        初始化通知器。

        Args:
            settings: 通知设置，None 则使用默认设置
        """
        self.settings = settings or NotificationSettings()
        self._tray_icon = None  # QSystemTrayIcon 实例，由 UI 层设置
        self._sound_effect = None  # QSoundEffect 实例，由 UI 层设置

    def set_tray_icon(self, tray_icon) -> None:
        """
        设置系统托盘图标（由 UI 层注入）。

        Args:
            tray_icon: QSystemTrayIcon 实例
        """
        self._tray_icon = tray_icon

    def set_sound_effect(self, sound_effect) -> None:
        """
        设置声音播放器（由 UI 层注入）。

        Args:
            sound_effect: QSoundEffect 实例
        """
        self._sound_effect = sound_effect

    def notify_complete(self, task_name: str, count: int, elapsed: str = "") -> None:
        """
        发送任务完成通知。

        Args:
            task_name: 任务名称
            count: 爬取的评论条数
            elapsed: 运行时长描述
        """
        title = "爬取任务完成"
        message = f"共 {count} 条"
        if elapsed:
            message += f"，耗时 {elapsed}"

        self._notify_all(title, message, task_name, event="complete")

    def notify_error(self, task_name: str, error_info: str) -> None:
        """
        发送任务出错通知。

        Args:
            task_name: 任务名称
            error_info: 错误描述
        """
        title = "爬取任务出错"
        message = f"「{task_name}」运行出错: {error_info}"

        self._notify_all(title, message, task_name, event="error")

    def notify_captcha(self, task_name: str = "") -> None:
        """
        发送验证码通知，提醒用户手动完成人机验证。

        通知方式与任务完成/出错一致：弹窗 + 声音 + PushPlus。

        Args:
            task_name: 任务名称
        """
        title = "需要人机验证"
        message = f"「{task_name}」遇到验证码，请打开浏览器窗口手动完成验证。\n完成后爬虫将自动继续。"
        if not task_name:
            message = "遇到验证码，请打开浏览器窗口手动完成验证。\n完成后爬虫将自动继续。"

        self._notify_all(title, message, task_name, event="captcha")

    def _notify_all(self, title: str, message: str, task_name: str = "", event: str = "complete") -> None:
        """
        根据设置发送所有已启用的通知通道。

        Args:
            title: 通知标题
            message: 通知内容
            task_name: 任务名称
            event: 事件类型（"complete" 或 "error"）
        """
        # 验证码事件使用独立的通知设置
        if event == "captcha":
            if self.settings.captcha_popup:
                self._send_desktop_popup(title, message)
            if self.settings.captcha_sound:
                self._play_sound()
            if self.settings.captcha_pushplus_token:
                # 临时替换 token 以使用验证码专用推送
                saved_token = self.settings.pushplus_token
                self.settings.pushplus_token = self.settings.captcha_pushplus_token
                self._send_pushplus(title, message)
                self.settings.pushplus_token = saved_token
            return

        if self.settings.desktop_popup:
            self._send_desktop_popup(title, message)

        # 音效（由任务通知设置控制开关）
        if self.settings.sound_enabled:
            self._play_sound()

        if self.settings.pushplus_token:
            self._send_pushplus(title, message)

    def _send_desktop_popup(self, title: str, message: str) -> None:
        """
        发送系统托盘弹窗通知。
        需要 QApplication 已创建并已设置托盘图标。
        """
        if self._tray_icon is not None:
            try:
                self._tray_icon.showMessage(
                    title,
                    message,
                    self._tray_icon.MessageIcon.Information,
                    5000,
                )
            except Exception as e:
                logger.warning(f"桌面弹窗失败: {e}")

    def _play_sound(self) -> None:
        """播放提示音（有自定义音效则播放，否则使用系统提示音）"""
        if self._sound_effect is not None:
            try:
                self._sound_effect.play()
                return
            except Exception:
                pass
        # 回退：系统提示音
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.beep()
        except Exception:
            import sys
            sys.stderr.write("\a")

    def _send_pushplus(self, title: str, message: str) -> None:
        """
        通过 PushPlus 推送通知到微信。

        调用 PushPlus 的 HTTP API 发送消息。
        使用 settings.pushplus_token 作为身份标识。
        """
        if not self.settings.pushplus_token:
            return

        try:
            response = requests.post(
                PUSHPLUS_API_URL,
                json={
                    "token": self.settings.pushplus_token,
                    "title": title,
                    "content": message,
                    "channel": self.settings.pushplus_channel,
                },
                timeout=10,
            )
            result = response.json()
            if result.get("code") != 200:
                logger.warning(f"PushPlus 推送失败: {result.get('msg', '未知错误')}")
        except requests.RequestException as e:
            logger.warning(f"PushPlus 网络请求失败: {e}")
