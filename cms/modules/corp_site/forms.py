import re

from django import forms
from django.contrib.sites.models import Site
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from clublink.cms import fields
from clublink.cms.models import CorpEventsGallery, CorpPage
from clublink.cms.modules.corp_site.config import PAGE_TEMPLATES
from clublink.corp.models import News


class InventoryLookupForm(forms.Form):
    """
    This form takes an inventory item ID and performs a search against 
    the IBS inventory.  The IBS inventory API only accepts EXACT, CONTAINS, 
    and something else, and due to budget constraints ClubLink only wanted to 
    do CONTAINS, with some frontend enforcement.
    """

    query = fields.CharField(
        label=_('Inventory ID'),
        required=True,
        widget=forms.TextInput(attrs={'minlength': 5}))


class NewsForm(forms.Form):
    publish_date = fields.DateField(input_formats=['%d/%m/%Y'],
                                    widget=forms.DateInput(attrs={'data-pikaday': True}))
    headline_en = fields.CharField(label=_('Headline'))
    headline_fr = fields.CharField(label=_('Headline (French)'), required=False)
    summary_en = fields.CharField(label=_('Summary'))
    summary_fr = fields.CharField(label=_('Summary (French)'), required=False)
    content_en = forms.CharField(label=_('Content'),
                                 widget=forms.Textarea(attrs={'data-tinymce': True}))
    content_fr = forms.CharField(label=_('Content (French)'), required=False,
                                 widget=forms.Textarea(attrs={'data-tinymce': True}))
    photo = forms.ImageField()
    slug = fields.CharField(required=False)
    show_on_corp_site = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    show_on_club_site = forms.BooleanField(widget=forms.CheckboxInput, required=False)

    def __init__(self, *args, **kwargs):
        self.news = None

        if 'news' in kwargs:
            self.news = kwargs.pop('news')
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'publish_date':
                    self.news.publish_date.strftime('%d/%m/%Y') if self.news.publish_date else '',
                'headline_en': self.news.headline_en,
                'headline_fr': self.news.headline_fr,
                'summary_en': self.news.summary_en,
                'summary_fr': self.news.summary_fr,
                'content_en': self.news.content_en,
                'content_fr': self.news.content_fr,
                'slug': self.news.slug,
                'show_on_corp_site': self.news.show_on_corp_site,
                'show_on_club_site': self.news.show_on_club_site,
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        if self.news:
            self.fields['photo'].required = False

    def clean(self):
        slug = self.cleaned_data.get('slug')
        headline = self.cleaned_data.get('headline')

        if not slug and headline:
            slug = headline

        self.cleaned_data['slug'] = slugify(slug)

        news = News.objects.filter(slug=self.cleaned_data.get('slug'))
        if self.news:
            news = news.exclude(pk=self.news.pk)
        if news.exists():
            self.add_error('slug', forms.ValidationError(_('Slug is already in use.')))

        return self.cleaned_data


class EventsGalleryForm(forms.Form):
    name = fields.CharField(required=False)
    name_en = fields.CharField(required=False)
    name_fr = fields.CharField(required=False)
    slug = fields.CharField()
    site_id = fields.ChoiceField(
        choices=[(site.id, site.name) for site in Site.objects.all()]
    )

    def __init__(self, request=None, *args, **kwargs):
        self.gallery = None

        if 'gallery' in kwargs:
            self.gallery = kwargs.pop('gallery')
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'name': self.gallery.name,
                'name_en': self.gallery.name_en,
                'name_fr': self.gallery.name_fr,
                'slug': self.gallery.slug,
                'site_id': self.gallery.site_id
            }
            kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

    def clean_slug(self):
        data = self.cleaned_data['slug']

        galleries = CorpEventsGallery.objects.all()
        if self.gallery:
            galleries = galleries.exclude(pk=self.gallery.pk)

        try:
            galleries.get(slug=data)
        except CorpEventsGallery.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(_('This slug is already in use.'))

        return data


class ImageUploadForm(forms.Form):
    file = forms.ImageField(widget=forms.FileInput({'multiple': True}))


