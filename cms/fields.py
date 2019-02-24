from django.forms import fields, Textarea
from django.utils.translation import ugettext_lazy as _


BOOLEAN_CHOICES = (
    (True, _('Yes')),
    (False, _('No')),
)


class CharField(fields.CharField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-input'
        return attrs


class TextareaField(fields.CharField):
    widget=Textarea
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-textarea'
        return attrs


class EmailField(fields.EmailField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-input'
        return attrs


class TypedChoiceField(fields.TypedChoiceField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-select'
        return attrs


class ChoiceField(fields.ChoiceField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-select'
        return attrs


class DateField(fields.DateField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-input'
        return attrs


class IntegerField(fields.IntegerField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'uk-input'
        return attrs
