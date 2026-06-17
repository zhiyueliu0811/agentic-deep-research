#***********************************************
#      Filename: llm.py
#   Description: 大模型客户端 
#***********************************************


from __future__ import annotations

import os
from typing import Any, Dict, Optional
from langchain.chat_models import init_chat_model

from deep_research.utils import load_config
from deep_research import logging as dr_logging


# 初始化logger
logger = dr_logging.get_logger(__name__)

# 缓存CONFIG，避免重复导入(config_path, stage, loader_id) 
_CONFIG_CACHE: Dict[tuple[str, str, int], Dict[str, Any]] = {}

# 默认的stage
DEFAULT_STAGE = "prod"


class LLMConfigError(ValueError):
    """当LLM配置错误或者不合法时抛出该异常"""


def _resolve_stage(stage: str | None) -> str:
    return stage or os.environ.get("STAGE") or DEFAULT_STAGE


def _load_stage_config(stage_name: str | None, config_path: str | None) -> Dict[str, Any]:
    """加载config.yml"""

    # Key作为config loader的唯一标识
    cache_key = (os.environ.get("CONFIG_PATH", "config.yml"), stage_name, id(load_config))

    if cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]

    cfg = load_config(stage_name=stage_name, config_path=config_path)
    if cfg is None:
        raise LLMConfigError(f"No config found for stage '{stage_name}'")

    _CONFIG_CACHE[cache_key] = cfg
    return cfg


def _build_openai_kwargs(
    handle: str,
    api_cfg: Dict[str, Any],
    max_tokens: int | None,
    timeout_seconds: Optional[int],
) -> Dict[str, Any]:
    """初始化llm client参数，例如api_key, base_url"""

    model = handle or api_cfg.get("default_model")
    if not model:
        raise LLMConfigError("OpenAI config requires a model name!")

    kwargs: Dict[str, Any] = {
        "model": model,
        "model_provider": "openai",
    }

    # api_key, base_url
    for key in ("api_key", "base_url", "organization"):
        if api_cfg.get(key):
            kwargs[key] = api_cfg[key]

    # 温度系数
    if api_cfg.get("temperature") is not None:
        kwargs["temperature"] = api_cfg["temperature"]

    # 最大token数
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    # 请求超时
    if timeout_seconds is not None:
        kwargs["timeout"] = timeout_seconds

    # qwen3-32b 非流式调用必须显式关闭思考模式
    if model.startswith("qwen3-32b"):
        kwargs["extra_body"] = {"enable_thinking": False}

    return kwargs


def _resolve_config_max_tokens(api_cfg: Dict[str, Any], handle: str) -> int | None:
    """解析最大token数"""
    models_cfg = api_cfg.get("models") or {}
    model_cfg = models_cfg.get(handle) or {}
    return model_cfg.get("max_tokens")


def _resolve_timeout_seconds(api_cfg: Dict[str, Any], role_cfg: Dict[str, Any]) -> Optional[int]:
    """解析timeout/request_timeout/timeout_seconds参数"""
    for cfg in (role_cfg, api_cfg):
        for key in ("timeout", "request_timeout", "timeout_seconds"):
            if cfg.get(key) is not None:
                return cfg.get(key)
    return None


def _build_kwargs(
    backend: str,
    handle: str,
    api_cfg: Dict[str, Any],
    role_cfg: Dict[str, Any],
    max_tokens: int | None,
    timeout_seconds: int | None,
) -> Dict[str, Any]:

    if backend == "openai":
        return _build_openai_kwargs(handle, api_cfg, max_tokens, timeout_seconds)
    else:
        raise LLMConfigError(f"Unsupported backend '{backend}'")


# 智能路由：query 字符数小于此值使用小模型
_ROUTING_COMPLEXITY_THRESHOLD = 100
_SIMPLE_MODEL_ROLE = "evaluator"
_COMPLEX_MODEL_ROLE = "writer"


# 任务类型 → 模型角色映射（规划/写作→235b，摘要/抽取→32b）
_TASK_ROLE_MAP = {
    "planning": "supervisor",
    "drafting": "writer",
    "summarizing": "researcher_compressor",
    "extracting": "evaluator",
    "verifying": "evaluator",
    "researching": "researcher_main",
    "critiquing": "red_team",
}


def get_chat_model_for_task(task_type: str, *, stage: str | None = None, max_tokens: int | None = None):
    """根据任务类型智能路由模型。规划/写作/研究 → 235b，摘要/抽取/验证/批评 → 32b。"""
    role = _TASK_ROLE_MAP.get(task_type)
    if role is None:
        logger.warning("Unknown task_type '%s', falling back to writer", task_type)
        role = "writer"
    logger.info("Task routing: '%s' → role '%s'", task_type, role)
    return get_chat_model(role, stage=stage, max_tokens=max_tokens)


def get_chat_model_auto(role: str, query_text: str = "", *, stage: str | None = None, max_tokens: int | None = None):
    """根据 query 复杂度自动路由模型。短 query → qwen3-32b，长 query → qwen3-235b。"""
    model_role = _SIMPLE_MODEL_ROLE if len(query_text) < _ROUTING_COMPLEXITY_THRESHOLD else _COMPLEX_MODEL_ROLE
    logger.info("Smart routing: role '%s' (query_len=%d) → model_role '%s'", role, len(query_text), model_role)
    return get_chat_model(model_role, stage=stage, max_tokens=max_tokens)


def get_chat_model(role: str, *, stage: str | None = None, max_tokens: int | None = None):
    """根据config和role返回LLM client.

    Args:
        role: 角色名，例如supervisor, writer
        stage: stage name
        max_tokens: 最大tokens
    """

    # 获取config路径
    config_path = os.environ.get("CONFIG_PATH", "config.yml")
    resolved_stage = _resolve_stage(stage)

    # 加载config.yam
    cfg = _load_stage_config(resolved_stage, config_path)

    # 获取role配置 
    roles_cfg = cfg.get("roles", {})
    if role not in roles_cfg:
        # 清除cache重新加载一次
        _CONFIG_CACHE.clear()
        cfg = _load_stage_config(resolved_stage, config_path)
        roles_cfg = cfg.get("roles", {})

    # 如果role配置错误
    if role not in roles_cfg:
        available = ", ".join(sorted(roles_cfg.keys())) or "<none>"
        raise LLMConfigError(
            f"Role '{role}' not found for stage '{resolved_stage}' using config '{config_path}'. Available: {available}"
        )

    # 解析backend和handle
    role_cfg = roles_cfg[role]
    backend = role_cfg.get("backend")
    handle = role_cfg.get("handle")
    if not backend or not handle:
        raise LLMConfigError(f"Role '{role}' is missing backend or handle")

    # 解析llm api config
    api_cfg = cfg.get("cognition", {}).get(backend)
    if api_cfg is None:
        raise LLMConfigError(f"No cognition config for backend '{backend}'")

    # 获取超时时间
    resolved_timeout = _resolve_timeout_seconds(api_cfg, role_cfg)
    logger.info(
        "Selected cognition backend '%s' for role '%s' with handle '%s' (timeout=%s)",
        backend,
        role,
        handle,
        resolved_timeout,
    )

    # 获取输出最大token数
    resolved_max_tokens = max_tokens
    if resolved_max_tokens is None:
        resolved_max_tokens = _resolve_config_max_tokens(api_cfg, handle)

    # 新建llm client
    kwargs = _build_kwargs(
        backend=backend,
        handle=handle,
        api_cfg=api_cfg,
        role_cfg=role_cfg,
        max_tokens=resolved_max_tokens,
        timeout_seconds=resolved_timeout
    )
    model = init_chat_model(**kwargs)
    try:
        from deep_research.callbacks.cost_tracker import get_cost_callback
        cb = get_cost_callback()
        if cb is not None:
            model = model.with_config({"callbacks": [cb]})
    except ImportError:
        pass
    return model
