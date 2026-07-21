from django.db import models


class Accessory(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="accessories/")

    def __str__(self):
        return self.name


class PetAccessory(models.Model):
    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="pet_accessories",
    )
    accessory = models.ForeignKey(
        Accessory,
        on_delete=models.CASCADE,
        related_name="pet_accessories",
    )
    is_equipped = models.BooleanField(default=False)
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("pet", "accessory"),
                name="unique_pet_accessory",
            ),
        ]

    def __str__(self):
        return f"{self.pet.name} - {self.accessory.name}"