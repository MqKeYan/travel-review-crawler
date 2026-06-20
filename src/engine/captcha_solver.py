"""
模块名称：验证码自动求解器

功能说明：
    - 自动检测并解决滑块验证码（阿里系 / 通用滑块）
    - 模拟人类拖拽轨迹：加速 → 匀速 → 减速 → 微调
    - 支持图像边缘检测精确定位缺口位置
    - 自动重试机制，失败后回退等待手动处理

技术方案：
    1. 检测页面中的滑块验证码元素（支持 iframe 嵌套）
    2. 计算滑动距离：
       - 主方案：图像处理定位缺口位置（精度最高）
       - 备选方案：轨道宽度比例估算
    3. 生成人类模拟轨迹（加速度曲线 + 随机抖动）
    4. 通过 Selenium ActionChains 执行拖拽
    5. 验证结果，失败自动重试

适用平台：
    - 飞猪 / 淘宝 / 天猫（阿里系滑块验证码 .nc_wrapper）
    - 其他使用通用滑块验证码的网站

依赖：
    - selenium (第三方)
    - PIL/Pillow (第三方，图像处理)
    - numpy (第三方，数组运算)
"""

import time
import random
import logging
import io
from typing import Optional

logger = logging.getLogger("tour-crawler.captcha_solver")

# 最大自动尝试次数，超过后回退手动模式
MAX_AUTO_ATTEMPTS = 3

# 滑块验证码元素选择器（按优先级排列）
_SLIDER_SELECTORS = {
    # 阿里系滑块（飞猪/淘宝/天猫）
    "ali_button": [
        "#nc_1_n1z",                      # 阿里滑块按钮 ID
        ".nc_iconfont.btn_slide",         # 阿里滑块按钮 class
        ".nc-lang-cnt .nc_iconfont",      # 阿里嵌套结构
        ".btn_slide",                     # 通用
    ],
    "ali_track": [
        "#nc_1__scale_text",              # 阿里滑块轨道
        ".nc-lang-cnt",                   # 阿里嵌套结构
        ".scale_text",                    # 通用
    ],
    "ali_container": [
        "#nocaptcha",                     # 阿里无感验证容器
        ".nc_wrapper",                    # 阿里验证码包装
        ".captcha-container",             # 通用
    ],
    # 通用滑块
    "generic_slider": [
        ".slidetounlock",
        ".slider-captcha",
        "[class*='slide']",
    ],
    # iframe 中的滑块
    "iframe_indicators": [
        "iframe[src*='nocaptcha']",
        "iframe[src*='captcha']",
        "iframe[id*='captcha']",
    ],
}


# ==================== 滑块检测 ====================

def detect_slider_captcha(driver) -> bool:
    """
    检测当前页面是否存在滑块验证码。

    检测策略（多维度）：
    1. 页面标题含关键词
    2. 页面 URL 含关键词
    3. DOM 中存在滑块元素
    4. 页面文本含验证码提示

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

        # 方式2：URL 检测
        url = driver.current_url.lower()
        url_keywords = ["captcha", "verify", "check", "sec"]
        for kw in url_keywords:
            if kw in url and ("login" not in url or "captcha" in url):
                logger.info(f"验证码检测(URL): 匹配关键词 '{kw}'")
                return True

        # 方式3：DOM 元素检测
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException

        # 检查阿里滑块
        for selector in _SLIDER_SELECTORS["ali_button"]:
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                logger.info(f"验证码检测(DOM): 找到滑块按钮 {selector}")
                return True
            except NoSuchElementException:
                pass

        # 检查通用滑块
        for selector in _SLIDER_SELECTORS["generic_slider"]:
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                logger.info(f"验证码检测(DOM): 找到通用滑块 {selector}")
                return True
            except NoSuchElementException:
                pass

        # 方式4：页面文本检测
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


def _find_slider_elements(driver):
    """
    查找滑块验证码的关键元素。

    支持：
    - 主页面中的滑块
    - iframe 中嵌套的滑块（阿里系常见）

    Returns:
        (button_element, track_element) 或 (None, None)
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    def _try_find(selectors):
        for sel in selectors:
            try:
                return driver.find_element(By.CSS_SELECTOR, sel)
            except NoSuchElementException:
                continue
        return None

    # 1. 先在主页面查找
    btn = _try_find(_SLIDER_SELECTORS["ali_button"])
    if btn:
        track = _try_find(_SLIDER_SELECTORS["ali_track"])
        logger.info("滑块定位: 主页面中找到滑块按钮")
        return btn, track

    # 2. 尝试在 iframe 中查找
    iframe_selectors = _SLIDER_SELECTORS["iframe_indicators"]
    for iframe_sel in iframe_selectors:
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, iframe_sel)
            driver.switch_to.frame(iframe)
            btn = _try_find(_SLIDER_SELECTORS["ali_button"])
            if btn:
                track = _try_find(_SLIDER_SELECTORS["ali_track"])
                logger.info(f"滑块定位: iframe ({iframe_sel}) 中找到滑块按钮")
                return btn, track
            driver.switch_to.default_content()
        except NoSuchElementException:
            continue

    # 3. 尝试所有 iframe
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                btn = _try_find(_SLIDER_SELECTORS["ali_button"])
                if btn:
                    track = _try_find(_SLIDER_SELECTORS["ali_track"])
                    logger.info("滑块定位: 未知 iframe 中找到滑块按钮")
                    return btn, track
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()
                continue
    except Exception:
        pass

    # 4. 通用滑块回退
    btn = _try_find(_SLIDER_SELECTORS["generic_slider"])
    if btn:
        logger.info("滑块定位: 通用滑块")
        return btn, None

    return None, None


