"""
模块名称：阿里系（淘宝/天猫）共享爬虫逻辑

功能说明：
    - 淘宝/天猫共用的 Selenium 爬虫核心
    - Cookie 注入、评论面板操作、滚动翻页、DOM 提取
    - 不包含站点适配器入口，适配器在 taobao.py / tmall.py 中分别创建

URL 格式：
    https://detail.tmall.com/item.htm?id=XXXXX
    https://item.taobao.com/item.htm?id=XXXXX
"""

import re
import time
import logging
from urllib.parse import urlparse

from src.sites.base import SiteAdapter, HttpMethod
from src.models.review import EMPTY_REVIEW

logger = logging.getLogger("tour-crawler.sites.taobao")

# 日志前缀
_prefix = ""


# ==================== URL 工具 ====================

def extract_url_params(url: str) -> dict[str, str]:
    """从淘宝/天猫商品 URL 中提取关键参数（域名、id、mi_id）"""
    from urllib.parse import urlparse
    params = {}
    # 提取域名
    try:
        host = urlparse(url).netloc.lower()
        # 取主域名（item.taobao.com / detail.tmall.com）
        for domain in ("item.taobao.com", "detail.tmall.com", "detail.taobao.com"):
            if domain in host:
                params["domain"] = domain
                break
    except Exception:
        pass
    # 提取 id
    m = re.search(r'[?&]id=(\d+)', url)
    if m:
        params["id"] = m.group(1)
    # 提取 mi_id
    m = re.search(r'[?&]mi_id=([^&]+)', url)
    if m:
        params["mi_id"] = m.group(1)
    return params


def build_taobao_url(domain: str, id: str, mi_id: str) -> str:
    """用提取的参数构造干净的淘宝/天猫商品页 URL"""
    return f"https://{domain}/item.htm?id={id}&mi_id={mi_id}"


# ==================== DOM 提取 ====================

def _get_text(el, driver) -> str:
    """通过 JS textContent 获取元素文本（不依赖视口渲染）"""
    text = driver.execute_script("return arguments[0].textContent", el)
    return (text or "").strip()


