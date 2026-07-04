from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    nickname = models.CharField(max_length=50)
    real_name = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    first_name = None
    last_name = None

    def __str__(self) -> str:
        return self.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from apps.profiles.models import UserProfile

        UserProfile.objects.create(user=instance)