# ==================== 滑动距离计算 ====================

def _calculate_distance_by_track(driver, slider_btn, track_el) -> float:
    """
    通过轨道/滑块尺寸估算滑动距离（备选方案）。

    Returns:
        估算的滑动距离（像素）
    """
    try:
        if track_el:
            track_width = track_el.size["width"]
            btn_width = slider_btn.size["width"]
            # 滑动距离 = 轨道宽度 - 按钮宽度 - 少量余量
            distance = track_width - btn_width - 2
            logger.info(f"距离估算(轨道): track={track_width}, btn={btn_width}, dist={distance}")
            return max(distance, 100)  # 至少滑动100px
    except Exception:
        pass

    # 回退：使用固定估算值
    logger.info("距离估算: 使用默认值 300px")
    return 300.0


def _calculate_distance_by_image(driver) -> Optional[float]:
    """
    通过图像处理精确定位滑块缺口位置（主方案）。

    原理：
    1. 截取验证码背景图
    2. 使用边缘检测找到缺口位置
    3. 将像素位置映射为滑动距离

    Returns:
        滑动距离（像素），失败返回 None
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        logger.info("PIL/numpy 未安装，跳过图像定位")
        return None

    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    # 尝试获取阿里滑块背景图
    bg_selectors = [
        "#nc_1__bg",                # 阿里滑块背景
        ".nc-lang-cnt .nc-canvas",  # 阿里画布
        "canvas.slider-bg",         # 通用画布背景
        ".slider-bg-img",           # 通用背景图
    ]

    bg_element = None
    for sel in bg_selectors:
        try:
            bg_element = driver.find_element(By.CSS_SELECTOR, sel)
            break
        except NoSuchElementException:
            continue

    if bg_element is None:
        logger.info("图像定位: 未找到背景图元素")
        return None

    # 截取背景元素
    try:
        bg_screenshot = bg_element.screenshot_as_png
        bg_image = Image.open(io.BytesIO(bg_screenshot))
    except Exception:
        # 回退：截图整个页面再裁剪
        try:
            full_screenshot = driver.get_screenshot_as_png()
            full_image = Image.open(io.BytesIO(full_screenshot))
            loc = bg_element.location
            size = bg_element.size
            bg_image = full_image.crop((
                loc["x"], loc["y"],
                loc["x"] + size["width"], loc["y"] + size["height"]
            ))
        except Exception as e:
            logger.warning(f"图像定位: 截图失败 - {e}")
            return None

    # 转为灰度图进行边缘检测
    try:
        bg_gray = bg_image.convert("L")
        bg_array = np.array(bg_gray)

        # 使用 Canny 边缘检测定位缺口
        # 缺口的特征：垂直边缘明显，通常位于图像中段
        height, width = bg_array.shape

        # 沿水平方向计算每列的边缘强度
        edge_strength = np.zeros(width)
        for x in range(1, width - 1):
            # 垂直梯度（缺口边缘通常是垂直的）
            col_diff = np.abs(np.diff(bg_array[:, x].astype(np.float64)))
            edge_strength[x] = np.sum(col_diff)

        # 缺口特征：在中间区域找到边缘最强的位置
        # 排除左右两侧（通常是边框）
        margin = int(width * 0.05)
        search_start = margin
        search_end = width - margin

        if search_end <= search_start:
            return None

        edge_strength = edge_strength.astype(np.float64)  # 确保类型兼容
        # 对边缘强度做平滑处理，减少噪声
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(edge_strength, kernel, mode="same")

        # 在搜索范围内找到峰值位置
        search_region = smoothed[search_start:search_end]
        if len(search_region) == 0:
            return None

        peak_idx = np.argmax(search_region) + search_start
        gap_position = float(peak_idx)

        # 根据实际页面比例换算距离
        # 阿里滑块的轨道宽度通常为 300-360px
        track_scale = 300.0 / width if width > 0 else 1.0
        distance = gap_position * track_scale

        logger.info(f"图像定位: 图宽={width}, 缺口位置={gap_position:.0f}px, "
                    f"换算距离={distance:.1f}px")
        return max(distance, 20.0)  # 至少滑动20px

    except Exception as e:
        logger.warning(f"图像定位: 处理失败 - {e}")
        return None


def _calculate_slide_distance(driver, slider_btn, track_el) -> float:
    """
    综合计算滑块需要拖动的距离。

    优先级：
    1. 图像处理精确定位
    2. 轨道宽度估算
    3. 固定默认值
    """
    # 方案1：图像定位
    distance = _calculate_distance_by_image(driver)
    if distance is not None and distance > 10:
        return distance

    # 方案2：轨道估算
    distance = _calculate_distance_by_track(driver, slider_btn, track_el)

    # 加入小量随机抖动，模拟人类行为
    jitter = random.uniform(-3, 3)
    return distance + jitter


# ==================== 人类轨迹生成 ====================

def _generate_human_track(distance: float) -> list[tuple[float, float, float]]:
    """
    生成模拟人类的滑动轨迹。

    轨迹特征：
    - 加速阶段（0~20%）：缓慢起步
    - 匀速阶段（20%~70%）：较快匀速
    - 减速阶段（70%~90%）：逐步减速
    - 微调阶段（90%~100%）：微小调整
    - 随机抖动：小幅度的 y 轴偏移
    - 随机停顿：模仿人类犹豫

    Args:
        distance: 目标滑动距离（像素）

    Returns:
        轨迹点列表 [(x_offset, y_offset, duration_ms), ...]
    """
    track = []
    current_x = 0.0
    current_y = 0.0
    total_time = 0.0

    # 轨迹分为 4 个阶段
    stages = [
        (0.20, 0.10, "加速"),      # 占比20%，耗时10%
        (0.70, 0.35, "匀速"),      # 占比50%，耗时35%
        (0.90, 0.35, "减速"),      # 占比20%，耗时35%
        (1.00, 0.20, "微调"),      # 占比10%，耗时20%
    ]

    # 总滑动时间 0.5~1.2秒（人类拖拽的典型时长）
    total_duration = random.uniform(500, 1200)

    remaining_distance = distance

    for stage_idx, (end_ratio, time_ratio, stage_name) in enumerate(stages):
        stage_target = distance * end_ratio
        stage_distance = stage_target - current_x
        stage_duration = total_duration * time_ratio

        # 该阶段中的步数 (8~20步/阶段)
        steps = random.randint(8, 20)
        step_duration = stage_duration / steps

        for step in range(steps):
            # 进度 (0~1)
            progress = (step + 1) / steps

            if stage_name == "加速":
                # 加速：位置变化逐渐增大
                ease = progress ** 1.5
            elif stage_name == "匀速":
                # 匀速：位置线性变化
                ease = progress
            elif stage_name == "减速":
                # 减速：位置变化逐渐减小
                ease = 1 - (1 - progress) ** 2
            else:  # 微调
                # 微小步进，带随机性
                ease = progress * (0.8 + random.random() * 0.2)

            step_x = stage_distance * ease
            actual_x = current_x + (step_x - (current_x - distance * stages[stage_idx-1][0] if stage_idx > 0 else 0))

            # 简化计算
            target_x = stage_target * ease if stage_name != "微调" else stage_target * progress
            previous_stage_end = distance * stages[stage_idx - 1][0] if stage_idx > 0 else 0
            actual_x = previous_stage_end + stage_distance * ease

            # y 轴微小抖动 (±1.5px)
            y_jitter = random.uniform(-1.5, 1.5)
            actual_y = y_jitter

            # 偶尔的随机停顿（5%概率）
            extra_delay = 0
            if random.random() < 0.05:
                extra_delay = random.randint(20, 80)

            total_time += step_duration + extra_delay
            track.append((round(actual_x, 1), round(actual_y, 1), round(total_time, 0)))
            current_x = actual_x
            current_y = actual_y

    # 确保最终位置准确到达目标
    if track:
        last = track[-1]
        track[-1] = (round(distance, 1), last[1], last[2])

    logger.debug(f"轨迹生成: {distance}px, {len(track)} 步, {total_time:.0f}ms")
    return track


# ==================== 执行滑动 ====================

def _execute_drag(driver, slider_btn, track: list[tuple[float, float, float]]) -> bool:
    """
    在滑块元素上执行模拟人类的拖拽操作。

    使用 Selenium ActionChains 分步执行轨迹中的每个点，
    先按住滑块不放，按轨迹逐步移动，最后释放。

    Args:
        driver: WebDriver 实例
        slider_btn: 滑块按钮 WebElement
        track: 轨迹点列表

    Returns:
        True 表示拖拽执行完成
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver import ActionChains
    from selenium.webdriver.common.actions.action_builder import ActionBuilder
    from selenium.webdriver.common.actions.pointer_input import PointerInput
    from selenium.webdriver.common.actions import interaction

    try:
        # 确保滑块可见并滚动到视口
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slider_btn)
        time.sleep(0.5)

        # 使用 ActionChains 执行拖拽
        actions = ActionChains(driver)
        actions.click_and_hold(slider_btn)

        # 按轨迹逐步移动
        prev_x = 0.0
        prev_time = 0.0
        for x_offset, y_offset, elapsed_ms in track:
            dx = x_offset - prev_x
            dy = y_offset  # y 轴偏移是绝对值，需要转为增量
            wait_ms = elapsed_ms - prev_time

            if dx > 0 or abs(dy) > 0.1:
                actions.move_by_offset(dx, dy)
                if wait_ms > 5:
                    actions.pause(wait_ms / 1000.0)

            prev_x = x_offset
            prev_time = elapsed_ms

        # 在终点稍作停顿后释放
        actions.pause(0.2)
        actions.release()
        actions.perform()

        logger.info(f"滑动执行: 轨迹 {len(track)} 步, 最终偏移 {track[-1][0]:.0f}px")
        return True

    except Exception as e:
        logger.error(f"滑动执行失败: {e}")
        # 备用方案：JavaScript 直接模拟
        try:
            _execute_drag_by_js(driver, slider_btn, track[-1][0])
            return True
        except Exception as e2:
            logger.error(f"JS 滑动也失败: {e2}")
            return False


