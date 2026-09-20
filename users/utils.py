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

def send_signup_verification_code(email, code, ttl_minutes):
    send_mail(
        subject="[산책앱] 회원가입 이메일 인증번호",
        message=(
            f"회원가입 인증번호는 [{code}] 입니다.\n"
            f"{ttl_minutes}분 안에 앱에 입력해 주세요.\n\n"
            "본인이 요청하지 않았다면 이 메일을 무시하세요."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

def send_password_reset_email(email, reset_link):
    send_mail(
        subject="[산책앱] 비밀번호 재설정",
        message=(
            "비밀번호 재설정을 요청하셨습니다.\n\n"
            "아래 링크를 눌러 새 비밀번호를 설정해 주세요.\n\n"
            f"{reset_link}\n\n"
            "본인이 요청하지 않았다면 이 메일을 무시해 주세요."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )