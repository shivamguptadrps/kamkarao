"""
Create the "Helper" staff role: a person who onboards workers and handles
calls in Banda, without access to money, settings or deleting anything.

    python manage.py setup_roles

Safe to run again. Then in the admin: Staff logins → Add, tick "Staff status",
and choose the Helper role.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

HELPER = {
    "providers": {"provider": ["view", "add", "change"], "joinrequest": ["view", "change"]},
    "leads": {"lead": ["view", "change"], "rating": ["view", "change"],
              "complaint": ["view", "change"], "workrequest": ["view", "add", "change"]},
    "accounts": {"customer": ["view"]},
    "ads": {"banner": ["view"]},
    "core": {"category": ["view"], "area": ["view"]},
}


class Command(BaseCommand):
    help = "Create or update the Helper staff role."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="Helper")
        perms = []
        for app, models in HELPER.items():
            for model, actions in models.items():
                for act in actions:
                    perms.append(Permission.objects.get(content_type__app_label=app,
                                                        codename=f"{act}_{model}"))
        group.permissions.set(perms)
        self.stdout.write(self.style.SUCCESS(f"Helper role ready ({len(perms)} permissions)."))
