from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'clublink.base'
    label = 'base'

    def ready(self):
        super().ready()
        import clublink.base.templatetags  # noqa
