"""
模块名称：淘宝/天猫（Taobao/Tmall）网站适配器

功能说明：
    - 淘宝/天猫商品评论页面的适配规则
    - 通过 Selenium 驱动浏览器：注入 Cookie → 点击查看全部评价 → 切换时间排序 → 滚动内置窗口翻页提取
    - 需要淘宝登录 Cookie

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
    """在加载目标页面前注入 Cookie，绕过登录"""
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


# ==================== 加载等待工具 ====================

def _wait_for_loading_done(driver, selectors: list[str], task_name: str = "",
                           max_wait: int = 15) -> bool:
    """
    等待页面加载动画消失后再继续。

    Args:
        driver: WebDriver 实例
        selectors: 加载动画的 CSS 选择器列表
        task_name: 任务名称（用于日志）
        max_wait: 最大等待秒数

    Returns:
        True 表示检测到加载动画并等待完成，False 表示页面空闲无加载
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    _prefix = f"任务 [{task_name}] " if task_name else ""
    waited = 0
    interval = 0.5
    loading_detected = False

    while waited < max_wait:
        loading_found = False
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    loading_found = True
                    break
            except NoSuchElementException:
                continue
            except Exception:
                continue

        if not loading_found:
            return loading_detected  # 加载完成，是否曾检测到加载

        loading_detected = True
        time.sleep(interval)
        waited += interval

    # 超时也继续，不阻塞流程
    logger.debug(f"{_prefix}等待加载动画超时（{max_wait}秒），继续执行")
    return loading_detected


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
) -> tuple[list[dict], int]:
    """
    通过 Selenium 翻页爬取淘宝商品评论。

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

        # 加载中检测：页面的加载动画选择器
        _LOADING_SELECTORS = [
            "[class*='loading']",
            "[class*='Loading']",
            "[class*='spinner']",
            "[class*='Spinner']",
            ".next-loading",
        ]

        # 切换排序为「时间排序」
        _set_sort_by_time(driver)

        # 等排序切换触发的加载完成
        _wait_for_loading_done(driver, _LOADING_SELECTORS, task_name)

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

            # 本轮无新内容，识别加载状态决定处理方式
            if raw_count == 0 and len(all_reviews) > 0:
                # 先等加载完成，检测是否真的有加载动画
                was_loading = _wait_for_loading_done(driver, _LOADING_SELECTORS, task_name)
                # 只有页面空闲（无加载动画）才计数，加载中不计数
                if not was_loading:
                    no_new_count += 1
                    if no_new_count >= 3:
                        logger.info(f"{_prefix}连续 {no_new_count} 次空闲无新评论，翻页结束")
                        break
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
                _wait_for_loading_done(driver, _LOADING_SELECTORS, task_name)
                time.sleep(1)
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

            before = len(all_reviews)
            all_reviews.extend(page_reviews)
            # 安全兜底：过滤后条数超过目标时截断
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            new_count = len(all_reviews) - before

            logger.info(f"{_prefix}第 {page} 页: 提取 {raw_count} 条（新增 {new_count} 条，累计 {len(all_reviews)} 条）")

            if progress_callback:
                progress_callback(
                    page_num=page,
                    count=new_count,
                    total=len(all_reviews),
                    message=f"正在滚动加载第 {page} 轮...（累计 {len(all_reviews)} 条）"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            # 超时检查
            if time.time() - page_start > timeout:
                logger.warning(f"{_prefix}第 {page} 轮处理超时（{timeout}秒）")
                break

            # 先等当前加载动画完成，再滚动加载更多（避免加载中途滚动导致漏评）
            _wait_for_loading_done(driver, _LOADING_SELECTORS, task_name)
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

            # 等待滚动触发的新加载完成
            _wait_for_loading_done(driver, _LOADING_SELECTORS, task_name)
            time.sleep(1)  # 渲染余量

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


# ==================== URL 校验 ====================

def _validate_taobao_url(url: str) -> tuple[bool, str]:
    """校验是否为有效的淘宝/天猫商品 URL（必须包含 id 和 mi_id 参数）"""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return (False, "无法解析 URL")

    valid_hosts = ["detail.tmall.com", "item.taobao.com", "detail.taobao.com"]
    if not any(h in host for h in valid_hosts):
        return (False, "仅支持 detail.tmall.com / item.taobao.com 的商品评价页面")
    if "id=" not in url:
        return (False, "URL 缺少商品 id 参数")
    if "mi_id=" not in url:
        return (False, "URL 缺少 mi_id 参数（淘宝/天猫商品页必需）")
    return (True, "")


# ==================== 适配器入口 ====================

def create_taobao_adapter() -> SiteAdapter:
    """创建淘宝适配器实例"""
    return SiteAdapter(
        site_name="taobao",
        site_display_name="淘宝",
        crawl_type="shopping",
        domain=".tmall.com",
        login_url="https://login.taobao.com/member/login.jhtml",
        url_template="https://detail.tmall.com/item.htm?id={id}&mi_id={mi_id}",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=99999,
        review_selector="",
        raw_html_parser=None,
        selenium_crawler=selenium_crawl_taobao,
        url_validator=_validate_taobao_url,
        field_mapping={},
    )
