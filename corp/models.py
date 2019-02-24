from django.conf import settings
from django.db import models
from django.utils.translation import get_language
from django.urls import reverse

from urllib.parse import urlparse

from clublink.base.utils import RandomizedUploadPath
from clublink.clubs.models import Club

class News(models.Model):
    publish_date = models.DateField()
    headline_en = models.CharField(max_length=255)
    headline_fr = models.CharField(max_length=255, null=True, blank=True)
    slug = models.CharField(max_length=128, unique=True)
    summary_en = models.CharField(max_length=255)
    summary_fr = models.CharField(max_length=255, null=True, blank=True)
    content_en = models.TextField()
    content_fr = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to=RandomizedUploadPath('corp_news'))
    clubs = models.ManyToManyField(Club, related_name='news')
    show_on_corp_site = models.BooleanField(default=True)
    show_on_club_site = models.BooleanField(default=True)

    class Meta:
        ordering = ('-publish_date',)

    def get_photo(self):
        path = urlparse(self.photo.url).path
        return (
            settings.S3_BASE + '/filters:quality(80):format(jpeg)' + path)

    @property
    def fully_french(self):
        return (self.summary_fr and self.headline_fr and self.content_fr)

    @property
    def headline(self):
        locale = get_language()
        localized = getattr(self, 'headline_{}'.format(locale), self.headline_en)
        return localized or self.headline_en

    @property
    def summary(self):
        locale = get_language()
        localized = getattr(self, 'summary_{}'.format(locale), self.summary_en)
        return localized or self.summary_en

    @property
    def content(self):
        locale = get_language()
        localized = getattr(self, 'content_{}'.format(locale), self.content_en)
        return localized or self.content_en

    def get_absolute_url(self):
        return reverse('news-item', kwargs={'slug': self.slug})