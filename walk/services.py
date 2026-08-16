MAX_WALK_EXPERIENCE = 50
EXPERIENCE_PER_KM = 10


def calculate_walk_experience(distance_km):
    if distance_km <= 0:
        return 0

    experience = int(distance_km * EXPERIENCE_PER_KM)

    return min(experience, MAX_WALK_EXPERIENCE)