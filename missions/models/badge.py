from django.db import models


class Badge(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="badges/")

    def __str__(self):
        return self.name


class PetBadge(models.Model):
    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="pet_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="pet_badges",
    )
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("pet", "badge"),
                name="unique_pet_badge",
            ),
        ]

    def __str__(self):
        return f"{self.pet.name} - {self.badge.name}"