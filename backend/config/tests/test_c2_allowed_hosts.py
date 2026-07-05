import os

import environ


def test_allowed_hosts_default_empty_is_dangerous():
    """默认 default=[] 时，env 未设置 ALLOWED_HOSTS 会静默返回 []（Bug 复现）"""
    env = environ.Env()
    env_var_name = "ALLOWED_HOSTS_TEST_EMPTY"
    os.environ.pop(env_var_name, None)
    result = env.list(env_var_name, default=[])
    assert result == []


def test_allowed_hosts_without_default_raises_error():
    """去掉 default=[] 后，env 未设置 ALLOWED_HOSTS 应抛出 ImproperlyConfigured"""
    env = environ.Env()
    env_var_name = "ALLOWED_HOSTS_TEST_MISSING"
    os.environ.pop(env_var_name, None)
    try:
        env.list(env_var_name)
        assert False, "应该抛出异常但没有"
    except Exception as e:
        from django.core.exceptions import ImproperlyConfigured
        assert isinstance(e, ImproperlyConfigured)
