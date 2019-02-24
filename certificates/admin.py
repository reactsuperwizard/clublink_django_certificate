from django.contrib import admin

from clublink.certificates.models import (
    Certificate,
    CertificateAd,
    CertificateGroup,
    CertificateGroupTemplate,
    CertificateType,
    DepartmentCertificateType,
    EmailSignature,
)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    pass


@admin.register(CertificateAd)
class CertificateAdAdmin(admin.ModelAdmin):
    pass


@admin.register(CertificateType)
class CertificateTypeAdmin(admin.ModelAdmin):
    list_filter = ('club',)
    search_fields = ('name', 'club__name', 'code',)
    list_display = ('name', 'club', 'code', 'staging_code', 'all_departments',
                    'template', 'category')

    def all_departments(self, obj):
        return ",\n".join(obj.departments.values_list('name', flat=True))


@admin.register(DepartmentCertificateType)
class DepartmentCertificateTypeAdmin(admin.ModelAdmin):
    list_filter = ('department', 'certificate_type',)
    list_display = ('department', 'certificate_type', 'guid',)
    list_editable = ('guid',)


@admin.register(CertificateGroup)
class CertificateGroupAdmin(admin.ModelAdmin):
    pass


@admin.register(CertificateGroupTemplate)
class CertificateGroupTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'group',
        'type',
        'club',
        'club_secondary',
        'expiry_date',
        'quantity',
        'power_cart',
        'note',
        'message'
    )
    list_filter = (
        'club',
        'club_secondary',
    )


@admin.register(EmailSignature)
class EmailSignatureAdmin(admin.ModelAdmin):
    pass
