#***********************************************
#      Filename: utils.py
#   Description: 工具函数库
#***********************************************

import json
import os
import re
import yaml
from pathlib import Path
from datetime import datetime


# ===== UTILITY FUNCTIONS =====

def get_today_str() -> str:
    """获取今天的日期并返回格式化的字符串"""
    now = datetime.now()
    return f"{now:%a %b} {now.day}, {now:%Y}"

def parse_json_response(text: str) -> dict:
    """从 LLM 返回的文本中提取 JSON，兼容各种格式（裸 JSON、markdown 代码块等）"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 或 ``` ... ``` 代码块
    for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # 尝试匹配最外层 {...}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse JSON from response: {text[:500]}...")


def get_current_dir() -> Path:
    """获取当前的目录"""
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


# ===== CONFIG LOADER =====

def get_config_yml(path, section_name, subsection_name=None):
    """读取yaml文件"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No such file: {path}")

    with open(path, encoding="utf8") as f:
        data = yaml.safe_load(f)
        try:
            return (
                data[section_name]
                if subsection_name is None
                else data[section_name][subsection_name]
            )
        except KeyError as e:
            raise KeyError(
                f"No such section or subsection in config file: {section_name}, {subsection_name}. Config file: {path}"
            ) from e


def load_config(stage_name=None, config_path=None):
    """加载配置"""
    return get_config_yml(
        path=config_path or os.environ.get("CONFIG_PATH", "config.yml"),
        section_name="stages",
        subsection_name=stage_name,
    )
