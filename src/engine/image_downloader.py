"""
模块名称：评论图片下载器

功能说明：
    - 将爬取的评论图片从远程 URL 下载到本地存储
    - 按任务/评论分目录组织：images/{task_name}/review_{idx:04d}/
    - 并发下载、重试机制、请求超时控制
    - 下载完成后将 image_urls 从链接替换为本地文件路径

目录结构：
    data/images/
    └── {task_name}/
        ├── review_0001/
        │   ├── img_0.jpg
        │   ├── img_1.jpg
        │   └── img_2.webp
        ├── review_0002/
        │   └── img_0.png
        └── ...

依赖：
    - requests (第三方)
    - threading, os, time, logging (标准库)
"""

import os
import time
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

from src.utils.paths import get_images_dir

logger = logging.getLogger("tour-crawler.image_downloader")

# 下载配置
MAX_WORKERS = 6                 # 并发下载线程数
REQUEST_TIMEOUT = 15            # 单张图片下载超时（秒）
MAX_RETRIES = 3                 # 最大重试次数
RETRY_DELAY = 1.0               # 重试间隔（秒）
MAX_IMAGE_SIZE_MB = 20          # 单张图片最大体积（MB），超出跳过


# ==================== 工具函数 ====================

def _extract_extension(url: str, content_type: str | None = None) -> str:
    """
    从 URL 或 Content-Type 推断文件扩展名。

    Args:
        url: 图片 URL
        content_type: HTTP 响应 Content-Type 头

    Returns:
        扩展名（不含点号），如 "jpg"
    """
    # 优先从 URL 路径提取
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    # 过滤掉查询参数（如 .jpg?width=200）
    if "?" in ext:
        ext = ext.split("?")[0]
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff"):
        return "jpeg" if ext == "jpg" else ext

    # 从 Content-Type 推断
    if content_type:
        ct = content_type.lower()
        type_map = {
            "image/jpeg": "jpeg",
            "image/jpg": "jpeg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/bmp": "bmp",
            "image/svg+xml": "svg",
            "image/tiff": "tiff",
        }
        for mime, ext_name in type_map.items():
            if mime in ct:
                return ext_name

    # 默认 jpeg
    return "jpeg"


def _sanitize_filename(name: str) -> str:
    """
    清理文件名中的非法字符。

    Args:
        name: 原始文件名

    Returns:
        清理后的安全文件名
    """
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "_")
    return name[:100]  # 限制长度


# ==================== 单张图片下载 ====================

def _download_single_image(url: str, save_path: Path, timeout: int = REQUEST_TIMEOUT) -> bool:
    """
    下载单张图片到指定路径。

    Args:
        url: 图片 URL
        save_path: 保存路径（含扩展名）
        timeout: 请求超时秒数

    Returns:
        True 表示下载成功
    """
    if not url or not url.startswith("http"):
        return False

    # 如果文件已存在且非空，跳过
    if save_path.exists() and save_path.stat().st_size > 0:
        logger.debug(f"图片已存在，跳过: {save_path.name}")
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": url,
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
            resp.raise_for_status()

            # 检查内容大小
            content_length = resp.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > MAX_IMAGE_SIZE_MB:
                    logger.warning(f"图片过大 ({size_mb:.1f}MB)，跳过: {url[:80]}")
                    return False

            # 确定扩展名
            content_type = resp.headers.get("Content-Type", "")
            ext = _extract_extension(url, content_type)
            final_path = save_path.with_suffix(f".{ext}")

            # 写入文件
            final_path.parent.mkdir(parents=True, exist_ok=True)
            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"图片下载成功: {final_path.name} ({final_path.stat().st_size} bytes)")
            return True

        except requests.Timeout:
            last_error = "timeout"
        except requests.ConnectionError:
            last_error = "connection"
        except requests.HTTPError as e:
            last_error = f"HTTP {e.response.status_code if e.response else '?'}"
            if e.response is not None and e.response.status_code in (404, 410, 403):
                # 这些状态码不会因重试而改变
                break
        except Exception as e:
            last_error = str(e)[:50]

        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAY * (attempt + 1)
            logger.debug(f"图片下载重试 ({attempt+1}/{MAX_RETRIES}), {delay}s后: {url[:80]}")
            time.sleep(delay)

    logger.warning(f"图片下载失败 ({last_error}): {url[:80]}")
    return False


# ==================== 批量下载 ====================

