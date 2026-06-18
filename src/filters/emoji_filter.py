"""
模块名称：Emoji 过滤器

功能说明：
    - 移除评论内容中的 emoji 字符
    - 使用 Unicode 正则匹配 emoji 范围
    - 保留非 emoji 的其他 Unicode 字符（如中文、英文、数字）

参考范围（Unicode Emoji 标准）：
    - \U0001F600-\U0001F64F: 表情符号（Emoticons）
    - \U0001F300-\U0001F5FF: 杂项符号和图形（Misc Symbols and Pictographs）
    - \U0001F680-\U0001F6FF: 交通和地图符号（Transport and Map Symbols）
    - \U0001F1E0-\U0001F1FF: 国旗（Regional Indicator Symbols）
    - \U00002600-\U000027BF: 杂项符号（Miscellaneous Symbols）
    - \U00002702-\U000027B0: 印刷符号（Dingbats）
    - \U000024C2-\U000024FF: 带圈字母数字（Enclosed Alphanumerics）
    - \U0001F900-\U0001F9FF: 补充符号和图形（Supplemental Symbols）
    - \U0001FA00-\U0001FA6F: 国际象棋符号（Chess Symbols）
    - \U0001FA70-\U0001FAFF: 扩展图形（Symbols Extended-A）
    - \U00002B50-\U00002B55: 星星（星星/星号等）
    - \U00002934-\U00002935: 双向箭头
    - \U0000231A-\U0000231B: 时钟（表/沙漏）
    - \U000025AA-\U000025FE: 几何形状符号
    - \U00002640-\U00002642: 性别符号
    - \U00002693-\U000026FA: 杂项符号（锚/自行车等）
    - \U00002708-\U0000276F: 更多日常符号
    - \U0000200D: 零宽连接符（ZWJ）
    - \U0000FE0F: 异体字选择符-16（Emoji 样式）
"""

import re

from src.filters.base import BaseFilter, FilterResult


# Emoji Unicode 范围正则
# 覆盖主流 emoji 区域，不包括颜文字（如 (｡♥‿♥｡)）
# 注意：\U000024C2-\U0001F251 这个范围会匹配中文字符（跨越整个CJK区），必须拆分为正确的小范围
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons (表情符号)
    "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs (杂项符号和图形)
    "\U0001F680-\U0001F6FF"  # Transport and Map Symbols (交通和地图符号)
    "\U0001F1E0-\U0001F1FF"  # Flags - Regional Indicator Symbols (国旗)
    "\U00002600-\U000027BF"  # Misc symbols (杂项符号)
    "\U00002702-\U000027B0"  # Dingbats (印刷符号)
    "\U000024C2-\U000024FF"  # Enclosed Alphanumerics (带圈文字，仅此小范围)
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs (补充符号)
    "\U0001FA00-\U0001FA6F"  # Chess Symbols (国际象棋符号)
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A (扩展图形)
    "\U00002B50-\U00002B55"  # Stars (星星符号 ⭐⭑)
    "\U00002934-\U00002935"  # Arrow emoji (↴↵)
    "\U0000231A-\U0000231B"  # Watch, Hourglass (⌚⌛)
    "\U000025AA-\U000025FE"  # Geometric shapes (▪▫◼◻◼◾等)
    "\U00002640-\U00002642"  # Gender signs (♀♂⚀⚁)
    "\U00002693-\U000026FA"  # Various emoji (⚓⛓⛔⛩⛪⛰⛱⛲⛳⛴⛵⛷⛸⛹⛺)
    "\U00002708-\U0000276F"  # More everyday symbols (✈✉✊✋✌✍✏✒✔✖✝✡✩✪✫✬✭✮✯✰)
    "\U0000200D"              # Zero Width Joiner (零宽连接符)
    "\U0000FE0F"              # Variation Selector-16 (异体字选择符-16, emoji样式)
    "]+",
    flags=re.UNICODE,
)


class EmojiFilter(BaseFilter):
    """
    Emoji 字符过滤器。

    移除评论中的所有 emoji 字符。
    如果一条评论全是 emoji（移除后为空），
    由后续的 PureEmojiFilter 处理，本过滤器不负责判断。
    """

    name: str = "emoji"

    def process(self, review: dict) -> FilterResult:
        """
        移除评论内容中的 emoji 字符。

        Args:
            review: 评论字典，需包含 "content" 键

        Returns:
            处理后的结果：移除 emoji 后的内容
        """
        content = review.get("content", "")
        cleaned = EMOJI_PATTERN.sub("", content).strip()

        return FilterResult(
            passed=True,          # emoji 过滤器不拒绝评论，只清洗
            content=cleaned,
            reason="",
        )
