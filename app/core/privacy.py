"""隐私扫描器 - 检测并脱敏敏感信息"""
import re
from typing import Dict, List, Tuple

# 敏感信息正则模式
PRIVACY_PATTERNS = {
    "api_key": (r'(?:sk-|api[_-]?key|apikey|token|secret)[\s:=]+["\']?([A-Za-z0-9_\-]{20,})["\']?', "[REDACTED_API_KEY]"),
    "password": (r'(?:password|passwd|pwd|pass)[\s:=]+["\']?([^\s"\';,]{6,})["\']?', "[REDACTED_PASSWORD]"),
    "email": (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', "[REDACTED_EMAIL]"),
    "phone_cn": (r'(?:\+86)?1[3-9]\d{9}\b', "[REDACTED_PHONE]"),
    "private_ip": (r'\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b', "[REDACTED_IP]"),
    "uuid": (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', "[REDACTED_UUID]"),
    "bearer_token": (r'Bearer\s+[A-Za-z0-9_\-\.]{20,}', "Bearer [REDACTED_TOKEN]"),
    "aws_key": (r'AKIA[0-9A-Z]{16}', "[REDACTED_AWS_KEY]"),
    "github_pat": (r'ghp_[A-Za-z0-9]{36}', "[REDACTED_GITHUB_TOKEN]"),
}

def scan_and_redact(text: str) -> Tuple[str, List[Dict]]:
    """扫描文本并脱敏敏感信息
    
    Returns:
        (脱敏后的文本, 检测到的敏感信息列表)
    """
    if not text:
        return text, []
    
    findings = []
    redacted = text
    
    for pattern_name, (pattern, replacement) in PRIVACY_PATTERNS.items():
        matches = list(re.finditer(pattern, redacted, re.IGNORECASE))
        if matches:
            for m in matches:
                findings.append({
                    "type": pattern_name,
                    "position": (m.start(), m.end()),
                    "preview": m.group()[:10] + "..."
                })
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    
    return redacted, findings

def redact_memory_content(title: str, summary: str, content: dict) -> Tuple[str, str, dict, List[Dict]]:
    """脱敏记忆的所有字段
    
    Returns:
        (脱敏后的title, summary, content, findings)
    """
    all_findings = []
    
    redacted_title, findings = scan_and_redact(title)
    all_findings.extend([{**f, "field": "title"} for f in findings])
    
    redacted_summary, findings = scan_and_redact(summary)
    all_findings.extend([{**f, "field": "summary"} for f in findings])
    
    redacted_content = _redact_dict(content)
    all_findings.extend([{**f, "field": "content"} for f in findings])
    
    return redacted_title, redacted_summary, redacted_content, all_findings

def _redact_dict(d: dict) -> dict:
    """递归脱敏字典中的所有字符串值"""
    if not isinstance(d, dict):
        if isinstance(d, str):
            redacted, _ = scan_and_redact(d)
            return redacted
        return d
    
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k], _ = scan_and_redact(v)
        elif isinstance(v, dict):
            result[k] = _redact_dict(v)
        elif isinstance(v, list):
            result[k] = [_redact_dict(item) if isinstance(item, (dict, str)) else item for item in v]
        else:
            result[k] = v
    return result
