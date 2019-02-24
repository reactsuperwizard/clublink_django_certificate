import functools

from django.http import Http404


def member_portal_only(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.member_portal:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper
