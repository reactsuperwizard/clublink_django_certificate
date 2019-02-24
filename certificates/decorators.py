import functools

from django.conf import settings
from django.core.exceptions import PermissionDenied

from clublink.certificates.fences import office_vpn_fence


def ip_whitelist_only(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):

        enabled = getattr(
            settings, 
            'GIFT_CERTIFICATE_IP_WHITELIST_ENABLED', False
            )

        enabled = enabled and not request.user.is_superuser and not request.user.has_perm('certificates.can_login_off_premise')

        if enabled and not office_vpn_fence.allows(request):
            raise PermissionDenied()

        return view_func(request, *args, **kwargs)
    return wrapper
