"""敏感信息脱敏模块"""
import re
import json
from typing import Any, Dict, List, Optional
from hashlib import sha256


class Sanitizer:
    """敏感信息脱敏器"""

    # 敏感字段名称模式（不区分大小写）
    SENSITIVE_PATTERNS = [
        r'password', r'pwd', r'passwd',  # 密码
        r'token', r'access[_-]?token', r'refresh[_-]?token', r'auth[_-]?token',  # Token
        r'api[_-]?key', r'apikey', r'secret', r'private[_-]?key',  # 密钥
        r'credit[_-]?card', r'card[_-]?number', r'cc[_-]?num',  # 信用卡
        r'ssn', r'social[_-]?security',  # 社会安全号
        r'phone', r'tel', r'mobile',  # 电话号码
        r'address',  # 地址
    ]

    # 部分脱敏字段（保留部分信息）
    PARTIAL_SENSITIVE_PATTERNS = [
        r'email', r'mail',  # 邮箱
    ]

    # 敏感内容正则模式
    CONTENT_PATTERNS = {
        'password': re.compile(r'["\']?password["\']?\s*[:=]\s*["\']?([^"\'\s,}]{6,})["\']?', re.IGNORECASE),
        'token': re.compile(r'["\']?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?', re.IGNORECASE),
        'api_key': re.compile(r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
        'credit_card': re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}\b'),
        'email': re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    }

    def __init__(self, mask_char: str = '*', preserve_length: bool = True):
        """
        初始化脱敏器

        Args:
            mask_char: 脱敏占位符
            preserve_length: 是否保持原始长度
        """
        self.mask_char = mask_char
        self.preserve_length = preserve_length

    def is_sensitive_field(self, field_name: str) -> bool:
        """判断字段名是否敏感"""
        field_lower = field_name.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, field_lower):
                return True
        return False

    def is_partial_sensitive_field(self, field_name: str) -> bool:
        """判断字段名是否需要部分脱敏"""
        field_lower = field_name.lower()
        for pattern in self.PARTIAL_SENSITIVE_PATTERNS:
            if re.search(pattern, field_lower):
                return True
        return False

    def mask_value(self, value: Any, field_name: str = None) -> Any:
        """
        脱敏单个值

        Args:
            value: 原始值
            field_name: 字段名（用于判断是否需要脱敏）

        Returns:
            脱敏后的值
        """
        if value is None:
            return None

        # 如果指定了字段名且该字段是敏感字段，直接脱敏
        if field_name and self.is_sensitive_field(field_name):
            if isinstance(value, str):
                return self._mask_string(value)
            return str(self._generate_hash(str(value)))

        # 根据值类型处理
        if isinstance(value, str):
            return self._mask_sensitive_content(value)
        elif isinstance(value, dict):
            return self.sanitize_dict(value)
        elif isinstance(value, list):
            return self.sanitize_list(value)
        else:
            # 其他类型转换为字符串后检查
            str_value = str(value)
            masked = self._mask_sensitive_content(str_value)
            return value if masked == str_value else masked

    def _mask_string(self, value: str) -> str:
        """脱敏字符串（保持长度）"""
        if self.preserve_length:
            return self.mask_char * len(value)
        else:
            if len(value) <= 4:
                return self.mask_char * 4
            return self.mask_char * 4 + value[2:]

    def _mask_sensitive_content(self, value: str) -> str:
        """
        检查字符串内容中的敏感信息并脱敏

        Args:
            value: 原始字符串

        Returns:
            脱敏后的字符串
        """
        result = value

        # 信用卡：保留最后4位
        result = re.sub(
            self.CONTENT_PATTERNS['credit_card'],
            lambda m: '*' * (len(m.group(0)) - 4) + m.group(0)[-4:],
            result
        )

        # SSN：保留最后4位
        result = re.sub(
            self.CONTENT_PATTERNS['ssn'],
            lambda m: '***-**-' + m.group(0)[-4:],
            result
        )

        # 邮箱：保留首字符和@域名
        def mask_email(match):
            email = match.group(0)
            local, domain = email.split('@')
            masked_local = local[0] + '*' * (len(local) - 1)
            return f"{masked_local}@{domain}"

        result = re.sub(
            self.CONTENT_PATTERNS['email'],
            mask_email,
            result
        )

        # 电话：保留最后4位
        def mask_phone(match):
            phone = match.group(0)
            return '*' * (len(phone) - 4) + phone[-4:]

        result = re.sub(
            self.CONTENT_PATTERNS['phone'],
            mask_phone,
            result
        )

        # JSON key-value 中的敏感字段
        # password: "xxx" -> password: "***"
        result = re.sub(
            self.CONTENT_PATTERNS['password'],
            lambda m: m.group(0).split(':')[0] + ': "***"',
            result
        )

        result = re.sub(
            self.CONTENT_PATTERNS['token'],
            lambda m: m.group(0).split(':')[0] + ': "***"',
            result
        )

        result = re.sub(
            self.CONTENT_PATTERNS['api_key'],
            lambda m: m.group(0).split(':')[0] + ': "***"',
            result
        )

        return result

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        脱敏字典

        Args:
            data: 原始字典

        Returns:
            脱敏后的字典
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            # 检查字段名是否敏感
            if self.is_sensitive_field(key):
                # 敏感字段完全脱敏
                if isinstance(value, (str, int, float, bool)):
                    result[key] = "***" if self.preserve_length else self.mask_char * 3
                else:
                    result[key] = self._generate_hash(str(value))
            elif self.is_partial_sensitive_field(key):
                # 部分敏感字段使用内容检测脱敏
                result[key] = self.mask_value(value, key)
            else:
                # 其他字段也进行内容检测
                result[key] = self.mask_value(value, key)
        return result

    def sanitize_list(self, data: List[Any]) -> List[Any]:
        """
        脱敏列表

        Args:
            data: 原始列表

        Returns:
            脱敏后的列表
        """
        if not isinstance(data, list):
            return data

        return [self.mask_value(item) for item in data]

    def sanitize_request_body(self, body: Any) -> Any:
        """
        脱敏请求体

        Args:
            body: 请求体

        Returns:
            脱敏后的请求体
        """
        if isinstance(body, str):
            try:
                # 尝试解析 JSON
                parsed = json.loads(body)
                return self.sanitize_dict(parsed)
            except Exception:
                # 不是 JSON，直接检查敏感内容
                return self._mask_sensitive_content(body)
        else:
            return self.mask_value(body)

    def sanitize_response_body(self, body: Any) -> Any:
        """
        脱敏响应体

        Args:
            body: 响应体

        Returns:
            脱敏后的响应体
        """
        # 响应体中通常不包含敏感信息，但仍需要检查
        return self.sanitize_request_body(body)

    def _generate_hash(self, value: str) -> str:
        """
        生成哈希值（用于完全脱敏但仍保留可追溯性）

        Args:
            value: 原始值

        Returns:
            SHA256 哈希值的前16位
        """
        return sha256(value.encode()).hexdigest()[:16]


# 全局脱敏器实例
default_sanitizer = Sanitizer(mask_char='*', preserve_length=True)


def sanitize(data: Any, field_name: str = None) -> Any:
    """
    全局脱敏函数

    Args:
        data: 要脱敏的数据
        field_name: 字段名

    Returns:
        脱敏后的数据
    """
    return default_sanitizer.mask_value(data, field_name)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """脱敏字典"""
    return default_sanitizer.sanitize_dict(data)


def sanitize_request_body(body: Any) -> Any:
    """脱敏请求体"""
    return default_sanitizer.sanitize_request_body(body)


def sanitize_response_body(body: Any) -> Any:
    """脱敏响应体"""
    return default_sanitizer.sanitize_response_body(body)
