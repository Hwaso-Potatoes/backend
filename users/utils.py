from django.conf import settings
from django.core.mail import send_mail


def send_verification_code(email, code, ttl_minutes):
    send_mail(
        subject="[산책앱] 이메일 변경 인증번호",
        message=(
            f"인증번호는 [{code}] 입니다.\n"
            f"{ttl_minutes}분 안에 앱에 입력해 주세요.\n\n"
            "본인이 요청하지 않았다면 이 메일을 무시하세요."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )