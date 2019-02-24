from dirtyfields import DirtyFieldsMixin
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _

from clublink.base.utils import optimize_jpeg, RandomizedUploadPath
from clublink.clubs.models import Club
from clublink.cms.storages import assets_storage

from urllib.parse import urlparse
from datetime import datetime 
from clublink.users.models import User

class BasePage(models.Model):
    SNIPPET_CLASS = None

    name_en = models.CharField(max_length=255)
    name_fr = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=64)
    full_path = models.CharField(max_length=255, null=True)
    parent = models.ForeignKey(
        'self',
        related_name='children',
        null=True,
        on_delete=models.CASCADE
        )
    is_locked = models.BooleanField(default=False)
    sort = models.IntegerField(default=0)
    show_in_main_menu = models.BooleanField(default=True)
    list_in_main_menu_subnav = models.BooleanField(default=False)
    name_in_main_menu_subnav_en = models.CharField(max_length=255, blank=True)
    name_in_main_menu_subnav_fr = models.CharField(max_length=255, blank=True)
    show_page_nav = models.BooleanField(default=True)
    list_in_child_page_nav = models.BooleanField(default=False)
    name_in_child_page_nav_en = models.CharField(max_length=255, blank=True)
    name_in_child_page_nav_fr = models.CharField(max_length=255, blank=True)
    should_redirect = models.BooleanField(default=False)
    internal_redirect = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.SET_NULL
        )
    external_redirect = models.URLField(blank=True)
    opens_in_new_window = models.BooleanField(default=False)
    site = models.ForeignKey(
        Site,
        blank=True,
        null=True,
        related_name='%(class)s',
        on_delete=models.PROTECT
        )
    hidden_bucket = models.NullBooleanField(
        default=False,
        null=True,
        help_text='Do not show as a bucket'
        )
    facebook_pixel_id = models.CharField(
        max_length=50,
        blank=True,
        null=True
        )

    class Meta:
        abstract = True

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.full_path)

    def seo_title(self, locale='en'):
        try:
            return self.snippets.get(slug='title', locale=locale)
        except:
            return ''

    def seo_description(self, locale='en'):
        try:
            return self.snippets.get(slug='description', locale=locale)
        except:
            return ''

    @property
    def depth(self, starting=0):
        if not self.parent:
            return 0
        else:
            obj = self
            while(obj.parent != None):
                # print('WE ARE INSIDE')
                # print(obj.id)
                # print(starting)
                starting += 1
                obj = obj.parent
            return starting

    @property
    def name(self):
        locale = get_language()
        localized = getattr(self, 'name_{}'.format(locale), self.name_en)
        return localized or self.name_en

    @property
    def name_in_main_menu_subnav(self):
        locale = get_language()
        localized = getattr(self, 'name_in_main_menu_subnav_{}'.format(locale),
                            self.name_in_main_menu_subnav_en)
        return localized or self.name_in_main_menu_subnav_en

    @property
    def name_in_child_page_nav(self):
        locale = get_language()
        localized = getattr(self, 'name_in_child_page_nav_{}'.format(locale),
                            self.name_in_child_page_nav_en)
        return localized or self.name_in_child_page_nav_en

    @property
    def redirects_externally(self):
        return self.should_redirect and self.external_redirect and not self.internal_redirect

    @property
    def url(self):
        if self.should_redirect:
            if self.internal_redirect:
                return self.internal_redirect.url
            elif self.external_redirect:
                return self.external_redirect

        if not self.full_path:
            return '/'
        return '/{}/'.format(self.full_path)

    @property
    def target(self):
        if self.should_redirect:
            if self.internal_redirect:
                return self.internal_redirect.target
            elif self.external_redirect:
                return '_blank'
        elif self.opens_in_new_window:
            return '_blank'
        return None

    def get_snippet(self, slug, locale=None, fallback=True, default='', inhereted=False):
        if locale is None:
            locale = get_language()

        try:
            return self.snippets.get(slug=slug, locale=locale)
        except models.ObjectDoesNotExist:
            if fallback and not locale == settings.LANGUAGE_CODE:
                try:
                    return self.snippets.get(slug=slug, locale=settings.LANGUAGE_CODE)
                except models.ObjectDoesNotExist:
                    pass

            if self.parent and inhereted:
                return self.parent.get_snippet(
                    slug, locale=locale, fallback=fallback, default=default, inhereted=inhereted)

        return default

    def get_image(self, slug, locale=None, fallback=True, default='', inhereted=False, skip_corp=False):
        if locale is None:
            locale = get_language()

        # Because BGC wants to use a corp image, for no reason...
        # if getattr(self, 'use_corp_styles', False) or (hasattr(self, 'club') and self.club.use_corp_styles and not skip_corp):
        #     currentpage = self.site.corppage.filter(full_path=self.full_path)
        #     if not currentpage.count():
        #         currentpage = self
        #     else:
        #         currentpage = currentpage.first()
        # else:
        currentpage = self

        try:
            cpi = currentpage.images.get(slug=slug, locale=locale)
            return cpi
        except models.ObjectDoesNotExist:
            if fallback and not locale == settings.LANGUAGE_CODE:
                try:
                    return currentpage.images.get(slug=slug, locale=settings.LANGUAGE_CODE)
                except models.ObjectDoesNotExist:
                    pass

            if currentpage.parent and inhereted:
                return currentpage.parent.get_image(
                    slug, locale=locale, fallback=fallback, default=default, inhereted=inhereted)

        return default

    def snippet_class(self):
        raise NotImplementedError()

    def set_snippet(self, slug, locale, value):
        snippet, _ = self.snippet_class().objects.get_or_create(
            page=self, locale=locale, slug=slug)
        snippet.content = value
        snippet.save()

    def save(self, *args, **kwargs):
        self.full_path = '{}/'.format(self.parent.full_path) if self.parent else ''
        if self.slug:
            self.full_path += self.slug

        if hasattr(self, 'club'):
            self.site = self.club.site

        super().save(*args, **kwargs)

        for child in self.children.all():
            child.save()


