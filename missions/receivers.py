from django.dispatch import receiver

from walk.signals import walk_classified
from missions.services.badge import check_location_badges


@receiver(walk_classified)
def handle_walk_classified(
    sender,
    session,
    user,
    pet,
    is_forest_walk,
    is_city_walk,
    is_new_area,
    **kwargs,
):
    if not pet:
        return

    check_location_badges(
        pet=pet,
        session=session,
    )