from django.urls import path

from .views import (
    DeviceTokenRegisterView,
    DeviceTokenUnregisterView,
    NotificationPreferenceView,
)


urlpatterns = [
    path("settings/", NotificationPreferenceView.as_view(), name="notification-settings"),
    path("devices/", DeviceTokenRegisterView.as_view(), name="notification-device-register"),
    path("devices/unregister/", DeviceTokenUnregisterView.as_view(), name="notification-device-unregister"),
]