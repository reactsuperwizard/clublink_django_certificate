from django.contrib.sites.models import Site
from django.contrib.sitemaps import Sitemap
from clublink.cms.models import ClubPage

class ClubPageSitemap(Sitemap):
    changefreq = 'daily'
    def items(self):
        site = Site.objects.get_current()
        return ClubPage.objects.filter(
            site=site,
            should_redirect=False
            )