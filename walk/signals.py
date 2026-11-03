import logging

from django.dispatch import Signal
from django.utils import timezone

logger = logging.getLogger(__name__)

# 산책이 정상 종료되고 DB에 커밋된 뒤 발송됨.
# 받는 쪽 kwargs: session, user, pet, walk_date(로컬 날짜), is_first_walk_today(bool)
walk_finished = Signal()

# 산책 위치 유형 판정이 끝난 뒤 발송됨 (산책 종료 후 몇 초 뒤, 백그라운드).
# 받는 쪽 kwargs: session, user, pet, is_forest_walk, is_city_walk, is_new_area
#   각 값은 True / False / None(지도 데이터를 못 구해 판정 불가)
walk_classified = Signal()


def _log_failures(signal_name, results):
    for receiver, result in results:
        if isinstance(result, Exception):
            logger.error("%s 처리 실패 (%s): %r", signal_name, receiver, result, exc_info=result)


def send_walk_finished(session, is_first_walk_today):
    """받는 쪽에서 에러가 나도 산책 종료에 영향 없도록 send_robust 사용"""
    results = walk_finished.send_robust(
        sender=session.__class__,
        session=session,
        user=session.user,
        pet=session.pet,
        walk_date=timezone.localdate(session.end_time),
        is_first_walk_today=is_first_walk_today,
    )
    _log_failures('walk_finished', results)

    # 숲/도시/새로운 지역 판정 (외부 지도 조회가 있어 백그라운드)
    from .geo import classify_walk_in_background
    classify_walk_in_background(session.id)


def send_walk_classified(session_id, result):
    from .models import WalkingSession

    session = WalkingSession.objects.select_related('user', 'pet').get(id=session_id)
    results = walk_classified.send_robust(
        sender=WalkingSession,
        session=session,
        user=session.user,
        pet=session.pet,
        **result,
    )
    _log_failures('walk_classified', results)