def download_images_for_review(
    review: dict,
    task_name: str,
    review_index: int,
) -> int:
    """
    下载单条评论中的所有图片到本地。

    下载后的图片保存在 images/{task_name}/review_{idx:04d}/ 目录下。
    成功下载的图片将该字段更新为本地路径，失败则保留原始 URL。

    Args:
        review: 评论数据字典（就地修改 image_urls 字段）
        task_name: 任务名称（用于目录命名）
        review_index: 评论序号（从0开始）

    Returns:
        成功下载的图片数量
    """
    image_urls = review.get("image_urls", [])
    if not image_urls:
        return 0

    # 清理任务名中的非法字符
    safe_task = _sanitize_filename(task_name)
    review_dir = get_images_dir() / safe_task / f"review_{review_index:04d}"
    review_dir.mkdir(parents=True, exist_ok=True)

    local_paths = []
    success_count = 0

    for img_idx, url in enumerate(image_urls):
        if not isinstance(url, str) or not url.startswith("http"):
            local_paths.append(url)  # 保留非 URL 值
            continue

        save_path = review_dir / f"img_{img_idx}"
        if _download_single_image(url, save_path):
            # 查找实际写入的文件
            for ext in ("jpeg", "jpg", "png", "gif", "webp", "bmp", "svg"):
                candidate = save_path.with_suffix(f".{ext}")
                if candidate.exists():
                    local_paths.append(str(candidate))
                    success_count += 1
                    break
            else:
                # 下载声称成功但文件未找到（极端情况），保留URL
                local_paths.append(url)
        else:
            # 下载失败，保留原始 URL 作为回退
            local_paths.append(url)

    # 就地更新
    review["image_urls"] = local_paths
    return success_count


def download_images_for_task(
    reviews: list[dict],
    task_name: str,
    progress_callback=None,
    max_workers: int = MAX_WORKERS,
) -> dict:
    """
    为任务中所有评论批量下载图片（多线程并发）。

    Args:
        reviews: 评论数据列表
        task_name: 任务名称
        progress_callback: 进度回调 callback(message: str, done: int, total: int)
        max_workers: 并发下载线程数

    Returns:
        统计结果 {"downloaded": int, "failed": int, "skipped": int, "total_reviews_with_images": int}
    """
    total_reviews = len(reviews)
    reviews_with_images = [r for r in reviews if r.get("image_urls")]
    total_with_images = len(reviews_with_images)

    if total_with_images == 0:
        logger.info(f"任务 [{task_name}] 没有需要下载的图片")
        return {"downloaded": 0, "failed": 0, "skipped": 0, "total_reviews_with_images": 0}

    logger.info(f"任务 [{task_name}] 开始下载图片: {total_with_images} 条评论有图片")

    if progress_callback:
        progress_callback(
            page_num=0, count=0, total=0,
            message=f"正在下载图片 (0/{total_with_images} 条评论)..."
        )

    total_downloaded = 0
    total_failed = 0

    # 使用线程池并发下载各评论的图片
    # 注意：每条评论内的图片串行下载，不同评论间并发
    lock = threading.Lock()
    completed = [0]  # 用列表包装以便在闭包中修改

    def _download_one(idx_review: tuple[int, dict]) -> tuple[int, int]:
        """下载单条评论的所有图片"""
        idx, review = idx_review
        downloaded = download_images_for_review(review, task_name, idx)
        failed = len([p for p in review.get("image_urls", [])
                     if isinstance(p, str) and p.startswith("http")])

        with lock:
            completed[0] += 1
            if progress_callback:
                progress_callback(
                    page_num=completed[0],
                    count=downloaded,
                    total=completed[0],
                    message=f"下载图片中 ({completed[0]}/{total_with_images} 条评论)..."
                )

        return downloaded, failed

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_download_one, (i, r)): i
            for i, r in enumerate(reviews_with_images)
        }
        for future in as_completed(futures):
            try:
                d, f = future.result()
                total_downloaded += d
                total_failed += f
            except Exception as e:
                logger.error(f"图片下载线程异常: {e}")
                total_failed += 1

    # 清理空目录
    safe_task = _sanitize_filename(task_name)
    task_dir = get_images_dir() / safe_task
    _remove_empty_dirs(task_dir)

    result = {
        "downloaded": total_downloaded,
        "failed": total_failed,
        "skipped": 0,
        "total_reviews_with_images": total_with_images,
    }

    if progress_callback:
        progress_callback(
            page_num=0, count=0, total=0,
            message=f"图片下载完成: {total_downloaded} 张成功, {total_failed} 张失败"
        )

    logger.info(
        f"任务 [{task_name}] 图片下载完成: "
        f"{total_downloaded} 张成功, {total_failed} 张失败 "
        f"({total_with_images} 条评论)"
    )
    return result


def _remove_empty_dirs(root: Path) -> None:
    """递归删除空目录"""
    try:
        for item in sorted(root.iterdir(), reverse=True):
            if item.is_dir():
                _remove_empty_dirs(item)
        # 目录为空则删除
        if not any(root.iterdir()):
            root.rmdir()
    except OSError:
        pass


def get_review_image_dir(task_name: str, review_index: int) -> Path:
    """
    获取指定评论的图片存储目录路径。

    Args:
        task_name: 任务名称
        review_index: 评论序号

    Returns:
        目录 Path 对象
    """
    safe_task = _sanitize_filename(task_name)
    return get_images_dir() / safe_task / f"review_{review_index:04d}"
