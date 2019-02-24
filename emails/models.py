from django.db import models
from clublink.base.mixins import UpdatedCreatedMixin

'''
TODO - Define a Template model in which there is a HTML template with blocked 
out variables that are parsed and saved into the model as a JSON field.

class Template:
    file = FielField()
    context = JSONField()

    def save(...):
        # parse field for anything with {{ }}
        # save that as a key if it doesn't already exist in context
        ... on front end, this will be called for dynamic data entering too
'''

class Campaign(UpdatedCreatedMixin, models.Model):
    """Model definition for Campaign."""

    # TODO: Define fields here

    class Meta:
        """Meta definition for Campaign."""

        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'

    def __unicode__(self):
        """Unicode representation of Campaign."""
        pass

    def save(self):
        """Save method for Campaign."""
        pass

    def get_absolute_url(self):
        """Return absolute url for Campaign."""
        return ('')

    # TODO: Define custom methods here
