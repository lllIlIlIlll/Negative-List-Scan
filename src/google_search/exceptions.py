"""google_search.exceptions — 异常类层次定义（v2 简化版）"""


class GoogleSearchError(Exception):
    """基础异常，所有本项目异常的父类"""
    pass


class UserActionRequiredError(GoogleSearchError):
    """需要用户手动介入（首次登录、reCAPTCHA 超时等）"""
    pass


class RecoverableError(GoogleSearchError):
    """可恢复的临时错误（网络抖动、超时）"""
    pass


class FatalError(GoogleSearchError):
    """不可恢复错误（profile 锁定、Chrome 未安装、配置错误）"""
    pass
