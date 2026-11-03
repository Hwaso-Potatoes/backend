from django.dispatch import receiver

from walk.signals import walk_finished

from .services import process_walk_attendance


@receiver(walk_finished)
def handle_walk_finished(
    sender,
    session,
    user,
    pet,
    walk_date,
    is_first_walk_today,
    **kwargs,
):
    if not pet:
        return

    process_walk_attendance(
        user=user,
        pet=pet,
        walk_date=walk_date,
    )