from django.contrib import admin

from clublink.users.models import User, Address

from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field


class UserResource(resources.ModelResource):
    assigned_departments = Field()
    assigned_clubs = Field()
    can_access_cms = Field()
    can_impersonate_user = Field()

    def dehydrate_assigned_departments(self, user):
        return ', '.join(user.departments.values_list('name', flat=True))

    def dehydrate_assigned_clubs(self, user):
        return ', '.join(user.clubs.values_list('name', flat=True))

    ######################################################
    '''
    NOTE: THIS IS NOT ACTUALLY PERMISSIONS.
    This is what Influence Marketing sells as "permissions"
    '''

    def dehydrate_can_access_cms(self, user):
        if hasattr(user, 'permissions'):
            return user.permissions.can_access_cms
        else:
            return False

    def dehydrate_can_impersonate_user(self, user):
        if hasattr(user, 'permissions'):
            return user.permissions.can_impersonate_user
        else:
            return False

    ######################################################


    class Meta:
        model = User
        fields = (
            'id',
            'membership_number',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'status',
            'preferred_language',
            'home_club',
            'assigned_departments',
            'assigned_clubs',
            'can_access_cms',
            'can_impersonate_user'
            )
        export_order = fields


class AddressInline(admin.TabularInline):
    model = Address

class UserAdmin(ExportMixin, admin.ModelAdmin):

    resource_class = UserResource

    inlines = [
        AddressInline
    ]

    list_display = (
        'username',
        'is_superuser',
        'status',
        'option_club',
        'first_name',
        'last_name',
        'email',
        'membership_number',
        'employee_number',
    )
    search_fields = (
        'username', 
        'first_name', 
        'last_name', 
        'email', 
        'membership_number', 
        'employee_number',
        )
    list_editable = ('employee_number',)
    list_filter = (
        'is_staff',
        'is_superuser',
        'status',
        'permissions__can_impersonate_user',
        'permissions__can_access_cms',
        'departments',
        'clubs',
    )

    def get_export_queryset(self, request):
        qs = super(UserAdmin, self).get_export_queryset(request)
        return qs.select_related('permissions').prefetch_related('departments', 'clubs')


admin.site.register(User, UserAdmin)
