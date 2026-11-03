from django.db import transaction
from django.utils import timezone

from missions.models import Accessory, PetAccessory, Mission, PetMission


# '산책 종료 시' 미션 진행도 갱신
def update_walk_missions(session):
    if session.pet_id is None or session.end_time is None:
        return

    walk_date = timezone.localdate(session.end_time)

    pet_missions = (
        PetMission.objects
        .select_related("mission", "pet")
        .filter(
            pet_id=session.pet_id,
            status=PetMission.Status.IN_PROGRESS,
            period_start__lte=walk_date,
            period_end__gte=walk_date,
        )
    )

    for pet_mission in pet_missions:
        mission = pet_mission.mission

        if mission.mission_type == Mission.MissionType.WALK_COUNT:
            pet_mission.current_count += 1

            if pet_mission.current_count >= mission.required_count:
                pet_mission.status = PetMission.Status.CLAIMABLE
                pet_mission.completed_at = timezone.now()

        elif mission.mission_type == Mission.MissionType.TOTAL_DISTANCE:
            walk_distance_meters = int(
                round(session.total_distance * 1000)
            )

            pet_mission.current_value += walk_distance_meters

            if pet_mission.current_value >= mission.goal:
                pet_mission.status = PetMission.Status.CLAIMABLE
                pet_mission.completed_at = timezone.now()

        elif mission.mission_type == Mission.MissionType.DISTINCT_WALK_DAYS:
            walk_days = (
                pet_mission.pet.walking_sessions
                .filter(
                    status="FINISHED",
                    end_time__date__gte=pet_mission.period_start,
                    end_time__date__lte=pet_mission.period_end,
                )
                .dates(
                    "end_time",
                    "day",
                )
                .count()
            )

            pet_mission.current_count = walk_days

            if pet_mission.current_count >= mission.required_count:
                pet_mission.status = PetMission.Status.CLAIMABLE
                pet_mission.completed_at = timezone.now()

        pet_mission.save()


@transaction.atomic
def claim_mission_reward(*, pet_id, pet_mission_id, user):
    try:
        pet_mission = (
            PetMission.objects
            .select_for_update()
            .select_related(
                "pet",
                "mission",
            )
            .get(
                id=pet_mission_id,
                pet_id=pet_id,
                pet__user=user,
            )
        )
    except PetMission.DoesNotExist:
        raise ValueError("존재하지 않거나 접근할 수 없는 미션입니다.")

    if pet_mission.status != PetMission.Status.CLAIMABLE:
        raise ValueError("아직 완료되지 않았거나 이미 보상을 받은 미션입니다.")

    if pet_mission.claimed_at is not None:
        raise ValueError("이미 보상을 받은 미션입니다.")

    pet = pet_mission.pet

    accessory = (
        Accessory.objects
        .exclude(
            pet_accessories__pet=pet,
        )
        .order_by("?")
        .first()
    )

    if accessory is None:
        raise ValueError("획득 가능한 액세서리가 없습니다.")

    PetAccessory.objects.create(
        pet=pet,
        accessory=accessory,
    )

    pet_mission.status = PetMission.Status.CLAIMED
    pet_mission.claimed_at = timezone.now()
    pet_mission.save(
        update_fields=[
            "status",
            "claimed_at",
        ]
    )

    return {
        "accessory": {
            "id": accessory.id,
            "name": accessory.name,
            "image": accessory.image.url,
            "category": accessory.category,
        },  
    }