def _extract_review_from_element(item, driver) -> dict:
    """从单个评论卡片 DOM 元素中提取标准字段"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    review = EMPTY_REVIEW.copy()

    try:
        # --- 用户名 ---
        try:
            name_el = item.find_element(By.CSS_SELECTOR, ".userName--KpyzGX2s span")
            review["username"] = _get_text(name_el, driver)
        except NoSuchElementException:
            pass

        # --- 评论文本 ---
        try:
            content_el = item.find_element(By.CSS_SELECTOR, ".content--uonoOhaz")
            review["content"] = _get_text(content_el, driver)
        except NoSuchElementException:
            pass

        # --- 时间 + 购买信息 ---
        # 淘宝 meta 元素结构：日期文本 → <span>分隔线</span> → 已购：商品名
        # 取第一个文本节点作为日期，取 span 后面的文本作为购买信息
        try:
            meta_el = item.find_element(By.CSS_SELECTOR, ".meta--PLijz6qf")
            # 用 JS 提取第一个文本节点（日期部分）
            raw_date = driver.execute_script(
                "var n = arguments[0].firstChild;"
                "while (n && n.nodeType !== 3) n = n.nextSibling;"
                "return n ? n.textContent.trim() : '';",
                meta_el,
            )
            # 用 JS 提取 span 后面的文本节点（购买信息）
            purchase_text = driver.execute_script(
                "var s = arguments[0].querySelector('span');"
                "if (!s) return '';"
                "var n = s.nextSibling;"
                "while (n && n.nodeType !== 3) n = n.nextSibling;"
                "return n ? n.textContent.trim() : '';",
                meta_el,
            )
            # 仅当第一个文本节点含"年"才视为有效日期
            if raw_date and "年" in raw_date:
                review["time"] = raw_date
            # 购买信息去掉"已购："前缀
            if purchase_text.startswith("已购："):
                purchase_text = purchase_text[3:]
            if purchase_text:
                review["purchase_info"] = purchase_text
        except NoSuchElementException:
            pass

        # --- 图片 ---
        try:
            img_els = item.find_elements(By.CSS_SELECTOR, ".photo--ZUITAPZq img")
            img_urls = []
            for img in img_els:
                src = img.get_attribute("src") or ""
                if src and src.strip():
                    # 淘宝图片 URL 可能是 // 开头，补全协议
                    if src.startswith("//"):
                        src = "https:" + src
                    img_urls.append(src.strip())
            review["image_urls"] = img_urls
        except Exception:
            pass

        # --- 追评 ---
        try:
            append_el = item.find_element(By.CSS_SELECTOR, ".append--WvlQlFdT")
            append_content = append_el.find_element(By.CSS_SELECTOR, ".content--uonoOhaz")
            review["append_review"] = _get_text(append_content, driver)
        except NoSuchElementException:
            pass

    except Exception as e:
        logger.debug(f"提取淘宝评论异常: {e}")

    return review



# ==================== Cookie 注入 ====================

def _inject_cookies(driver, cookie_file: str, domain: str) -> bool:
    """在加载目标页面前注入 Cookie，绕过登录（统一使用淘宝 Cookie）"""
    if not cookie_file:
        return False

    try:
        from src.engine.cookie_manager import load_cookies_from_file

        cookies = load_cookies_from_file("taobao", cookie_file.replace(".json", ""))
        if not cookies:
            logger.warning(f"{_prefix}未找到 Cookie 文件: taobao/{cookie_file}")
            return False

        # 阿里系 Cookie 域为 .taobao.com，必须用淘宝域名注入
        driver.get("https://www.taobao.com")

        # 逐条注入 Cookie
        added = 0
        for c in cookies:
            try:
                cookie_dict = {
                    "name": c["name"],
                    "value": c["value"],
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                }
                if c.get("domain"):
                    cookie_dict["domain"] = c["domain"]
                driver.add_cookie(cookie_dict)
                added += 1
            except Exception:
                pass

        return added > 0

    except Exception as e:
        logger.warning(f"{_prefix}Cookie 注入失败: {e}")
        return False


# ==================== 页面预处理 ====================

def _click_all_reviews_button(driver) -> bool:
    """点击「查看全部评价」按钮，打开评论侧边面板"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import (
        NoSuchElementException,
        ElementClickInterceptedException,
        TimeoutException,
    )
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        # 等待按钮出现并点击
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".ShowButton--fMu7HZNs"))
        )
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)
        logger.info(f"{_prefix}已点击「查看全部评价」")
        return True
    except TimeoutException:
        logger.warning(f"{_prefix}等待「查看全部评价」按钮超时（10秒），页面可能未登录或按钮不存在")
        return False
    except NoSuchElementException:
        logger.warning(f"{_prefix}未找到「查看全部评价」按钮")
        return False
    except ElementClickInterceptedException:
        # 如果被遮挡，用 JS 强制点击
        try:
            btn = driver.find_element(By.CSS_SELECTOR, ".ShowButton--fMu7HZNs")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            return True
        except Exception:
            return False


