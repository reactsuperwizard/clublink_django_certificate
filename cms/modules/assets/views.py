from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.utils.translation import ugettext_lazy as _

from clublink.cms.models import File, Folder
from clublink.cms.modules.assets.forms import FileForm, FolderForm
from clublink.cms.views import CMSView


class AssetsView(CMSView):
    template = 'cms/assets/home.jinja'

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'cms_module': 'assets',
        })
        return extra_context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('assets.home'), _('Assets Manager')),
        ]


class FileBrowserView(AssetsView):
    browser_url = None
    template = 'cms/assets/browser.jinja'
    folder = None
    folders = Folder.objects.none()
    files = File.objects.none()

    def pre_dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('folder_pk', None)

        if pk:
            try:
                self.folder = Folder.objects.get(pk=pk)
            except Folder.DoesNotExist:
                messages.add_message(request, messages.WARNING, _('Folder does not exist.'))
                return redirect(reverse('assets.browser'))

        self.folders = Folder.objects.filter(parent=self.folder)
        self.files = File.objects.filter(folder=self.folder)

        reverse_kw = None
        if self.folder:
            reverse_kw = {'folder_pk': self.folder.pk}
        self.browser_url = reverse('assets.browser', kwargs=reverse_kw)

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (self.browser_url, _('File Browser')),
        ]

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        context.update({
            'folder': self.folder,
            'folders': self.folders,
            'files': self.files,
        })
        return context


class NewFolderView(FileBrowserView):
    template = 'cms/assets/new-folder.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        super().pre_dispatch(request, *args, **kwargs)
        self.form = FolderForm(parent=self.folder)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
        })
        return extra_context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('assets.browser.new-folder'), _('New Folder')),
        ]

    def post(self, request, *args, **kwargs):
        self.form = FolderForm(request.POST, parent=self.folder)
        if self.form.is_valid():
            folder = Folder(**self.form.cleaned_data, parent=self.folder)
            folder.save()
            return redirect(self.browser_url)
        return self.get(request, *args, **kwargs)


class FolderDeleteView(FileBrowserView):
    template = 'cms/common/confirm-delete.jinja'
    return_url = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        self.return_url = reverse('assets.browser')
        if self.folder.parent:
            self.return_url = reverse('assets.browser',
                                      kwargs={'folder_pk': self.folder.parent.pk})

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the folder: <strong>{}</strong>?')
        message = message.format(self.folder.full_path)
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        delete_url = reverse('assets.browser.folder-delete', kwargs={'folder_pk': self.folder.pk})
        return crumbs + [
            (delete_url, _('Delete Folder')),
        ]

    def post(self, request, *args, **kwargs):
        self.folder.delete()
        messages.add_message(request, messages.SUCCESS, _('Folder deleted.'))
        return redirect(self.return_url)


class NewFileView(FileBrowserView):
    template = 'cms/assets/new-file.jinja'
    form = None

    def pre_dispatch(self, request, *args, **kwargs):
        super().pre_dispatch(request, *args, **kwargs)
        self.form = FileForm(folder=self.folder)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'form': self.form,
        })
        return extra_context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)
        return crumbs + [
            (reverse('assets.browser.new-file'), _('New File')),
        ]

    def post(self, request, *args, **kwargs):
        self.form = FileForm(request.POST, request.FILES, folder=self.folder)
        if self.form.is_valid():
            new_file = File(**self.form.cleaned_data, folder=self.folder)
            new_file.save()
            return redirect(self.browser_url)
        return self.get(request, *args, **kwargs)


class FileDetailsView(FileBrowserView):
    file = None

    def pre_dispatch(self, request, *args, **kwargs):
        super().pre_dispatch(request, *args, **kwargs)

        try:
            self.file = File.objects.get(pk=kwargs.get('file_pk'))
        except File.DoesNotExist:
            messages.add_message(request, messages.WARNING, _('File does not exist.'))
            return redirect(self.browser_url)

    def get_extra_context(self, request, *args, **kwargs):
        extra_context = super().get_extra_context(request, *args, **kwargs)
        extra_context.update({
            'file': self.file,
        })
        return extra_context


class FileDeleteView(FileDetailsView):
    template = 'cms/common/confirm-delete.jinja'
    return_url = None

    def pre_dispatch(self, request, *args, **kwargs):
        response = super().pre_dispatch(request, *args, **kwargs)

        self.return_url = reverse('assets.browser')
        if self.file.folder:
            self.return_url = reverse('assets.browser',
                                      kwargs={'folder_pk': self.file.folder.pk})

        return response

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        message = _('Are you sure you wish to delete the file: <strong>{}</strong>?')
        message = message.format(self.file.file.name)
        context.update({'confirm_message': message})
        return context

    def get_breadcrumbs(self, request, *args, **kwargs):
        crumbs = super().get_breadcrumbs(request, *args, **kwargs)

        delete_url = reverse(
            'assets.browser.file-delete', kwargs={'file_pk': self.file.pk})

        if self.folder:
            delete_url = reverse(
                'assets.browser.file-delete', kwargs={
                    'folder_pk': self.folder.pk, 'file_pk': self.file.pk})

        return crumbs + [
            (delete_url, _('Delete File')),
        ]

    def post(self, request, *args, **kwargs):
        self.file.delete()
        messages.add_message(request, messages.SUCCESS, _('File deleted.'))
        return redirect(self.return_url)