def _execute_drag_by_js(driver, slider_btn, distance: float) -> None:
    """
    JavaScript 方式执行滑动（备用方案）。

    通过派发 mousedown → mousemove → mouseup 事件序列来模拟拖拽。
    某些网站的验证码对 ActionChains 有检测，JS 方式隐蔽性更好。
    """
    x = slider_btn.location["x"] + slider_btn.size["width"] / 2
    y = slider_btn.location["y"] + slider_btn.size["height"] / 2

    script = f"""
    var btn = arguments[0];
    var dist = arguments[1];
    var startX = arguments[2];
    var startY = arguments[3];

    // 创建鼠标事件辅助函数
    function dispatchMouseEvent(target, type, clientX, clientY) {{
        var event = new MouseEvent(type, {{
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: clientX,
            clientY: clientY,
            button: 0
        }});
        target.dispatchEvent(event);
    }}

    // 模拟拖拽过程
    dispatchMouseEvent(btn, 'mousedown', startX, startY);

    // 分步移动（模拟人类轨迹）
    var steps = 25;
    var stepDist = dist / steps;
    var currentX = startX;
    for (var i = 1; i <= steps; i++) {{
        currentX = startX + stepDist * i;
        dispatchMouseEvent(document, 'mousemove', currentX, startY);
    }}

    // 释放
    dispatchMouseEvent(document, 'mouseup', currentX, startY);
    """
    driver.execute_script(script, slider_btn, distance, x, y)
    logger.info(f"JS 滑动: distance={distance:.0f}px")


