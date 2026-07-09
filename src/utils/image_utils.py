"""
模块名称：图片 URL 工具

功能说明：
    - 从 HTML 元素中提取原图 URL（优先取 data 属性、父链接、再回退 src）
    - 清除 URL 中的缩略图尺寸/压缩参数，还原为原图地址
"""

import re

# 缩略图/压缩参数正则（按顺序清理）
_THUMB_PATTERNS = [
    # 携程：_w_200_h_200 / _w_800_h_600 等尺寸后缀
    re.compile(r"_\w_\d+_\w_\d+(?=\.\w+($|\?))"),
    # 携程/通用：@XXXw_XXXh_1e_1c 等
    re.compile(r"@\d+w_\d+h(?:_[a-z0-9]+)*(?=\.\w+($|\?))"),
    # 飞猪/阿里OSS：?x-oss-process=image/... 处理参数
    re.compile(r"\?x-oss-process=image/[^&]*(&|$)"),
    # 通用：?imageView2/... / ?imageMogr2/...
    re.compile(r"\?image(View|Mogr)\d+/[^&]*(&|$)"),
    # 质量参数：_Q70 / _Q90 等（阿里系常见）
    re.compile(r"_Q\d+(?=\.\w+($|\?))"),
    # 尺寸：_200x200 / _800x800 等（第三方平台常见）
    re.compile(r"_\d+x\d+(?=\.\w+($|\?))"),
]


def clean_image_url(url: str) -> str:
    """
    清除图片 URL 中的缩略图/压缩参数，返回原图地址。

    Args:
        url: 原始图片 URL

    Returns:
        清理后的原图 URL
    """
    if not url or not url.startswith("http"):
        return url

    for pattern in _THUMB_PATTERNS:
        url = pattern.sub("", url)

    # 清理残留的 ?& 符号
    url = re.sub(r"(\?|&)$", "", url)

    return url


def extract_img_url_from_tag(img_tag) -> str:
    """
    从 BeautifulSoup img 标签中提取原图 URL。

    优先级：data-src > data-original > data-big > 父级a标签href > src
    提取后自动清理缩略图参数。

    Args:
        img_tag: BeautifulSoup Tag 对象（<img> 元素）

    Returns:
        原图 URL，获取失败返回空字符串
    """
    # 优先取懒加载属性（通常是原图）
    for attr in ("data-src", "data-original", "data-big"):
        url = (img_tag.get(attr) or "").strip()
        if url and url.startswith("http"):
            return clean_image_url(url)

    # 检查父级 <a> 标签的 href（通常是原图链接）
    parent = img_tag.parent
    if parent and getattr(parent, "name", "") == "a":
        href = (parent.get("href") or "").strip()
        if href and href.startswith("http"):
            return clean_image_url(href)

    # 回退到 src
    src = (img_tag.get("src") or "").strip()
    if src and src.startswith("http"):
        return clean_image_url(src)

    return src


def extract_img_url_from_selenium(img_element) -> str:
    """
    从 Selenium WebElement 中提取原图 URL。

    优先级：data-src > data-original > data-big > src
    提取后自动清理缩略图参数。

    Args:
        img_element: Selenium WebElement 对象（<img> 元素）

    Returns:
        原图 URL，获取失败返回空字符串
    """
    for attr in ("data-src", "data-original", "data-big"):
        try:
            url = (img_element.get_attribute(attr) or "").strip()
            if url and url.startswith("http"):
                return clean_image_url(url)
        except Exception:
            pass

    # 回退到 src
    try:
        src = (img_element.get_attribute("src") or "").strip()
        if src and src.startswith("http"):
            return clean_image_url(src)
        return src or ""
    except Exception:
        return ""
