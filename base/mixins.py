################
# Model mixins
################

from django.db import models

class UpdatedCreatedMixin:
    '''
    Mixin that stamps when the model was updated
    '''
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    