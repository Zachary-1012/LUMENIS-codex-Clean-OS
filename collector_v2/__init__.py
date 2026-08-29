"""
采集引擎 V2 - 模块化架构
基于采集引擎.docx的研究方案实现
- PlatformCollector 基类（统一接口）
- BrowserSession 独立登录管理
- XHSClient 独立HTTP请求层（含评论分页）
- Pipeline 数据处理流水线（标准化/去重/主体过滤/持久化）
- 主体过滤不放进爬虫，由系统层判断
"""
__version__ = "2.0.0"