class ClubPage(BasePage):
    EVERYONE_VISIBILITY = 0
    MEMBERS_ONLY_VISIBILITY = 1
    NON_MEMBERS_ONLY_VISIBILITY = 2
    NOBODY_VISIBILITY = 3

    VISIBILITY_CHOICES = (
        (EVERYONE_VISIBILITY, _('Everyone')),
        (MEMBERS_ONLY_VISIBILITY, _('Members Only')),
        (NON_MEMBERS_ONLY_VISIBILITY, _('Non-Members Only')),
        (NOBODY_VISIBILITY, _('Nobody')),
    )
    club = models.ForeignKey(
        Club,
        related_name='pages',
        null=True,
        on_delete=models.PROTECT
        )
    visibility = models.IntegerField(choices=VISIBILITY_CHOICES, default=EVERYONE_VISIBILITY)
    show_address_bar = models.BooleanField(default=True)
    alias = models.ForeignKey(
        'self',
        related_name='aliases',
        null=True,
        on_delete=models.CASCADE
        )

    use_corp_styles = models.BooleanField(
        default=False,
        help_text='This is meant to use the same background as your corp-page equivalent based on the path'
        )

    class Meta:
        ordering = ('sort',)
        unique_together = (('club', 'full_path'),)

    def get_absolute_url(self):
        return self.url
        # from django.core.urlresolvers import reverse
        # return reverse('', kwargs={'pk': self.pk})

    @property
    def visiblity_type(self):
        map = {k:v.__str__() for k,v in ClubPage.VISIBILITY_CHOICES}
        return map[self.visibility].lower()

    @property
    def icon_class(self):
        '''For FontAwesome'''
        map = {0: 'globe', 1: 'id-card-o', 2: 'low-vision', 3: 'user-secret'}
        return map[self.visibility]

    def snippet_class(self):
        return ClubSnippet

    def get_snippet(self, *args, **kwargs):
        ignore_alias = kwargs.pop('ignore_alias', False)
        if self.alias and not ignore_alias:
            return self.alias.get_snippet(*args, **kwargs)
        else:
            return super().get_snippet(*args, **kwargs)

    def get_image(self, *args, **kwargs):
        ignore_alias = kwargs.pop('ignore_alias', False)
        if self.alias and not ignore_alias:
            return self.alias.get_image(*args, **kwargs)
        else:
            return super().get_image(*args, **kwargs)

    def set_snippet(self, *args, **kwargs):
        if self.alias:
            return self.alias.set_snippet(*args, **kwargs)
        else:
            return super().set_snippet(*args, **kwargs)

    def is_visible(self, request):

        if self.visibility == ClubPage.EVERYONE_VISIBILITY:
            return True
        elif self.visibility == ClubPage.MEMBERS_ONLY_VISIBILITY and request.member_portal:
            return True
        elif self.visibility == ClubPage.NON_MEMBERS_ONLY_VISIBILITY and not request.member_portal:
            return True
        return False


class CorpPage(BasePage):
    class Meta:
        ordering = ('sort',)
        unique_together = (('full_path'),)

    def snippet_class(self):
        return CorpSnippet

    def get_absolute_url(self):
        return self.url
        # from django.core.urlresolvers import reverse
        # return reverse('', kwargs={'pk': self.pk})


