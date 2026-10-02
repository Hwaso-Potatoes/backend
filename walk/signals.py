import logging

from django.dispatch import Signal
from django.utils import timezone

logger = logging.getLogger(__name__)

# 산책이 정상 종료되고 DB에 커밋된 뒤 발송됨.
# 받는 쪽 kwargs: session, user, pet, walk_date(로컬 날짜), is_first_walk_today(bool)
walk_finished = Signal()


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
    for receiver, result in results:
        if isinstance(result, Exception):
            logger.error("walk_finished 처리 실패 (%s): %r", receiver, result, exc_info=result)
