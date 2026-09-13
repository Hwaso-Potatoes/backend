import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        
        email = self.normalize_email(email)

        user = self.model(
            email=email, 
            **extra_fields
        )

        user.set_password(password)         
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(
            email, 
            password, 
            **extra_fields
        )

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("슈퍼유저는 is_staff=True여야 합니다.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("슈퍼유저는 is_superuser=True여야 합니다.")
        
        return self._create_user(
            email, 
            password, 
            **extra_fields
        )


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=8, unique=True, null=True, blank=True)  # 가입 후 프로필에서 설정
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []         

    objects = UserManager()

    def __str__(self):
        return self.email

class EmailVerification(models.Model):
    """이메일 인증번호 (이메일 변경 등에 사용)"""

    class Purpose(models.TextChoices):
        EMAIL_CHANGE = "email_change", "이메일 변경"

    CODE_TTL_MINUTES = 5           # 코드 유효시간
    RESEND_COOLDOWN_SECONDS = 60   # 재발송 쿨다운
    MAX_ATTEMPTS = 5               # 입력 최대 시도 횟수

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    email = models.EmailField(db_index=True)      # 인증 대상 = 새 이메일
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)  # 평문 저장 X
    attempt_count = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["email", "purpose", "-created_at"])]

    def __str__(self):
        return f"{self.email} ({self.purpose})"

    @classmethod
    def issue(cls, *, user, email, purpose):
        """새 인증번호 발급 → (객체, 평문코드)"""
        cls.objects.filter(user=user, purpose=purpose, verified_at__isnull=True).delete()

        code = f"{secrets.randbelow(10**6):06d}"
        obj = cls.objects.create(
            user=user,
            email=email,
            purpose=purpose,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=cls.CODE_TTL_MINUTES),
        )
        return obj, code

    @classmethod
    def cooldown_remaining(cls, *, user, purpose):
        """재발송까지 남은 초 (0이면 발송 가능)"""
        last = cls.objects.filter(user=user, purpose=purpose).order_by("-created_at").first()
        if not last:
            return 0
        elapsed = (timezone.now() - last.created_at).total_seconds()
        return max(int(cls.RESEND_COOLDOWN_SECONDS - elapsed), 0)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def verify(self, raw_code):
        if not check_password(raw_code, self.code_hash):
            self.attempt_count += 1
            self.save(update_fields=["attempt_count"])
            return False

        self.verified_at = timezone.now()
        self.save(update_fields=["verified_at"])
        return True