# ==================== 主入口 ====================

def solve_slider_captcha(driver, max_attempts: int = MAX_AUTO_ATTEMPTS) -> bool:
    """
    自动检测并解决当前页面的滑块验证码。

    完整流程：
    1. 检测页面是否存在验证码
    2. 定位滑块元素
    3. 计算滑动距离
    4. 生成模拟轨迹
    5. 执行拖拽
    6. 等待验证结果
    7. 失败则重试

    Args:
        driver: Selenium WebDriver 实例
        max_attempts: 最大自动尝试次数

    Returns:
        True 表示验证码已通过或不存在
    """
    # 先检测是否需要验证
    if not detect_slider_captcha(driver):
        return True  # 没有验证码，直接返回成功

    logger.info("=" * 50)
    logger.info("验证码自动求解器启动")

    for attempt in range(1, max_attempts + 1):
        logger.info(f"--- 第 {attempt}/{max_attempts} 次尝试 ---")

        try:
            # 等待滑块渲染完成
            time.sleep(1 + attempt * 0.5)

            # 切换回主文档（可能之前在 iframe 中）
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

            # 1. 定位滑块
            btn, track = _find_slider_elements(driver)
            if btn is None:
                logger.warning("未找到滑块元素，可能不是滑块验证码")
                # 尝试刷新等待后重新检测
                time.sleep(3)
                if not detect_slider_captcha(driver):
                    logger.info("验证码已消失")
                    return True
                continue

            # 2. 计算距离
            distance = _calculate_slide_distance(driver, btn, track)
            logger.info(f"计算滑动距离: {distance:.1f}px")

            # 3. 生成轨迹
            track_points = _generate_human_track(distance)

            # 4. 执行拖动
            success = _execute_drag(driver, btn, track_points)
            if not success:
                continue

            # 5. 等待验证结果（页面响应需要时间）
            time.sleep(3)

            # 6. 检查是否通过
            if not detect_slider_captcha(driver):
                logger.info("✓ 验证码自动通过！")
                # 等待页面恢复正常
                time.sleep(2)
                return True

            # 验证码还存在，可能距离不对
            logger.warning(f"第 {attempt} 次尝试未通过，可能距离偏差")

            # 尝试点击刷新验证码
            _try_refresh_captcha(driver)

        except Exception as e:
            logger.error(f"第 {attempt} 次尝试异常: {e}")

    logger.warning(f"自动求解失败 ({max_attempts}次)，需要手动处理")
    return False


