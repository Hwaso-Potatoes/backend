from django.conf import settings
from django.db import models

PERSONALITY_CHOICES = [    
    ("energy", "에너지형"),
    ("social", "사회성형"),
    ("timid", "겁쟁이형"),
    ("curious", "호기심형"),
    ("relaxed", "느긋형"),
    ("calm", "얌전형"),
]

class Pet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,       
        on_delete=models.CASCADE,      
        related_name="pets",
    )
    name = models.CharField("이름", max_length=30)
    breed = models.CharField("견종", max_length=50, blank=True)
    birth_date = models.DateField("생년월일", null=True, blank=True)
    profile_image = models.ImageField("프로필 사진", upload_to="pets/", null=True, blank=True)
    personalities = models.JSONField("성격", default=list, blank=True) 
    level = models.PositiveIntegerField("레벨", default=1)
    experience = models.PositiveIntegerField("경험치", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PetHistory(models.Model):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name="level_up_histories",
    )
    before_level = models.PositiveIntegerField()
    after_level = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]