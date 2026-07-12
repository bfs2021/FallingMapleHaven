import os
import uuid

from django.conf import settings
from PIL import Image
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    UserRegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.common.utils import api_response

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return api_response(data={"csrfToken": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return api_response(
            data=UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return api_response(
                code=40003,
                message="用户名或密码错误",
                data=None,
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        return api_response(data=UserSerializer(user, context={"request": request}).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return api_response()


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return api_response(data=UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(data=UserSerializer(user, context={"request": request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return api_response(
                code=40001,
                message="请提供旧密码和新密码",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(old_password):
            return api_response(
                code=40003,
                message="旧密码不正确",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return api_response(
                code=40001,
                message="新密码长度不能少于8位",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not any(c.isalpha() for c in new_password):
            return api_response(
                code=40001,
                message="新密码必须包含字母",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not any(c.isdigit() for c in new_password):
            return api_response(
                code=40001,
                message="新密码必须包含数字",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in new_password):
            return api_response(
                code=40001,
                message="新密码必须包含至少一个特殊字符",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save()
        return api_response()


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("avatar")
        if not file:
            return api_response(
                code=40001,
                message="请上传头像文件",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return api_response(
                code=40001,
                message="仅支持 jpg/png/gif/webp 格式",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)
            img = Image.open(file)
            img.load()
            file.seek(0)
        except Exception:
            return api_response(
                code=40001,
                message="文件不是有效的图片",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        safe_filename = f"{uuid.uuid4().hex}{ext}"
        request.user.avatar.save(safe_filename, file, save=True)
        return api_response(
            data={"avatar_url": request.user.avatar.url if request.user.avatar else None}
        )


class CoverUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("cover_image")
        if not file:
            return api_response(
                code=40001,
                message="请上传封面文件",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return api_response(
                code=40001,
                message="仅支持 jpg/png/gif/webp 格式",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)
            img = Image.open(file)
            img.load()
            file.seek(0)
        except Exception:
            return api_response(
                code=40001,
                message="文件不是有效的图片",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        safe_filename = f"{uuid.uuid4().hex}{ext}"
        request.user.cover_image.save(safe_filename, file, save=True)
        return api_response(
            data={
                "cover_url": (
                    request.user.cover_image.url if request.user.cover_image else None
                )
            }
        )
