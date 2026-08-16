def add_experience(pet, amount):
    if amount <= 0:
        return pet

    pet.experience += amount

    while pet.experience >= pet.level * 100:
        required_experience = pet.level * 100

        pet.experience -= required_experience
        pet.level += 1

    pet.save(
        update_fields=[
            "experience",
            "level",
            "updated_at",
        ]
    )

    return pet