"""Shared admin building blocks: the Unfold look plus KamKarao's safety rules."""
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


class KKAdmin(ModelAdmin):
    """Every KamKarao admin page.

    - Warns before leaving a form with unsaved changes.
    - Only the owner (superuser) can delete. Helpers pause or block instead,
      so nothing is lost by a wrong tap on a phone.
    """

    warn_unsaved_form = True
    list_filter_submit = False
    list_per_page = 50

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


class KKTabularInline(TabularInline):
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


class KKStackedInline(StackedInline):
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


# Staff logins and roles in the same look ------------------------------------------
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class StaffUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ["username", "first_name", "roles", "is_superuser", "is_active", "last_login"]
    list_filter = ["is_superuser", "is_active", "groups"]

    @admin.display(description="Role")
    def roles(self, obj):
        if obj.is_superuser:
            return "Owner (everything)"
        return ", ".join(g.name for g in obj.groups.all()) or "—"


@admin.register(Group)
class StaffRoleAdmin(BaseGroupAdmin, ModelAdmin):
    pass
