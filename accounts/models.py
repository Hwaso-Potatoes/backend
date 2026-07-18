from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """email을 아이디로 쓰는 User 생성 규칙"""
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)          # 비밀번호는 반드시 암호화해서 저장
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None                                    # username 필드 제거
    email = models.EmailField("이메일", unique=True)
    nickname = models.CharField("닉네임", max_length=30, blank=True)

    USERNAME_FIELD = "email"                           # 로그인 ID로 email 사용
    REQUIRED_FIELDS = []                               # createsuperuser 시 email/password만

    objects = UserManager()

    def __str__(self):
        return self.email