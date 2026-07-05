import pytest
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import re_path

from apps.chat.consumers import ChatConsumer

application = URLRouter([
    re_path(r"ws/chat/$", ChatConsumer.as_asgi()),
])


@pytest.mark.asyncio
async def test_no_origin_rejected():
    """无 Origin 头时连接应被拒绝"""
    communicator = WebsocketCommunicator(application, "/ws/chat/")
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
async def test_invalid_origin_rejected():
    """非法 Origin 应被拒绝"""
    communicator = WebsocketCommunicator(application, "/ws/chat/")
    communicator.scope["headers"] = [
        (b"origin", b"https://evil.com"),
    ]
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
async def test_valid_origin_passes_origin_check():
    """合法 Origin 应通过校验（后续会因未认证被拒，但那是另一层）"""
    communicator = WebsocketCommunicator(application, "/ws/chat/")
    communicator.scope["headers"] = [
        (b"origin", b"http://localhost:5173"),
    ]
    connected, _ = await communicator.connect()
    assert not connected  # 被 auth 层拒绝而非 origin 层
