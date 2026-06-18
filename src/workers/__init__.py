"""
工作线程包，提供 Qt QThread 工作线程实现。

包含：
    - crawl_worker.py: 爬取任务线程，在后台运行爬虫引擎
    - export_worker.py: 导出任务线程，在后台执行文件导出

设计说明：
    所有耗时操作（网络请求、文件写入）在独立 QThread 中运行，
    通过 Qt Signal 机制将进度实时推送到 UI 层，不阻塞主线程。
"""
