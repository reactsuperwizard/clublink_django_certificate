from django.conf import settings
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string


def get_storage_class(import_path=None):
    return import_string(import_path or settings.ASSETS_FILE_STORAGE)


class AssetsStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class()(location=settings.ASSETS_ROOT,
                                            base_url=settings.ASSETS_URL)


assets_storage = AssetsStorage()