class PageForm(forms.Form):
    name_en = fields.CharField(label=_('Name'), required=False)
    name_fr = fields.CharField(label=_('Name (French)'), required=False)
    slug = fields.CharField(max_length=64)
    show_in_main_menu = forms.BooleanField(
        label=_('Show in Hamburger Menu'), required=False, initial=True,
        widget=forms.CheckboxInput)
    hidden_bucket = forms.BooleanField(required=False, initial=False)
    list_in_main_menu_subnav = forms.BooleanField(
        label=_('Duplicate in Hamburger Menu Subnav'), required=False, initial=False,
        widget=forms.CheckboxInput)
    name_in_main_menu_subnav_en = fields.CharField(
        label=_('Name in Hamburger Menu Subnav'), required=False)
    name_in_main_menu_subnav_fr = fields.CharField(
        label=_('Name in Hamburger Menu Subnav (French)'), required=False)
    show_page_nav = forms.BooleanField(
        label=_('Show Page Navigation'), required=False, initial=True,
        widget=forms.CheckboxInput)
    list_in_child_page_nav = forms.BooleanField(
        label=_('Show in Child Page Navigation'), required=False, initial=False,
        widget=forms.CheckboxInput)
    name_in_child_page_nav_en = fields.CharField(
        label=_('Name in Child Page Navigation'), required=False)
    name_in_child_page_nav_fr = fields.CharField(
        label=_('Name in Child Page Navigation (French)'), required=False)
    should_redirect = forms.BooleanField(
        required=False, initial=False, widget=forms.CheckboxInput)
    external_redirect = fields.CharField(required=False)
    opens_in_new_window = fields.TypedChoiceField(
        coerce=lambda x: x == 'True', choices=fields.BOOLEAN_CHOICES, initial=False,
        required=False)
    site_id = fields.ChoiceField(
        choices=[
            [s.id, s.domain] for s in Site.objects.all()
        ]
    )
    facebook_pixel_id = fields.CharField(required=False)

    def __init__(self, site=None, request=None, *args, **kwargs):
        self.page = None

        if 'page' in kwargs:
            self.page = kwargs.pop('page')

        p = self.page

        specified_site_id_string = request.GET.get('site', None)

        if specified_site_id_string:
            initial_site_id = specified_site_id_string
        elif p and p.site:
            initial_site_id = p.site.id

        if self.page:
            kw_initial = kwargs.get('initial', {})
            kwargs['initial'] = {
                'name_en': p.name_en,
                'name_fr': p.name_fr,
                'slug': p.slug,
                'parent': p.parent.pk if p.parent else None,
                'show_in_main_menu': p.show_in_main_menu,
                'list_in_main_menu_subnav': p.list_in_main_menu_subnav,
                'name_in_main_menu_subnav_en': p.name_in_main_menu_subnav_en,
                'name_in_main_menu_subnav_fr': p.name_in_main_menu_subnav_fr,
                'show_page_nav': p.show_page_nav,
                'list_in_child_page_nav': p.list_in_child_page_nav,
                'name_in_child_page_nav_en': p.name_in_child_page_nav_en,
                'name_in_child_page_nav_fr': p.name_in_child_page_nav_fr,
                'should_redirect': p.should_redirect,
                'external_redirect': p.external_redirect,
                'internal_redirect': p.internal_redirect.pk if p.internal_redirect else None,
                'opens_in_new_window': p.opens_in_new_window,
                'site_id': int(initial_site_id),
                'facebook_pixel_id': p.facebook_pixel_id
            }
            kwargs['initial'].update(kw_initial)
        else:

            prepop_site = {'site_id': initial_site_id}

            if kwargs.get('initial', {}):
                kwargs['initial'].update(prepop_site)
            else:
                kwargs['initial'] = prepop_site


        super().__init__(*args, **kwargs)

        excludes = Q(parent=None, slug='')
        if self.page:
            excludes |= Q(pk=self.page.pk)
        linkable_pages = CorpPage.objects.exclude(excludes).order_by('full_path')

        if request:
            # import pdb; pdb.set_trace();
            if p and p.site:
                linkable_pages = linkable_pages.filter(site=p.site)
            elif request:
                if specified_site_id_string:
                    linkable_pages = linkable_pages.filter(site_id=specified_site_id_string)
                else:
                    linkable_pages = linkable_pages.filter(site=request.site)
            else:
                pass

        if self.page and self.page.is_locked:
            self.fields.pop('slug')
        else:
            self.fields['parent'] = fields.ChoiceField(
                choices=[(None, 'No parent')] + [(p.pk, '{} ({})'.format(p.full_path, p.site.domain) ) for p in linkable_pages],
                required=False)

        self.fields['internal_redirect'] = fields.ChoiceField(
            choices=[(None, 'No redirect')] + [(p.pk, p.full_path) for p in linkable_pages],
            required=False)

    def clean_parent(self):
        pk = self.cleaned_data['parent']
        parent = None

        if pk:
            try:
                parent = CorpPage.objects.get(pk=pk)
            except CorpPage.DoesNotExist:
                raise forms.ValidationError('Invalid parent.')

        return parent

    def clean_internal_redirect(self):
        pk = self.cleaned_data['internal_redirect']
        parent = None

        if pk:
            try:
                parent = CorpPage.objects.get(pk=pk)
            except CorpPage.DoesNotExist:
                raise forms.ValidationError('Invalid internal redirect.')

        return parent

    def clean(self):
        cleaned_data = super().clean()

        slug = cleaned_data.get('slug', '')
        parent = cleaned_data.get('parent', None)

        if slug:
            if re.match(r'[^a-zA-Z0-9_-]', slug):
                self.add_error(
                    'slug', forms.ValidationError(_('Slug may only contain alphanumeric '
                                                    'characters, underscore and hyphens.')))
            else:
                pages = CorpPage.objects.filter(parent=parent, slug=slug)

                if self.page:
                    pages = pages.exclude(pk=self.page.pk)

                if pages.exists():
                    self.add_error(
                        'slug', forms.ValidationError(_('This slug is already in use.')))

        return cleaned_data


