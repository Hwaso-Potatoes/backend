from django.db import transaction

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

    while (pet.experience>= get_required_experience(pet.level)):
        required_experience = (
            get_required_experience(pet.level)
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

    return pet