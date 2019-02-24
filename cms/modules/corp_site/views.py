from __future__ import print_function
import traceback
import sys
import os
from django.conf import settings
from django.http import HttpResponse

from django.contrib import messages
from django.contrib.sites.models import Site
from django.db import IntegrityError
from django.conf import settings

from django.shortcuts import redirect, reverse, render
from django.utils.translation import ugettext_lazy as _

from itertools import groupby

from clublink.base.clients.ibs import WebMemberClient

from clublink.cms.modules.corp_site.forms import (
    ImageUploadForm, NewsForm, EventsGalleryForm, InventoryLookupForm)
from clublink.cms.models import (
    CorpEventsGallery,
    CorpEventsGalleryImage,
    CorpImage,
    CorpPage,
    Campaigner,

)
from clublink.users.models import User
from clublink.cms.modules.corp_site.forms import (
    PageImagesForm,
    PageForm,
    SnippetsForm,
)

from clublink.cms.views import CMSView
from clublink.corp.models import News
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils.encoding import smart_str


from pprint import pprint
import csv
import logging
import datetime


class CorpSiteView(CMSView):
    template = 'cms/corp_site/home.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'cms_module': 'corp_site',
        })
        return extra_context

    def check_permissions(self, request, *args, **kwargs):
        permissions = super().check_permissions(request, *args, **kwargs)
        return permissions and request.user.is_superuser

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.home'), _('Corporate Site Manager')),
        ]


class PagesView(CorpSiteView):
    template = 'cms/corp_site/pages.jinja'
    pages = CorpPage.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        self.pages = CorpPage.objects.all()

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.pages'), _('Pages')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'pages': self.pages.distinct().order_by('sort'),
            'sites': Site.objects.all()
        })
        return context


class PagesAddView(PagesView):
    template = 'cms/corp_site/pages-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = PageForm(request=request)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.pages-add'), _('Add New')),
        ]

    def post(self, request, *args, **kwargs):
        self.form = PageForm(request=request, data=request.POST)

        if self.form.is_valid():
            # import pdb; pdb.set_trace()
            try:
                page = CorpPage.objects.create(**self.form.cleaned_data)
            except IntegrityError:
                messages.add_message(request, messages.ERROR, _('An error occured.'))
            else:
                edit_url = reverse('corp-site.pages-edit', kwargs={'page_pk': page.pk})
                messages.add_message(request, messages.SUCCESS, _('Page was created.'))
                return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class PagesDetailsView(PagesView):
    page = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.page = self.pages.get(pk=kwargs.get('page_pk'))
        except CorpPage.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Page does not exist.'))
            return redirect(reverse('corp-site.pages'))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'page': self.page})
        return context


