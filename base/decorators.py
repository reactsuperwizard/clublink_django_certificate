import functools

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def vpn_protected(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        enabled = getattr(settings, 'VPN_PROTECTED_VIEWS_ENABLED', True)
        vpn_ip = getattr(settings, 'VPN_IP_ADDRESS', '0.0.0.0')

        if enabled and request.META.get('REMOTE_ADDR') != vpn_ip:
            raise PermissionDenied()

        return view_func(request, *args, **kwargs)
    return wrapper


def login_required(function):
    @functools.wraps(function)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            redirect_to = '{}?{}={}'.format(reverse('login'), REDIRECT_FIELD_NAME, request.path)
            return redirect(redirect_to)
        return function(request, *args, **kwargs)
    return wrapped_view


def staff_required(function):
    @functools.wraps(function)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            redirect_to = '{}?{}={}'.format(reverse('login'), REDIRECT_FIELD_NAME, request.path)
            return redirect(redirect_to)
        elif not request.user.is_staff:
            raise PermissionDenied()
        return function(request, *args, **kwargs)
    return wrapped_view


def short_circuit_middlewares(view_func):
    """
    Marks a view function as wanting to short circuit middlewares.
    """
    # Based on Django's csrf_exempt

    # We could just do view_func.short_circuit_middlewares = True, but
    # decorators are nicer if they don't have side-effects, so we return
    # a new function.
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)
    wrapped_view.short_circuit_middlewares = True
    return functools.wraps(view_func)(wrapped_view)
