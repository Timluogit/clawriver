"""app/core/validators.py — ID 格式验证"""
import re
from typing import Optional
from fastapi import HTTPException

# ID 格式规范
ID_PATTERNS = {
    "memory": re.compile(r"^mem_[0-9a-f]{12}$"),
    "agent": re.compile(r"^agent_[0-9a-f]{12}$"),
    "team": re.compile(r"^team_[0-9a-f]{12}$"),
    "purchase": re.compile(r"^pur_[0-9a-f]{12}$"),
    "rating": re.compile(r"^rat_[0-9a-f]{12}$"),
    "verification": re.compile(r"^ver_[0-9a-f]{12}$"),
    "audit": re.compile(r"^audit_[0-9a-f]{12}$"),
    "version": re.compile(r"^ver_[0-9a-f]{12}$"),
}

# 通用 ID 模式（前缀_12位hex，总长 <= 50）
GENERAL_ID_PATTERN = re.compile(r"^[a-z]+_[0-9a-f]{6,20}$")

# 严格的 hex 前缀白名单
ALLOWED_PREFIXES = {"mem", "agent", "team", "pur", "rat", "ver", "audit",
                     "tx", "stats", "perm", "role", "pol", "pver", "patt",
                     "uprof", "fact", "ucont", "pchange", "abtest", "anom",
                     "alert", "rule", "exp", "inv", "tctx", "act", "pcache",
                     "paudit", "click", "search"}


def validate_id(
    value: str,
    id_type: Optional[str] = None,
    field_name: str = "id",
) -> str:
    """
    验证 ID 格式
    
    Args:
        value: 待验证的 ID 值
        id_type: ID 类型（memory/agent/team 等），如果为 None 则使用通用规则
        field_name: 字段名（用于错误消息）
    
    Returns:
        验证通过的 ID 值
    
    Raises:
        HTTPException: 格式不合法时抛出 400 错误
    """
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{field_name} 不能为空")
    
    # 长度限制（数据库字段为 String(50)）
    if len(value) > 50:
        raise HTTPException(
            status_code=400, 
            detail=f"{field_name} 格式不合法：长度超过限制"
        )
    
    # 只允许安全字符
    if not re.match(r"^[a-z0-9_]+$", value):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 格式不合法：只允许小写字母、数字和下划线"
        )
    
    # 前缀白名单检查
    prefix = value.split("_")[0] if "_" in value else ""
    if prefix not in ALLOWED_PREFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 格式不合法：未知前缀 '{prefix}'"
        )
    
    # 特定类型严格验证
    if id_type and id_type in ID_PATTERNS:
        if not ID_PATTERNS[id_type].match(value):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} 格式不合法：期望格式 {id_type}_xxxxxxxxxxxx"
            )
    
    return value


def validate_memory_id(memory_id: str) -> str:
    """验证 memory_id 格式"""
    return validate_id(memory_id, "memory", "memory_id")


def validate_agent_id(agent_id: str) -> str:
    """验证 agent_id 格式"""
    return validate_id(agent_id, "agent", "agent_id")


def validate_team_id(team_id: str) -> str:
    """验证 team_id 格式"""
    return validate_id(team_id, "team", "team_id")
