from django.contrib import admin

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from clublink.cms.models import ClubAdvertisement, CorpAdvertisement, ClubPage, CorpPage, ClubSnippet, CorpSnippet

class ClubPageResource(resources.ModelResource):

    class Meta:
        model = ClubPage

class CorpPageResource(resources.ModelResource):

    class Meta:
        model = CorpPage

class ClubSnippetResource(resources.ModelResource):

    class Meta:
        model = ClubSnippet

class CorpSnippetResource(resources.ModelResource):

    class Meta:
        model = CorpSnippet

class CorpSnippetAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CorpSnippetResource
    
    list_filter = (
        'locale',
        'slug'
    )

    list_display = (
        'page_name', 'slug', 'locale', 'content',
    )
admin.site.register(CorpSnippet, CorpSnippetAdmin)    

class ClubSnippetAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ClubSnippetResource

    list_filter = (
        'locale',
        'slug'
    )


    list_display = (
        'page_name', 'slug', 'locale', 'content',
    )    
admin.site.register(ClubSnippet, ClubSnippetAdmin)


class ClubPageAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ClubPageResource
    list_display = (
        'club',
        'name_en', 'name_fr',
        'slug',
    )    
    list_filter = ('club',)

admin.site.register(ClubPage, ClubPageAdmin)

class CorpPageAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CorpPageResource    
    list_display = (
        'site',
        'name_en', 'name_fr',
        'slug',
    )
    list_filter = ('site',)

admin.site.register(CorpPage, CorpPageAdmin)

class ClubAdvertisementAdmin(admin.ModelAdmin):
    list_display = ('name', 'club', 'sort',)
    list_editable = ('sort',)
    list_filter = ('club',)


admin.site.register(ClubAdvertisement, ClubAdvertisementAdmin)


class CorpAdvertisementAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'sort')
    list_editable = ('sort', 'site',)


admin.site.register(CorpAdvertisement, CorpAdvertisementAdmin)
