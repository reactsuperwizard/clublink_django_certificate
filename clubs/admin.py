from django.contrib import admin

from clublink.clubs.models import Club, Department, Region


admin.site.site_title = 'ClubLink'
admin.site.site_header = 'ClubLink Admin'


class ClubAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
        'tier',
        'region',
        'site',
    )
    list_editable = (
        'tier',
        'region',
        'site',
    )

    filter_horizontal = ('admins',)
    list_filter = ('site', 'region', 'tier',)


admin.site.register(Club, ClubAdmin)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'hidden', 'number',)
    list_editable = ('hidden',)


admin.site.register(Department, DepartmentAdmin)


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'site',)
    list_editable = ('site',)


admin.site.register(Region, RegionAdmin)
