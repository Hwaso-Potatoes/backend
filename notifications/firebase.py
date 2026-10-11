import json
import logging

import firebase_admin
from django.conf import settings
from firebase_admin import credentials


logger = logging.getLogger(__name__)


def get_firebase_app():
    try:
        return firebase_admin.get_app()

    except ValueError:
        pass

    service_account_json = (
        settings.FIREBASE_SERVICE_ACCOUNT_JSON
    )

    if not service_account_json:
        logger.warning(
            "Firebase service account가 설정되지 않았습니다."
        )
        return None

    credential_data = json.loads(
        service_account_json
    )

    credential = credentials.Certificate(
        credential_data
    )

    return firebase_admin.initialize_app(
        credential
    )