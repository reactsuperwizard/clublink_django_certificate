from django import forms
from django.utils.translation import ugettext_lazy as _

from clublink.cms import fields
from clublink.cms.models import File, Folder


class FolderForm(forms.Form):
    name = fields.CharField(max_length=60)

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if Folder.objects.filter(name=name, parent=self.parent).exists():
            raise forms.ValidationError(_('A folder with that name already exists.'))

        return name


class FileForm(forms.Form):
    name = fields.CharField(max_length=60)
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.folder = kwargs.pop('folder', None)

        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields.pop('file')

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if File.objects.filter(name=name, folder=self.folder).exists():
            raise forms.ValidationError(_('A file with that name already exists.'))

        return name