class SnippetsForm(forms.Form):
    title = fields.CharField(required=False)
    keywords = fields.CharField(required=False)
    description = fields.TextareaField(required=False)
    headline = fields.CharField(required=False)
    button = fields.CharField(required=False)
    clickthrough = fields.CharField(required=False)

    def __init__(self, page, locale, *args, **kwargs):
        self.page = page

        if 'prefix' not in kwargs:
            kwargs['prefix'] = locale

        template = PAGE_TEMPLATES.get(self.page.full_path, PAGE_TEMPLATES['*'])
        template_snippets = template.get('snippets', PAGE_TEMPLATES['*']['snippets'])

        kw_initial = kwargs.get('initial', {})
        kwargs['initial'] = {
            'title': self.page.get_snippet('title', fallback=False, locale=locale),
            'keywords': self.page.get_snippet('keywords', fallback=False, locale=locale),
            'description': self.page.get_snippet('description', fallback=False, locale=locale),
            'headline': self.page.get_snippet('headline', fallback=False, locale=locale),
            'button': self.page.get_snippet('button', fallback=False, locale=locale),
            'clickthrough': self.page.get_snippet('clickthrough', fallback=False, locale=locale),
        }

        for slug in template_snippets:
            kwargs['initial'][slug] = self.page.get_snippet(slug, fallback=False, locale=locale)

        kwargs['initial'].update(kw_initial)

        super().__init__(*args, **kwargs)

        for slug in template_snippets:
            field_type = template_snippets[slug]

            if field_type == 'text':
                self.fields[slug] = fields.TextareaField(required=False)
            elif field_type == 'html':
                self.fields[slug] = forms.CharField(
                    required=False, widget=forms.Textarea(attrs={'data-tinymce': True}))
            else:
                self.fields[slug] = fields.CharField(required=False)


class PageImagesForm(forms.Form):
    def __init__(self, page, locale, *args, **kwargs):
        self.page = page

        if 'prefix' not in kwargs:
            kwargs['prefix'] = locale

        template = PAGE_TEMPLATES.get(self.page.full_path, PAGE_TEMPLATES['*'])
        template_images = template.get('images', PAGE_TEMPLATES['*']['images'])

        super().__init__(*args, **kwargs)

        for slug in template_images:
            label = template_images[slug]['label']
            self.fields[slug] = forms.ImageField(label=label, required=False)

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()
