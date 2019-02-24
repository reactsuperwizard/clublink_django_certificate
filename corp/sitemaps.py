from django.contrib.sites.models import Site
from django.contrib.sitemaps import Sitemap
from clublink.cms.models import CorpPage
from clublink.corp.models import News

class CorpPageSitemap(Sitemap):
    changefreq = 'daily'
    def items(self):
        site = Site.objects.get_current()
        return CorpPage.objects.filter(
            site=site,
            should_redirect=False
            )

class CorpNewsSitemap(Sitemap):
    changefreq = 'daily'   
    def items(self):
        return News.objects.filter(show_on_corp_site=True)