class BaseSnippet(models.Model):
    locale = models.CharField(max_length=2, choices=settings.LANGUAGES)
    slug = models.CharField(max_length=64)
    content = models.TextField()

    class Meta:
        abstract = True

    def page_name(self):
        return self.page.name

    def __str__(self):
        if '\u200b' in self.content:
            self.content = self.content.replace('\u200b', '')
            self.save()
        return self.content

    def __bool__(self):
        return bool(self.content)


class ClubSnippet(BaseSnippet):
    page = models.ForeignKey(
        ClubPage,
        related_name='snippets',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class CorpSnippet(BaseSnippet):
    page = models.ForeignKey(
        CorpPage,
        related_name='snippets',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class BaseImage(DirtyFieldsMixin, models.Model):
    locale = models.CharField(max_length=2, choices=settings.LANGUAGES,
                              default=settings.LANGUAGE_CODE)
    slug = models.CharField(max_length=64)
    image = models.ImageField(upload_to=RandomizedUploadPath('page'), null=True)

    class Meta:
        abstract = True

    @property
    def optimized_url(self):
        path = urlparse(self.image.url).path
        return (settings.S3_BASE + '/filters:quality(80):format(jpeg)' + path)

    def __str__(self):
        try:
            path = urlparse(self.image.url).path
            return (settings.S3_BASE + '/filters:quality(80):format(jpeg)' + path)
        except:
            return self.image.url if self.image else ''

    def __bool__(self):
        return self.image is not None

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        super().save(*args, **kwargs)

        if 'image' in dirty_fields and self.image:
            optimize_jpeg(self.image)


class ClubImage(BaseImage):
    page = models.ForeignKey(
        ClubPage,
        related_name='images',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class CorpImage(BaseImage):
    page = models.ForeignKey(
        CorpPage,
        related_name='images',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class BaseImageSet(models.Model):
    locale = models.CharField(max_length=2, choices=settings.LANGUAGES,
                              default=settings.LANGUAGE_CODE)
    slug = models.CharField(max_length=64)

    class Meta:
        abstract = True


class ClubImageSet(BaseImageSet):
    page = models.ForeignKey(
        ClubPage,
        related_name='image_sets',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class CorpImageSet(BaseImageSet):
    page = models.ForeignKey(
        CorpPage,
        related_name='image_sets',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'locale', 'slug'),)


class BaseImageSetImage(DirtyFieldsMixin, models.Model):
    sort = models.IntegerField(default=0)
    image = models.ImageField(upload_to=RandomizedUploadPath('page_image_set'), null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.image.url if self.image else ''

    def __bool__(self):
        return self.image is not None

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        super().save(*args, **kwargs)

        if 'image' in dirty_fields and self.image:
            optimize_jpeg(self.image)


class ClubImageSetImage(BaseImageSetImage):
    image_set = models.ForeignKey(
        ClubImageSet,
        related_name='images',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class CorpImageSetImage(BaseImageSetImage):
    image_set = models.ForeignKey(
        CorpImageSet,
        related_name='images',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class BaseGallery(models.Model):
    slug = models.CharField(max_length=64)
    sort = models.IntegerField(default=0)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    name_fr = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class ClubGallery(BaseGallery):
    club = models.ForeignKey(
        Club,
        related_name='galleries',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('club', 'slug'),)
        ordering = ('sort', '-id',)


class CorpEventsGallery(BaseGallery):
    site = models.ForeignKey(
        Site,
        default=1,
        blank=True,
        null=True,
        related_name='event_galleries',
        on_delete=models.PROTECT)

    class Meta:
        unique_together = (('slug',),)
        ordering = ('sort', '-id',)


class BaseGalleryImage(DirtyFieldsMixin, models.Model):
    sort = models.IntegerField(default=0)
    image = models.ImageField(upload_to=RandomizedUploadPath('gallery/club/'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.image.url if self.image else ''

    def __bool__(self):
        return self.image is not None

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        super().save(*args, **kwargs)

        if 'image' in dirty_fields and self.image:
            optimize_jpeg(self.image)


class ClubGalleryImage(BaseGalleryImage):
    gallery = models.ForeignKey(
        ClubGallery,
        related_name='images',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
        )

    class Meta:
        ordering = ('sort', '-id',)


class CorpEventsGalleryImage(BaseGalleryImage):
    gallery = models.ForeignKey(
        CorpEventsGallery,
        related_name='images',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
        )

    class Meta:
        ordering = ('sort', '-id',)


class BaseList(models.Model):
    locale = models.CharField(max_length=2, choices=settings.LANGUAGES,
                              default=settings.LANGUAGE_CODE)
    slug = models.CharField(max_length=64)

    class Meta:
        abstract = True


class ClubList(BaseList):
    page = models.ForeignKey(
        ClubPage,
        related_name='lists',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'slug',),)


class CorpList(BaseList):
    page = models.ForeignKey(
        CorpPage,
        related_name='lists',
        on_delete=models.PROTECT
        )

    class Meta:
        unique_together = (('page', 'slug',),)


class BaseListItem(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    sort = models.IntegerField(default=0)

    class Meta:
        abstract = True


class ClubListItem(BaseListItem):
    list = models.ForeignKey(
        ClubList,
        related_name='items',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class CorpListItem(BaseListItem):
    list = models.ForeignKey(
        CorpList,
        related_name='items',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class BaseAdvertisement(models.Model):
    name = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        abstract = True

    def get_image(self):
        path = urlparse(self.image.url).path
        return (
            settings.S3_BASE + '/x250/filters:format(jpeg)' + path)

    def get_thumbnail(self):
        path = urlparse(self.thumbnail.url).path
        return (settings.S3_BASE + '/x250/filters:format(jpeg)' + path)


class ClubAdvertisement(BaseAdvertisement):
    LANGUAGE_CHOICES = (
        ('EN', 'English'),
        ('FR', 'French'),
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='EN',
    )
    thumbnail = models.ImageField(upload_to=RandomizedUploadPath('sponsors/club/thumbnail/'))
    image = models.ImageField(upload_to=RandomizedUploadPath('sponsors/club/image/'))
    club = models.ForeignKey(
        Club,
        related_name='advertisements',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class CorpAdvertisement(BaseAdvertisement):

    LANGUAGE_CHOICES = (
        ('EN', 'English'),
        ('FR', 'French'),
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='EN',
    )
    thumbnail = models.ImageField(upload_to=RandomizedUploadPath('sponsors/corp/thumbnail/'))
    image = models.ImageField(upload_to=RandomizedUploadPath('sponsors/corp/image/'))
    site = models.ForeignKey(
        Site,
        blank=True,
        null=True,
        related_name='corp_ads',
        on_delete=models.PROTECT
        )

    class Meta:
        ordering = ('sort',)


class Folder(models.Model):
    name = models.CharField(max_length=64)
    parent = models.ForeignKey(
        'self',
        null=True,
        related_name='folders',
        on_delete=models.PROTECT
        )
    full_path = models.TextField()

    class Meta:
        unique_together = (('name', 'parent',),)
        ordering = ('name',)

    def delete(self, *args, **kwargs):
        for folder in self.folders.all():
            folder.delete()

        for f in self.files.all():
            f.delete()

        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_path = '{}/'.format(self.parent.full_path) if self.parent else ''
        self.full_path += self.name

        super().save(*args, **kwargs)

        for folder in self.folders.all():
            folder.save()

        for f in self.files.all():
            f.save()


def get_file_upload_path(instance, filename):
    parts = []
    if instance.folder:
        parts.append(instance.folder.full_path)

    parts.append(instance.name)

    if '.' in filename:
        extension = filename.split('.').pop().lower()
        if not instance.name.lower().endswith('.{}'.format(extension)):
            parts.append(extension)

    return '/'.join(parts)


class File(DirtyFieldsMixin, models.Model):
    name = models.CharField(max_length=64)
    folder = models.ForeignKey(
        Folder,
        null=True,
        related_name='files',
        on_delete=models.PROTECT
        )
    file = models.FileField(upload_to=get_file_upload_path, storage=assets_storage)

    class Meta:
        unique_together = (('name', 'folder',),)
        ordering = ('name',)

    def delete(self, *args, **kwargs):
        try:
            assets_storage.delete(self.file.name)
        except:
            pass
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        dirty_fields = self.get_dirty_fields()

        if 'name' in dirty_fields and '.' in self.file.name:
            extension = self.file.name.split('.').pop().lower()
            if not self.name.lower().endswith('.{}'.format(extension)):
                self.name += '.{}'.format(extension)

        ref = None
        if self.pk:
            ref = File.objects.get(pk=self.pk)

        super().save(*args, **kwargs)

        if 'file' not in dirty_fields:
            filename = self.real_name
            path = get_file_upload_path(self, filename)

            if ref and path != ref.file.name:
                with assets_storage.open(ref.file.name, 'rb') as f:
                    contents = f.read()
                with assets_storage.open(path, 'wb') as f:
                    f.write(contents)
                assets_storage.delete(ref.file.name)

    @property
    def real_name(self):
        return self.file.name.split('/').pop()


class Campaigner(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    pin_code = models.CharField(max_length=20)
    reg_time = models.DateTimeField(default=datetime.now, blank=True)    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opt_flag = models.IntegerField();
    send_giftcard = models.IntegerField();
    msg_step = models.IntegerField();    
    class Meta:
        ordering = ('pin_code',)
    