def _set_sort_by_time(driver) -> bool:
    """点击排序下拉并选择「时间排序」"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    try:
        # 点击排序文字展开下拉
        sort_text = driver.find_element(By.CSS_SELECTOR, ".sortByText--jAWCjr5U")
        driver.execute_script("arguments[0].click();", sort_text)
        time.sleep(1)

        # 点击「时间排序」(排序列表中的第二个)
        sort_items = driver.find_elements(By.CSS_SELECTOR, ".sortItem--KqnXckES")
        if len(sort_items) >= 2:
            driver.execute_script("arguments[0].click();", sort_items[1])
            time.sleep(2)
            logger.info(f"{_prefix}已切换排序为「时间排序」")
            return True
        else:
            logger.warning(f"{_prefix}未找到「时间排序」选项")
            return False
    except NoSuchElementException:
        logger.warning(f"{_prefix}未找到排序控件")
        return False


# ==================== Selenium 爬虫主函数 ====================

def selenium_crawl_taobao(
    url: str,
    max_pages: int = 99999,
    max_count: int = 0,
    timeout: int = 600,
    stop_check=None,
    progress_callback=None,
    cookie_file=None,
    filter_chain=None,
    task_name: str = "",
    driver_ref: list | None = None,
    notifier=None,
    resume_page: int = 0,
    resume_count: int = 0,
    delay_seconds: float = 2.0,
) -> tuple[list[dict], int]:
    """
    通过 Selenium 翻页爬取淘宝/天猫商品评论。

    流程：
    1. 注入 Cookie 绕过登录
    2. 打开商品详情页
    3. 点击「查看全部评价」打开评论侧边面板
    4. 切换排序为「时间排序」
    5. 在评论面板内滚动加载更多评论
    6. 逐批提取评论，去重，过滤
    """
    global _prefix
    _prefix = f"任务 [{task_name}] " if task_name else ""

    try:
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        logger.error(f"{_prefix}Selenium 未安装")
        return [], 0

    # 浏览器配置（阿里系平台使用最小化窗口，便于用户手动验证）
    options = Options()
    options.page_load_strategy = 'eager'  # DOM就绪即返回，不等所有资源加载完
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")

    from src.engine.browser import create_edge_driver_minimized
    driver = create_edge_driver_minimized(options)
    if driver_ref is not None:
        driver_ref.append(driver)

    all_reviews = []
    total_rejected = 0

    try:
        # 提取 URL 参数并构造干净的访问地址
        url_params = extract_url_params(url)
        clean_url = build_taobao_url(
            url_params.get("domain", "item.taobao.com"),
            url_params.get("id", ""),
            url_params.get("mi_id", ""),
        )
        # 注入 Cookie（在加载目标页面前）
        _inject_cookies(driver, cookie_file, url_params.get("domain", ""))

        # 打开商品页
        driver.get(clean_url)
        wait = WebDriverWait(driver, 15)
        time.sleep(3)

        # 点击「查看全部评价」
        if not _click_all_reviews_button(driver):
            logger.error(f"{_prefix}无法打开评论面板，爬取终止")
            return [], 0

        # 切换排序为「时间排序」
        _set_sort_by_time(driver)

        # 等排序切换触发的加载完成
        time.sleep(delay_seconds)

        # 定位侧边面板容器，后续只爬取面板内的评论
        _panel = driver.execute_script("""
            var all = document.querySelectorAll('.Comment--H5QmJwe9');
            for (var i = 0; i < all.length; i++) {
                var p = all[i].parentElement;
                while (p && p !== document.body) {
                    var cls = (p.className || '').toString();
                    if (cls.indexOf('rawer') !== -1 || cls.indexOf('ialog') !== -1 ||
                        cls.indexOf('anel') !== -1 || cls.indexOf('verlay') !== -1) {
                        return p;
                    }
                    p = p.parentElement;
                }
            }
            return null;
        """)

        # 等待评论卡片出现在面板内
        try:
            wait.until(lambda d: _panel.find_elements(By.CSS_SELECTOR, ".Comment--H5QmJwe9"))
        except Exception:
            logger.warning(f"{_prefix}等待评论加载超时")

        # 翻页循环（通过滚动加载）
        no_new_count = 0  # 连续无新评论计数
        extracted_count = 0  # 已提取的DOM卡片数（用于切片新卡片）
        skipped_count = 0  # 断点续爬：已跳过的评论数

        # 断点续爬提示
        if resume_count > 0:
            logger.info(f"{_prefix}淘宝: 断点续爬，跳过前 {resume_count} 条已收集评论")

        for page in range(1, max_pages + 1):
            if stop_check and stop_check():
                logger.info(f"{_prefix}爬取被外部停止")
                break

            if max_count and len(all_reviews) >= max_count:
                logger.info(f"{_prefix}已达到目标条数 {max_count}，停止")
                break

            # 计算本轮还差多少条达到目标
            needed = max_count - len(all_reviews) if max_count else None

            page_start = time.time()

            # 验证码检测 → 通知用户手动处理
            from src.engine.captcha_handler import detect_captcha, wait_for_captcha_solved
            if detect_captcha(driver):
                logger.warning(f"{_prefix}淘宝: 遇到验证码，通知用户手动处理...")
                if not wait_for_captcha_solved(driver, notifier, task_name,
                                               progress_callback=progress_callback):
                    logger.error(f"{_prefix}淘宝: 等待验证码超时，终止爬取")
                    break
                time.sleep(2)
                continue

            # 只提取本轮新增的卡片（不超过目标需要的数量）
            all_items = _panel.find_elements(By.CSS_SELECTOR, ".Comment--H5QmJwe9")
            new_items = all_items[extracted_count:]
            if needed is not None and len(new_items) > needed:
                new_items = new_items[:needed]
            raw_count = len(new_items)

            # 本轮无新内容，等待后滚动加载更多
            if raw_count == 0 and len(all_reviews) > 0:
                no_new_count += 1
                if no_new_count >= 5:
                    logger.info(f"{_prefix}连续 {no_new_count} 次空闲无新评论，翻页结束")
                    break
                # 自适应等待：≥3次空闲用5秒特殊等待，否则用任务配置的延迟
                wait_sec = 5 if no_new_count >= 3 else delay_seconds
                logger.debug(f"{_prefix}第 {no_new_count} 次空闲，等待 {wait_sec}s")
                # 等待内容加载（不滑动屏幕）
                time.sleep(wait_sec)
                # 滚动加载更多
                items = all_items
                if items:
                    driver.execute_script("""
                        var el = arguments[0];
                        while (el) {
                            var s = window.getComputedStyle(el);
                            if ((s.overflowY === 'scroll' || s.overflowY === 'auto') && el.scrollHeight > el.clientHeight) {
                                el.scrollTop = Math.max(0, el.scrollTop - 10);
                                return;
                            }
                            el = el.parentElement;
                        }
                    """, items[-1])
                    time.sleep(0.3)
                    driver.execute_script("""
                        var el = arguments[0];
                        while (el) {
                            var s = window.getComputedStyle(el);
                            if ((s.overflowY === 'scroll' || s.overflowY === 'auto') && el.scrollHeight > el.clientHeight) {
                                el.scrollTop = el.scrollHeight;
                                return;
                            }
                            el = el.parentElement;
                        }
                    """, items[-1])
                else:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(wait_sec)  # 等滚动触发的新内容加载
                continue

            no_new_count = 0  # 有新评论，重置连续无新计数

            extracted_count += len(new_items)
            page_reviews = [_extract_review_from_element(item, driver) for item in new_items]
            page_reviews = [r for r in page_reviews if r.get("content")]

            # 过滤链
            rejected_batch = []
            if filter_chain and page_reviews:
                page_reviews, rejected_batch = filter_chain.apply(page_reviews)
                total_rejected += len(rejected_batch)

            # 断点续爬：跳过前 resume_count 条已收集评论
            if skipped_count < resume_count:
                remaining_skip = resume_count - skipped_count
                if len(page_reviews) <= remaining_skip:
                    skipped_count += len(page_reviews)
                    page_reviews = []  # 整批跳过
                else:
                    skipped_count += remaining_skip
                    page_reviews = page_reviews[remaining_skip:]  # 部分跳过

            before = len(all_reviews)
            all_reviews.extend(page_reviews)
            # 安全兜底：过滤后条数超过目标时截断
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            new_count = len(all_reviews) - before
            total_display = resume_count + len(all_reviews)  # 含已爬过的总数

            logger.info(f"{_prefix}第 {page} 页: 提取 {raw_count} 条（新增 {new_count} 条，累计 {total_display} 条）")

            if progress_callback:
                progress_callback(
                    page_num=page,
                    count=new_count,
                    total=total_display,
                    message=f"正在滚动加载第 {page} 轮...（累计 {total_display} 条）"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            # 超时检查
            if time.time() - page_start > timeout:
                logger.warning(f"{_prefix}第 {page} 轮处理超时（{timeout}秒）")
                break

            # 等待内容稳定后再滚动加载更多（不滑动屏幕）
            time.sleep(delay_seconds)
            items = _panel.find_elements(By.CSS_SELECTOR, ".Comment--H5QmJwe9")
            if items:
                driver.execute_script("""
                    var el = arguments[0];
                    while (el) {
                        var s = window.getComputedStyle(el);
                        if ((s.overflowY === 'scroll' || s.overflowY === 'auto') && el.scrollHeight > el.clientHeight) {
                            el.scrollTop = Math.max(0, el.scrollTop - 10);
                            return;
                        }
                        el = el.parentElement;
                    }
                """, items[-1])
                time.sleep(0.3)
                driver.execute_script("""
                    var el = arguments[0];
                    while (el) {
                        var s = window.getComputedStyle(el);
                        if ((s.overflowY === 'scroll' || s.overflowY === 'auto') && el.scrollHeight > el.clientHeight) {
                            el.scrollTop = el.scrollHeight;
                            return;
                        }
                        el = el.parentElement;
                    }
                """, items[-1])
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # 等滚动触发的新内容加载
            time.sleep(delay_seconds)

            if page >= max_pages:
                break

    except Exception as e:
        logger.error(f"{_prefix}Selenium 爬取异常: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        if driver_ref is not None:
            driver_ref.clear()

    return all_reviews, total_rejected
