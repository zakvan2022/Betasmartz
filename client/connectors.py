from django.db.models.signals import post_save
from django.dispatch import receiver

from client.models import Client


@receiver(post_save, sender=Client)
def client__post_save__group(sender, instance, created, **kwargs):
    """
    Experimental
    Add user to Client group on profile creation
    (maybe it could be done from other end)
    """
    if created and isinstance(instance, Client):
        user = instance.user
        user.groups_add(user.GROUP_CLIENT)
