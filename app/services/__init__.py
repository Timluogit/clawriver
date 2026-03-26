"""服务模块 - 延迟导入避免内存溢出"""

def __getattr__(name):
    """延迟导入重型服务模块"""
    if name in ("signature_service", "DigitalSignatureService"):
        from app.services.digital_signature_service import signature_service, DigitalSignatureService
        return locals()[name]
    if name in ("key_management_service", "KeyManagementService"):
        from app.services.key_management_service import key_management_service, KeyManagementService
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
