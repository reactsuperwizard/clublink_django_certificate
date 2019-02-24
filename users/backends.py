class ForcedAuthenticationBackend(object):
    """A custom authentication backend to force a login."""
    def authenticate(self, force_user=None):
        return force_user
