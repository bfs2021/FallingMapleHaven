from .base import *

import environ

env = environ.Env()
env.read_env(BASE_DIR / ".env")

DEBUG = False

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://fm_user:fm_dev_password@localhost:5432/fallingmaple"),
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ORIGINS", default=["http://localhost:5173"])
