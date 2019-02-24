from django.contrib import messages
from django.core import paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import redirect, reverse
from django.utils.translation import ugettext_lazy as _

from clublink.clubs.models import Club, Department
from clublink.cms.modules.users.forms import (
    AccountsFilterForm,
    MyAccountForm,
    PermissionsForm,
    UserForm,
    UserSearchForm,
)
from clublink.cms.views import CMSView
from clublink.users.models import User, UserPermissions


class UsersView(CMSView):
    template = 'cms/users/home.jinja'

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.home'), _('User Management')),
        ]


class UserAccountsView(UsersView):
    template = 'cms/users/accounts.jinja'
    users = User.objects.none()
    filter_form = None

    def check_permissions(self, request, *args, **kwargs):
        permissions = super().check_permissions(request, *args, **kwargs)
        return permissions and request.user.is_superuser

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.accounts'), _('Accounts')),
        ]

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        self.filter_form = AccountsFilterForm(request.GET)
        self.users = User.objects.exclude(pk=request.user.pk)

        if self.filter_form.is_valid():
            filters = self.filter_form.cleaned_data
            if filters['show_only'] == AccountsFilterForm.STAFF_ONLY:
                self.users = self.users.filter(is_staff=True)
            elif filters['show_only'] == AccountsFilterForm.SUPERUSERS_ONLY:
                self.users = self.users.filter(is_superuser=True)

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)

        per_page = request.GET.get('per_page', 50)
        pages = paginator.Paginator(self.users.order_by('username'), per_page)

        page = request.GET.get('page')
        try:
            users = pages.page(page)
        except paginator.PageNotAnInteger:
            users = pages.page(1)
        except paginator.EmptyPage:
            page = pages.num_pages
            users = pages.page(page)

        context.update({'users': users, 'filter_form': self.filter_form})

        return context

    def post(self, request, *args, **kwargs):
        query = request.POST.get('query')
        if query:
            self.users = self.users.filter(
                Q(username__contains=query) | Q(first_name__contains=query)
                | Q(last_name__contains=query) | Q(email=query) | Q(membership_number=query)
                | Q(employee_number=query))
        return self.get(request, *args, **kwargs)


class UserAddView(UserAccountsView):
    template = 'cms/users/accounts-add.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = UserForm()
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.accounts-add'), _('Add New'))
        ]

    def post(self, request, *args, **kwargs):
        self.form = UserForm(request.POST)

        if self.form.is_valid():
            data = self.form.cleaned_data
            password = data.pop('password', None)

            user = User(**self.form.cleaned_data)
            if password:
                user.set_password(password)

            try:
                user.save()
            except IntegrityError:
                messages.add_message(request, messages.ERROR, _('An error occured.'))
            else:
                edit_url = reverse('users.accounts-edit', kwargs={'user_pk': user.pk})
                messages.add_message(request, messages.SUCCESS, _('User account was created.'))
                return redirect(edit_url)

        return self.get(request, *args, **kwargs)


class UserDetailsView(UserAccountsView):
    user = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        try:
            self.user = self.users.get(pk=kwargs.get('user_pk'))
        except User.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('User account does not exist.'))
            return redirect(reverse('users.accounts'))

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'selected_user': self.user})
        return context


class UserEditView(UserDetailsView):
    template = 'cms/users/accounts-edit.jinja'
    user_form = None
    permissions_form = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        permissions, _ = UserPermissions.objects.get_or_create(user=self.user)
        self.user_form = UserForm(user=self.user)
        self.permissions_form = PermissionsForm(user=self.user)
        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        unassigned_departments = Department.objects.exclude(
            pk__in=[d.pk for d in self.user.departments.all()])
        unassigned_clubs = Club.objects.exclude(
            pk__in=[c.pk for c in self.user.clubs.all()])
        context.update({
            'user_form': self.user_form,
            'permissions_form': self.permissions_form,
            'assigned_departments': self.user.departments.all(),
            'unassigned_departments': unassigned_departments,
            'assigned_clubs': self.user.clubs.all(),
            'unassigned_clubs': unassigned_clubs,
        })
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.accounts-edit', kwargs={'user_pk': self.user.pk}), _('Edit'))
        ]

    def post(self, request, *args, **kwargs):
        edit_url = reverse('users.accounts-edit', kwargs={'user_pk': self.user.pk})

        if 'edit' in request.POST:
            self.user_form = UserForm(request.POST, user=self.user)

            if self.user_form.is_valid():
                data = self.user_form.cleaned_data
                password = data.pop('password')
                try:
                    self.users.filter(pk=self.user.pk).update(**data)
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    if password:
                        self.user.set_password(password)
                        self.user.save()
                    messages.add_message(request, messages.SUCCESS, _('Changes saved.'))
                    return redirect(edit_url)
        elif 'departments' in request.POST:
            if 'add' in request.POST and request.POST['add']:
                try:
                    department = Department.objects.get(pk=request.POST['add'])
                except Department.DoesNotExist:
                    pass
                else:
                    self.user.departments.add(department)
                    messages.add_message(request, messages.SUCCESS, _('Department assigned.'))
            elif 'delete' in request.POST and request.POST['delete']:
                try:
                    department = Department.objects.get(pk=request.POST['delete'])
                except Department.DoesNotExist:
                    pass
                else:
                    self.user.departments.remove(department)
                    messages.add_message(request, messages.SUCCESS, _('Department unassigned.'))
            return redirect('{}?edit-departments'.format(edit_url))
        elif 'clubs' in request.POST:
            if 'add' in request.POST and request.POST['add']:
                try:
                    club = Club.objects.get(pk=request.POST['add'])
                except Club.DoesNotExist:
                    pass
                else:
                    self.user.clubs.add(club)
                    messages.add_message(request, messages.SUCCESS, _('Club assigned.'))
            elif 'delete' in request.POST and request.POST['delete']:
                try:
                    club = Club.objects.get(pk=request.POST['delete'])
                except Club.DoesNotExist:
                    pass
                else:
                    self.user.clubs.remove(club)
                    messages.add_message(request, messages.SUCCESS, _('Club unassigned.'))
            return redirect('{}?edit-clubs'.format(edit_url))
        elif 'permissions' in request.POST:
            self.permissions_form = PermissionsForm(request.POST, user=self.user)

            if self.permissions_form.is_valid():
                data = self.permissions_form.cleaned_data
                try:
                    UserPermissions.objects.filter(user=self.user).update(**data)
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, _('An error occured.'))
                else:
                    messages.add_message(request, messages.SUCCESS, _('Permissions updated.'))
                    return redirect('{}?edit-permissions'.format(edit_url))

        return self.get(request, *args, **kwargs)


class UserDeleteView(UserDetailsView):
    template = 'cms/common/confirm-delete.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the user account: '
                    '<strong>{username}</strong>?')
        context.update({'confirm_message': message.format(username=self.user.username)})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('users.accounts-delete', kwargs={'user_pk': self.user.pk})
        return crumbs + [
            (delete_url, _('Delete')),
        ]

    def post(self, request, *args, **kwargs):
        self.user.delete()
        messages.add_message(request, messages.SUCCESS, _('User account deleted.'))
        return redirect(reverse('users.accounts'))


class ImpersonateUserView(UsersView):
    template = 'cms/users/impersonate.jinja'
    form = UserSearchForm()
    results = None

    def check_permissions(self, request, *args, **kwargs):
        permissions = super().check_permissions(request, *args, **kwargs)
        can_impersonate = request.user.is_superuser or request.user.permits('can_impersonate_user')
        return permissions and can_impersonate

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.impersonate'), _('Impersonate User')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form, 'results': self.results})
        return context

    def post(self, request, *args, **kwargs):
        self.form = UserSearchForm(request.POST)

        if self.form.is_valid():
            self.results = self.form.cleaned_data['results']

        return self.get(request, *args, **kwargs)


class MyAccountView(UsersView):
    template = 'cms/users/my-account.jinja'
    form = None

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('users.my-account'), _('My Account')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({'form': self.form})
        return context

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)
        self.form = MyAccountForm(user=request.user)
        return response

    def post(self, request, *args, **kwargs):
        self.form = MyAccountForm(request.POST, request.user)

        if self.form.is_valid():
            data = self.form.cleaned_data

            if 'password' in data:
                request.user.set_password(data.pop('password'))
                request.user.save()

            user = User.objects.filter(pk=request.user.pk)
            user.update(**data)

            messages.add_message(request, messages.SUCCESS, _('Your account was updated.'))
            return redirect(reverse('users.my-account'))

        return self.get(request, *args, **kwargs)
