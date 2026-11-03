from django.db import transaction

from notifications.services import send_push_notification

from .models import Pet, PetHistory


# 현재 레벨에서 다음 레벨까지 필요한 경험치 반환
def get_required_experience(level):
    return level * 100


# 반려견 경험치 증가 및 레벨업 처리
@transaction.atomic
def add_experience(pet, amount):
    if amount <= 0:
        return pet

    pet = (
        Pet.objects
        .select_for_update()
        .get(pk=pet.pk)
    )

    pet.experience += amount

    level_up_histories = []

    while (
        pet.experience
        >= get_required_experience(pet.level)
    ):
        required_experience = (
            get_required_experience(
                pet.level
            )
        )

        pet.experience -= required_experience

        before_level = pet.level
        pet.level += 1

        level_up_histories.append(
            PetHistory(
                pet=pet,
                before_level=before_level,
                after_level=pet.level,
            )
        )

    pet.save(
        update_fields=[
            "experience",
            "level",
            "updated_at",
        ]
    )

    if level_up_histories:
        PetHistory.objects.bulk_create(
            level_up_histories
        )

        pet_name = pet.name
        pet_id = pet.id
        final_level = pet.level
        user = pet.user

        transaction.on_commit(
            lambda: send_push_notification(
                user=user,
                notification_type="level_badge",
                title="레벨업",
                body=(
                    f"{pet_name}이(가) "
                    f"Lv.{final_level}이 되었어요!"
                ),
                data={
                    "type": "level_up",
                    "pet_id": pet_id,
                    "level": final_level,
                },
            )
        )

    return pet