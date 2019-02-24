from django import views
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator


from clublink.base.decorators import login_required
from clublink.cms.forms import ImageUploadForm
from clublink.cms.models import ClubImage, CorpImage, ClubPage, CorpPage, ClubSnippet, CorpSnippet


@method_decorator(login_required, name='dispatch')
class CMSView(views.View):
    template = None
    extra_context = {}

    def get_breadcrumbs(self, request, *args, **kwargs):
        return []

    def check_permissions(self, request, *args, **kwargs):
        can_access = request.user.permits('can_access_cms') and request.user.is_staff
        return request.user.is_superuser or can_access

    def get_extra_context(self, request, *args, **kwargs):
        return self.extra_context

    def pre_dispatch(self, request, *args, **kwargs):
        pass

    def get(self, request, *args, **kwargs):        
        context = {'breadcrumbs': self.get_breadcrumbs(request, *args, **kwargs)}
        context.update(self.get_extra_context(request, *args, **kwargs))
        return render(request, self.template, context)

    def dispatch(self, request, *args, **kwargs):
        response = self.pre_dispatch(request, *args, **kwargs)
        if response:
            return response

        if not self.check_permissions(request, *args, **kwargs):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)


class RichTextSnippetView(views.View):
    def post(self, request):
        redirect_to = request.POST.get('next', '/')
        locale = request.POST.get('locale')

        if 'corp' in getattr(request, 'urlconf', ''):
            page_class = CorpPage
            snippet_class = CorpSnippet
        else:
            page_class = ClubPage
            snippet_class = ClubSnippet

        try:
            page = page_class.objects.get(pk=request.POST.get('page'))
        except page_class.DoesNotExist:
            pass
        else:
            if locale:
                snippet, _ = snippet_class.objects.get_or_create(
                    page=page, locale=request.LANGUAGE_CODE, slug=request.POST.get('slug'))
                content = request.POST.get('content')

                if content:
                    snippet.content = request.POST.get('content')
                    snippet.save()
                else:
                    snippet.delete()

        return redirect(redirect_to)


class ImageView(views.View):
    def post(self, request):
        redirect_to = request.POST.get('next', '/')

        if 'corp' in getattr(request, 'urlconf', ''):
            page_class = CorpPage
            image_class = CorpImage
        else:
            page_class = ClubPage
            image_class = ClubImage

        try:
            page = page_class.objects.get(pk=request.POST.get('page'))
        except page_class.DoesNotExist:
            pass
        else:
            image, _ = image_class.objects.get_or_create(page=page, slug=request.POST.get('slug'))

            if 'delete' in request.POST:
                image.delete()
            else:
                form = ImageUploadForm(request.POST, request.FILES)
                if form.is_valid():
                    image.image = form.cleaned_data['image']
                    image.save()

        return redirect(redirect_to)
