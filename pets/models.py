from django.db import models

from django.conf import settings
from django.db import models


class Dog(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,       
        on_delete=models.CASCADE,      
        related_name="dogs",
    )
    name = models.CharField("이름", max_length=30)
    breed = models.CharField("견종", max_length=50, blank=True)
    birth_date = models.DateField("생년월일", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
