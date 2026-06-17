"""pytest 共享配置和 fixtures。"""

import os
import sys
import pytest

# 确保项目根目录在 Python path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_search_results():
    """提供标准的 mock 搜索结果，用于测试去重和格式化。"""
    return [
        {
            "results": [
                {"url": "https://example.com/a", "title": "文章 A", "content": "内容 A", "raw_content": "长内容 A"},
                {"url": "https://example.com/b", "title": "文章 B", "content": "内容 B", "raw_content": "长内容 B"},
            ]
        }
    ]


@pytest.fixture
def duplicate_search_results():
    """包含重复 URL 的搜索结果，用于测试去重逻辑。"""
    return [
        {
            "results": [
                {"url": "https://example.com/a", "title": "文章 A", "content": "内容 A"},
                {"url": "https://example.com/a", "title": "文章 A 重复", "content": "内容 A 重复"},
            ]
        }
    ]