class PagesEditView(PagesDetailsView):
    template = 'cms/corp_site/pages-edit.jinja'
    page_form = None
    snippets_form_en = None
    snippets_form_fr = None
    images_form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        if self.page:
            self.page_form = PageForm(page=self.page, request=request)
            self.snippets_form_en = SnippetsForm(self.page, locale='en')
            self.snippets_form_fr = SnippetsForm(self.page, locale='fr')
            self.images_form = PageImagesForm(self.page, locale='en')

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'page_form': self.page_form,
            'snippets_form_en': self.snippets_form_en,
            'snippets_form_fr': self.snippets_form_fr,
            'images_form': self.images_form,
        })
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('corp-site.pages-edit', kwargs={'page_pk': self.page.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('corp-site.pages-edit', kwargs={'page_pk': self.page.pk})

        if 'settings' in request.POST:
            self.page_form = PageForm(request=request, data=request.POST, page=self.page)

            if self.page_form.is_valid():
                for field in self.page_form.cleaned_data:
                    setattr(self.page, field, self.page_form.cleaned_data[field])
                try:
                    self.page.save()
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
                    return redirect(edit_url)

        elif 'snippets_en' in request.POST or 'snippets_fr' in request.POST:
            self.snippets_form_en = SnippetsForm(self.page, 'en', request.POST)
            self.snippets_form_fr = SnippetsForm(self.page, 'fr', request.POST)

            locale = 'en'
            snippet_form = self.snippets_form_en

            if 'snippets_fr' in request.POST:
                locale = 'fr'
                snippet_form = self.snippets_form_fr

            if snippet_form.is_valid():
                for field in snippet_form.fields:
                    value = snippet_form.cleaned_data.get(field, None)
                    if value:
                        self.page.set_snippet(field, locale, value)
                    else:
                        self.page.snippets.filter(slug=field, locale=locale).delete()

            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect('{}?edit-snippets&locale={}'.format(edit_url, locale))

        elif 'images' in request.POST:
            self.images_form = PageImagesForm(self.page, 'en', request.POST, request.FILES)

            if self.images_form.is_valid():
                for field in self.images_form.fields:
                    value = self.images_form.cleaned_data.get(field, None)
                    if value:
                        CorpImage.objects.update_or_create(
                            page=self.page, slug=field, locale='en', defaults={'image': value})

            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect('{}?edit-images'.format(edit_url))

        return self.get(request, *args, **kwargs)


class PagesDeleteView(PagesDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        if self.page and self.page.is_locked and not request.user.is_superuser:
            messages.add_message(request, messages.WARNING, _('You cannot delete system pages.'))
            return redirect(reverse('corp-site.pages'))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the page: <strong>{}</strong>?')
        message = message.format(self.page.name or '{}/'.format(self.page.full_path))
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('corp-site.pages-delete', kwargs={'page_pk': self.page.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.page.delete()
        messages.add_message(request, messages.SUCCESS, _('Page deleted.'))
        edit_url = reverse('corp-site.pages')
        return redirect(edit_url)


class NewsView(CorpSiteView):
    template = 'cms/corp_site/news.jinja'
    news = News.objects.all()

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.news'), _('News'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'news': self.news})
        return context


class NewsAddView(NewsView):
    template = 'cms/corp_site/news-add.jinja'
    form = NewsForm()

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.news-add'), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = NewsForm(request.POST, request.FILES)

        if self.form.is_valid():
            data = self.form.cleaned_data
            news_item = News.objects.create(**data)
            edit_url = reverse('corp-site.news-edit', kwargs={'news_item_pk': news_item.pk})
            messages.add_message(request, messages.SUCCESS, _('News item was created.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class NewsDetailsView(NewsView):
    news_item = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.news_item = self.news.get(pk=kwargs.get('news_item_pk'))
        except News.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('News item does not exist.'))
            return redirect(reverse('corp-site.news'))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'news_item': self.news_item})
        return context


class NewsEditView(NewsDetailsView):
    template = 'cms/corp_site/news-edit.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = NewsForm(news=self.news_item)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('corp-site.news-edit', kwargs={'news_item_pk': self.news_item.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('corp-site.news-edit', kwargs={'news_item_pk': self.news_item.pk})

        self.form = NewsForm(request.POST, request.FILES, news=self.news_item)

        if self.form.is_valid():
            news_item = News.objects.filter(pk=self.news_item.pk)
            data = self.form.cleaned_data
            photo = data.pop('photo')
            news_item.update(**data)
            if photo:
                news_item = news_item.first()
                news_item.photo = photo
                news_item.save()
            messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
            return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class NewsDeleteView(NewsDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the news item: <strong>{}</strong>?')
        message = message.format(self.news_item.headline)
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('corp-site.news-delete', kwargs={'news_item_pk': self.news_item.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.news_item.delete()
        messages.add_message(request, messages.SUCCESS, _('News item deleted.'))
        edit_url = reverse('corp-site.news')
        return redirect(edit_url)


class EventsGalleryView(CorpSiteView):
    template = 'cms/corp_site/events-gallery.jinja'
    galleries = CorpEventsGallery.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.galleries = CorpEventsGallery.objects.all()
        return response

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.events-gallery'), _('Events Gallery'))
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context['sites'] = Site.objects.all()
        context.update({'galleries': self.galleries.order_by('name', 'slug')})
        return context


class EventsGalleryAddView(EventsGalleryView):
    template = 'cms/corp_site/events-gallery-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        site_id = kwargs.get('site_pk', request.site.id if request and request.site.id else 1)

        self.form = EventsGalleryForm(initial={'site_id': site_id})

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        # import IPython; IPython.embed();
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.events-gallery-add'), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = EventsGalleryForm(data=request.POST)

        if self.form.is_valid():
            try:
                gallery = CorpEventsGallery.objects.create(**self.form.cleaned_data)
            except IntegrityError:
                messages.add_message(request, messages.ERROR, _('An error occured.'))
            else:
                edit_url = reverse('corp-site.events-gallery-edit',
                                   kwargs={'gallery_pk': gallery.pk})
                messages.add_message(request, messages.SUCCESS, _('Events gallery was created.'))
                return redirect(edit_url)
        else:
            messages.add_message(
                request, messages.ERROR, '{}'.format(self.form.errors)
            )

        return self.get(request, *args, **kwargs)


class EventsGalleryReorderView(EventsGalleryView):
    template = 'cms/corp_site/events-gallery-reorder.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(self, request, *args, **kwargs)
        context.update({'galleries': self.galleries.order_by('sort')})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        reorder_url = reverse('corp-site.events-gallery-reorder')
        return crumbs + [
            (reorder_url, _('Re-order'))
        ]

    def post(self, request, *args, **kwargs):
        for i, pk in enumerate(request.POST.getlist('pk', [])):
            try:
                gallery = self.galleries.get(pk=pk)
            except CorpEventsGallery.DoesNotExist:
                pass
            else:
                gallery.sort = i
                gallery.save()
        messages.add_message(request, messages.SUCCESS, _('Galleries re-ordered.'))
        return redirect(reverse('corp-site.events-gallery'))


class EventsGalleryDetailsView(EventsGalleryView):
    gallery = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.gallery = CorpEventsGallery.objects.get(pk=kwargs.get('gallery_pk'))
        except CorpEventsGallery.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Events gallery does not exist.'))
            return redirect(reverse('corp-site.events-gallery'))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'gallery': self.gallery})
        return context


class EventsGalleryEditView(EventsGalleryDetailsView):
    template = 'cms/corp_site/events-gallery-edit.jinja'
    edit_form = None
    upload_form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.edit_form = EventsGalleryForm(gallery=self.gallery)
        self.upload_form = ImageUploadForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'edit_form': self.edit_form, 'upload_form': self.upload_form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        edit_url = reverse('corp-site.events-gallery-edit',
                           kwargs={'gallery_pk': self.gallery.pk})
        return crumbs + [
            (edit_url, _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('corp-site.events-gallery-edit',
                           kwargs={'gallery_pk': self.gallery.pk})

        if 'edit' in request.POST:
            self.edit_form = EventsGalleryForm(request.POST, gallery=self.gallery)

            if self.edit_form.is_valid():
                gallery = CorpEventsGallery.objects.filter(pk=self.gallery.pk)
                try:
                    gallery.update(**self.edit_form.cleaned_data)
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
                    return redirect(edit_url)
        elif 'upload' in request.POST:
            self.upload_form = ImageUploadForm(request.POST, request.FILES)

            if self.upload_form.is_valid():
                files = request.FILES.getlist('file')
                for image_file in files:
                    CorpEventsGalleryImage.objects.create(gallery=self.gallery, image=image_file)
                messages.add_message(request, messages.SUCCESS, _('Images uploaded.'))
                return redirect('{}?edit-images'.format(edit_url))
        elif 'reorder' in request.POST:
            for i, pk in enumerate(request.POST.getlist('pk', [])):
                try:
                    image = self.gallery.images.get(pk=pk)
                except CorpEventsGalleryImage.DoesNotExist:
                    pass
                else:
                    image.sort = i
                    image.save()
            messages.add_message(request, messages.SUCCESS, _('Images re-ordered.'))
            return redirect('{}?edit-images'.format(edit_url))

        return self.get(request, *args, **kwargs)


class EventsGalleryDeleteView(EventsGalleryDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the gallery: <strong>{name}</strong>?')
        context.update({'confirm_message': message.format(name=self.gallery.name)})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('corp-site.events-gallery-delete',
                             kwargs={'gallery_pk': self.gallery.pk})
        return crumbs + [
            (delete_url, _('Delete'))
        ]

    def post(self, request, *args, **kwargs):
        self.gallery.delete()
        messages.add_message(request, messages.SUCCESS, _('EventsGallery deleted.'))
        return redirect(reverse('corp-site.events-gallery'))


class EventsGalleryImageDetailsView(EventsGalleryDetailsView):
    image = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.image = self.gallery.images.get(pk=kwargs.get('image_pk'))
        except CorpEventsGalleryImage.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('Image does not exist.'))
            edit_url = reverse('corp-site.events-gallery-edit',
                               kwargs={'gallery_pk': self.gallery.pk})
            return redirect('{}?edit-images'.format(edit_url))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'image': self.image})
        return context

webclient = WebMemberClient('Clublink', 'club1nk')

class InventoryLookupView(CMSView):
    template = 'cms/common/inventory-lookup.jinja'

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [('', _('Inventory Lookup'))]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': InventoryLookupForm()})
        return context

    def get(self, request, *args, **kwargs):
        # print(request.GET)

        query = request.GET.get('query', None)
            
        if query:
            query = query.strip()
            context = self.get_extra_context(request, *args, **kwargs)
            context['query'] = query

            form = context['form']
            form.initial = {'query': query}
            context['form'] = form

            # print(webclient.user)
            # print(webclient.password)

            data = webclient.get_inventory(query, 'CONTAINS')

            print(data)

            error = data.get('a_sMessage')
            if error and "is not online" in error:
                messages.add_message(
                    request, messages.ERROR,
                    _('IBS client is not online'))

            #message = data.get('a_sMessage', None)
            result = data.get('SearchOnHandRetailInventoryResult', None)

            # Uncomment after deploy
            # if result:

            # Delete after deploy
            if result:

                # if settings.DEBUG:

                #     '''
                #     Example payload because the IBS server is turned off at night:

                #         from decimal import Decimal
                #         payload = [
                #             {
                #                 'ItemNumber': '086056',
                #                 'ItemName': 'Winn Dri Tac',
                #                 'DepartmentNumber': 'DB',
                #                 'DepartmentName': 'DiamondBack Golf Club',
                #                 'OnHandQuantity': 7,
                #                 'ItemPrice': Decimal('12.40')
                #             },
                #             {
                #                 'ItemNumber': '086056',
                #                 'ItemName': 'Winn Gripps',
                #                 'DepartmentNumber': 'KV',
                #                 'DepartmentName': 'King Valley Golf Club',
                #                 'OnHandQuantity': 45,
                #                 'ItemPrice': Decimal('14.15')
                #             }
                #         ]
                #     '''

                #     from decimal import Decimal
                #     payload = [
                #         {
                #             'ItemNumber': '086056',
                #             'ItemName': 'Winn Dri Tac',
                #             'DepartmentNumber': 'DB',
                #             'DepartmentName': 'DiamondBack Golf Club',
                #             'OnHandQuantity': 7,
                #             'ItemPrice': Decimal('12.40')
                #         },
                #         {
                #             'ItemNumber': '086056',
                #             'ItemName': 'Winn Gripps',
                #             'DepartmentNumber': 'KV',
                #             'DepartmentName': 'King Valley Golf Club',
                #             'OnHandQuantity': 45,
                #             'ItemPrice': Decimal('14.15')
                #         }
                #     ]
                # else:
                payload = result.get('InvItemSearchData', None)

                if len(payload) >= 200:
                    messages.add_message(
                        request, messages.INFO,
                        _('Query contains 200 or more results.  A maximum of 200 results are shown.  Try refining your search.'))

                # See: https://docs.python.org/3/library/itertools.html#itertools.groupby if needed
                grouped_payload = groupby(payload, key=lambda x: x['DepartmentName'])

                final_groups = []

                for k, v in grouped_payload:
                    output = list(v)
                    if output:
                        final_groups.append(
                            (k, output)
                        )

                context['groups'] = final_groups

            else:
                context['groups'] = None
                messages.add_message(
                    request, messages.INFO,
                    _('No results were found for "{}"'.format(query)))

            return render(request, self.template, context)

        else:
            # Go through regular flow but add in the context
            return super(InventoryLookupView, self).get(request, *args, **kwargs)


class EventsGalleryImageDeleteView(EventsGalleryImageDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the image?')
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('corp-site.events-gallery-image-delete',
                             kwargs={'gallery_pk': self.gallery.pk, 'image_pk': self.image.pk})
        edit_url = reverse('corp-site.events-gallery-edit',
                           kwargs={'gallery_pk': self.gallery.pk})
        return crumbs + [
            ('{}?edit-images'.format(edit_url), _('Edit')),
            (delete_url, _('Delete Image')),
        ]

    def post(self, request, *args, **kwargs):
        self.image.delete()
        messages.add_message(request, messages.SUCCESS, _('Image deleted.'))
        edit_url = reverse('corp-site.events-gallery-edit',
                           kwargs={'gallery_pk': self.gallery.pk})
        return redirect('{}?edit-images'.format(edit_url))

class GiftCardExchangerView(CorpSiteView):
    
    template = 'cms/corp_site/giftcard.jinja'
    campaigners = Campaigner.objects.none()
    upform = None
    list_fields = None
    saveBuf = None
    per_page = 50
    title = ''
    paginator = None
    perPageCamp = None
    pagenum = None
    def pre_dispatch(self, request, *args, **kwargs):
        self.campaigners = Campaigner.objects.all()

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('corp-site.golfforlife'), _('golfforlife')),
        ]

    def updatePagenator(self, request):
        self.paginator = Paginator(self.campaigners, self.per_page)
        self.pagenum = request.GET.get('pagenum')
        try:
            self.perPageCamp = self.paginator.page(self.pagenum)
        except PageNotAnInteger:
            self.perPageCamp = self.paginator.page(1)
        except EmptyPage:
            self.pagenum = self.paginator.num_pages
            self.perPageCamp = self.paginator.page(self.pagenum)
    def get(self, request):        
        self.updatePagenator(request)        
        return render(request, self.template, {
            'campaigners': self.perPageCamp,
            'list_fields': self.list_fields, 
            'pagenum': self.pagenum,
            'per_page': self.per_page,
            'title': self.title})
    def insert_2ModelPinCode(self, row):
        # model insert the pin code
        try:
            obj = Campaigner()
            obj.pin_code = row
            obj.save()
            return True
        except Exception as ex:
            return False
    
    def handle_uploaded_file(self, csvfile):
        try:
            # spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
            # for row in spamreader:
            #     insert_2ModelPinCode(row)
            pincodes = []
            bBuffer = b'';
            for chunk in csvfile.chunks():
                bBuffer = bBuffer + chunk
            buf = bBuffer.decode('ascii')
            lines = buf.split('\n')
            success_count = 0;
            for line in lines:  
                if line != None and line != '':                    
                    columns = line.split(",")                    
                    if len(columns) > 0:
                        pincodes.append(columns[0])
            for pincode in pincodes:
                try:
                    if self.insert_2ModelPinCode(pincode):
                        success_count += 1
                except Exception as e:
                    print('Insert error\n')                    
            return success_count
        except Exception as e:
            pprint(e)
            print('Passing error\n')
            return 0

    def makeRowFromCampaigner(self, campainer):
        retval = ''
        retval += campainer.pin_code
        retval += ','
        retval += campainer.user.email
        retval += ','
        retval += campainer.reg_time.strftime("%B %d, %Y")
        retval += ','
        retval += 'T'
        retval += ','
        retval += str(campainer.send_giftcard) + ' & ' + str(campainer.msg_step)
        retval += '\n'
        return retval


    def downloadCSV(self):
        outputfile = ''        
        for campainer in Campaigner.objects.filter(opt_flag__exact='1'):            
            outputfile += self.makeRowFromCampaigner(campainer)
        file_path = 'pincodes_' + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".csv"        
        response = HttpResponse(outputfile,content_type='application/force-download') 
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_path)
        response['X-Sendfile'] = smart_str(file_path)
        return response

    def post(self, request, *args, **kwargs):
        if 'upload' in request.POST and request.FILES['fileinput']:
            success_count = self.handle_uploaded_file(request.FILES['fileinput'])
            print('******************')
            print(success_count)
            print('******************')
            self.updatePagenator(request)
            return render(request, self.template, {
                'campaigners': self.perPageCamp,
                'list_fields': self.list_fields, 
                'pagenum': self.pagenum,
                'per_page': self.per_page,
                'title': self.title})
        elif 'download' in request.POST:
            return self.downloadCSV()
            
        self.updatePagenator(request)
        return render(request, self.template, {
            'campaigners': self.perPageCamp,
            'list_fields': self.list_fields, 
            'pagenum': self.pagenum,
            'per_page': self.per_page,
            'title': self.title
            })
