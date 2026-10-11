from django.contrib import admin
from django.utils import timezone

from .models import NotificationCampaign
from .services import send_marketing_campaign


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "created_at",
        "sent_at",
    )

    readonly_fields = (
        "created_at",
        "sent_at",
    )

    actions = [
        "send_campaigns",
    ]

    @admin.action(
        description="선택한 이벤트 알림 전송"
    )
    def send_campaigns(self, request, queryset):
        campaign_count = 0
        success_count = 0

        for campaign in queryset:
            # 이미 전송한 캠페인은 중복 전송하지 않음
            if campaign.sent_at:
                continue

            sent_count = send_marketing_campaign(
                campaign
            )

            # 실제 전송된 기기가 있을 때만 전송 완료 처리
            if sent_count > 0:
                campaign.sent_at = timezone.now()

                campaign.save(
                    update_fields=[
                        "sent_at",
                    ]
                )

                campaign_count += 1
                success_count += sent_count

        self.message_user(
            request,
            (
                f"{campaign_count}개의 캠페인을 "
                f"{success_count}개의 기기에 전송했습니다."
            ),
        )