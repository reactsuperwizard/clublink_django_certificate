from django.conf import settings
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout,
    REDIRECT_FIELD_NAME
)
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import redirect, render, resolve_url, reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views import View

from clublink.cms.forms import LoginForm
from clublink.clubs.models import Club, Department
from clublink.users.models import User

from clublink.cms.views import CMSView


def login(request):
    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')

    # Ensure the user-originating redirection URL is safe.
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = resolve_url(reverse('home'))
    form = LoginForm()

    if request.user.is_authenticated:
        if redirect_to == request.path:
            return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
        return redirect(redirect_to)
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(redirect_to)

    return render(request, 'cms/login.jinja', {'form': form})


def logout(request):
    auth_logout(request)
    return redirect(reverse('home'))


class HomeView(CMSView):
    def get(self, request, *args, **kwargs):
        return render(request, 'cms/dashboard/home.jinja')


class ListView(View):
    title = ''
    queryset = None
    list_fields = None
    per_page = 10
    actions = (
        ('delete_items', _('Delete selected')),
    )

    def get_queryset(self, request):
        return self.queryset

    def delete_items(self, request):
        item_pks = request.POST.get('items', [])
        items = self.get_queryset(request).filter(pk__in=item_pks)
        items.delete()

    def get(self, request):
        per_page = request.GET.get('per_page', self.per_page)
        paginator = Paginator(self.get_queryset(request), per_page)

        page = request.GET.get('page')
        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            page = paginator.num_pages
            items = paginator.page(page)

        return render(request, 'cms/list.jinja', {
            'items': items, 'list_fields': self.list_fields, 'page': page, 'per_page': per_page,
            'title': self.title})

    def post(self, request):
        action = request.POST.get('action')

        for a in self.actions:
            if a[0] == action:
                fn = getattr(self, a[1])
                if callable(fn):
                    fn(request)

        return self.get(request)


class UserListView(ListView):
    title = _('User Accounts')
    list_fields = (
        ('username', _('Username')),
        ('first_name', _('First Name')),
        ('last_name', _('Last Name')),
        ('membership_number', _('Membership Number')),
    )
    queryset = User.objects.all()


class ClubListView(ListView):
    title = _('Clubs')
    list_fields = (
        ('name', _('Name')),
        ('slug', _('Slug')),
        ('code', _('Club Number')),
    )
    queryset = Club.objects.all()


class DepartmentListView(ListView):
    title = _('Departments')
    list_fields = (
        ('name', _('Name')),
        ('number', _('Department Number')),
        ('hidden', _('Hidden')),
    )
    queryset = Department.objects.all()