def _try_refresh_captcha(driver) -> None:
    """
    尝试点击验证码刷新按钮获取新滑块。

    某些验证码允许刷新以获取新的滑块位置。
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    refresh_selectors = [
        ".nc-container .nc_refresh",
        ".captcha-refresh",
        ".refresh-btn",
        "[class*='refresh']",
        "a[href*='refresh']",
    ]

    for sel in refresh_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", btn)
            logger.info("已点击刷新验证码")
            time.sleep(2)
            return
        except NoSuchElementException:
            continue


def solve_captcha_with_fallback(driver, progress_callback=None) -> str:
    """
    尝试验证码求解，失败则通知用户手动处理。

    这是飞猪爬虫中使用的统一入口。

    Args:
        driver: WebDriver 实例
        progress_callback: 进度回调函数

    Returns:
        "auto" — 自动求解成功
        "manual_needed" — 需要手动处理
        "passed" — 不需要验证码
    """
    # 检查是否需要验证
    if not detect_slider_captcha(driver):
        return "passed"

    if progress_callback:
        progress_callback(page_num=0, count=0, total=0,
                         message="检测到验证码，正在自动求解...")

    # 尝试自动求解
    if solve_slider_captcha(driver):
        if progress_callback:
            progress_callback(page_num=0, count=0, total=0,
                             message="验证码自动通过，继续爬取...")
        return "auto"

    # 自动求解失败，通知用户
    if progress_callback:
        progress_callback(page_num=0, count=0, total=0,
                         message="自动求解失败，请在浏览器窗口中手动完成验证...")
    logger.warning("验证码自动求解失败，等待手动处理")
    return "manual_needed"
