import re

from django.forms.widgets import Widget, Select
from django.utils.safestring import mark_safe


# Attempt to match many time formats:
# Example: "12:34:56 P.M."  matches:
# ('12', '34', ':56', '56', 'P.M.', 'P', '.', 'M', '.')
# ('12', '34', ':56', '56', 'P.M.')
# Note that the colon ":" before seconds is optional, but only if seconds are omitted
RE_TIME = re.compile(r'(\d\d?):(\d\d)(:(\d\d))? *([aApP]\.?[mM]\.?)?$')

# The following are just more readable ways to access re.matched groups:
HOURS = 0
MINUTES = 1
SECONDS = 3
MERIDIEM = 4


class SelectTimeWidget(Widget):
    """
    A Widget that splits time input into <select> elements.

    Allows form to show as 24hr: <hour>:<minute>:<second>, (default)
    or as 12hr: <hour>:<minute>:<second> <am|pm>

    Also allows user-defined increments for minutes/seconds
    """
    none_value = ('', '---')
    hour_field = '%s_hour'
    minute_field = '%s_minute'
    second_field = '%s_second'
    meridiem_field = '%s_meridiem'

    def __init__(self, attrs=None,
                 hour_step=None, minute_step=None, second_step=None,
                 twelve_hr=False, use_seconds=True, required=True):
        """
        hour_step, minute_step, second_step are optional step values
        for the range of values for the associated select element
        twelve_hr: If True, forces the output to be in 12-hr format (rather than 24-hr)
        use_seconds: If False, doesn't show seconds select element and stores seconds = 0.
        required: If False, empty values are allowed.
        """
        self.attrs = attrs or {}
        self.twelve_hr = twelve_hr
        self.use_seconds = use_seconds
        self.required = required

        if hour_step and twelve_hr:
            self.hours = range(1, 13, hour_step)
        elif hour_step:  # 24hr, with stepping.
            self.hours = range(0, 24, hour_step)
        elif twelve_hr:  # 12hr, no stepping
            self.hours = range(1, 13)
        else:  # 24hr, no stepping
            self.hours = range(0, 24)

        if minute_step:
            self.minutes = range(0, 60, minute_step)
        else:
            self.minutes = range(0, 60)

        if second_step:
            self.seconds = range(0, 60, second_step)
        else:
            self.seconds = range(0, 60)

    def render(self, name, value, attrs=None):
        hour_val = ''
        minute_val = ''
        second_val = ''
        meridiem_val = ''

        try:  # try to get time values from a datetime.time object (value)
            hour_val, minute_val, second_val = value.hour, value.minute, value.second
            if self.twelve_hr:
                if hour_val >= 12:
                    meridiem_val = 'p.m.'
                else:
                    meridiem_val = 'a.m.'
        except AttributeError:
            if isinstance(value, str):
                match = RE_TIME.match(value)
                if match:
                    time_groups = match.groups()
                    hour_val = int(time_groups[HOURS]) % 24  # force to range(0-24)
                    minute_val = int(time_groups[MINUTES])
                    if time_groups[SECONDS] is None:
                        second_val = 0
                    else:
                        second_val = int(time_groups[SECONDS])

                    # check to see if meridiem was passed in
                    if time_groups[MERIDIEM] is not None:
                        meridiem_val = time_groups[MERIDIEM]
                    else:  # otherwise, set the meridiem based on the time
                        if self.twelve_hr:
                            if hour_val >= 12:
                                meridiem_val = 'p.m.'
                            else:
                                meridiem_val = 'a.m.'

        # If we're doing a 12-hr clock, there will be a meridiem value, so make sure the
        # hours get printed correctly
        if self.twelve_hr:
            if meridiem_val.lower().startswith('p') and hour_val > 12 and hour_val < 24:
                hour_val = hour_val % 12
            elif hour_val == 0:
                hour_val = 12

        output = []
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name

        # For times to get displayed correctly, the values MUST be converted to unicode
        # When Select builds a list of options, it checks against Unicode values
        if hour_val != '':
            hour_val = u"%.2d" % hour_val

        if minute_val != '':
            minute_val = u"%.2d" % minute_val

        if second_val != '':
            second_val = u"%.2d" % second_val

        hour_choices = [("%.2d" % i, "%.2d" % i) for i in self.hours]
        if not self.required:
            hour_choices.insert(0, self.none_value)
        local_attrs = self.build_attrs({'id': self.hour_field % id_})
        select_html = Select(choices=hour_choices).render(self.hour_field % name, hour_val,
                                                          local_attrs)
        output.append(select_html)

        minute_choices = [("%.2d" % i, "%.2d" % i) for i in self.minutes]
        if not self.required:
            minute_choices.insert(0, self.none_value)
        local_attrs['id'] = self.minute_field % id_
        select_html = Select(choices=minute_choices).render(self.minute_field % name, minute_val,
                                                            local_attrs)
        output.append(select_html)

        if self.use_seconds:
            second_choices = [("%.2d" % i, "%.2d" % i) for i in self.seconds]
            if not self.required:
                second_choices.insert(0, self.none_value)
            local_attrs['id'] = self.second_field % id_
            select_html = Select(choices=second_choices).render(self.second_field % name,
                                                                second_val, local_attrs)
            output.append(select_html)

        if self.twelve_hr:
            meridiem_choices = [('a.m.', 'a.m.'), ('p.m.', 'p.m.')]
            local_attrs['id'] = local_attrs['id'] = self.meridiem_field % id_
            select_html = Select(choices=meridiem_choices).render(self.meridiem_field % name,
                                                                  meridiem_val, local_attrs)
            output.append(select_html)

        return mark_safe(u'\n'.join(output))

    def id_for_label(self, id_):
        return '%s_hour' % id_

    id_for_label = classmethod(id_for_label)

    def value_from_datadict(self, data, files, name):
        h = data.get(self.hour_field % name)
        m = data.get(self.minute_field % name)
        s = data.get(self.second_field % name)

        # If no h:m:s fields are supplied, fall back to the original time field.
        if h is None and m is None and s is None:
            return data.get(name, None)

        # If any h:m:s fields are supplied, default any empty values to zero.
        if h or m or s:
            try:
                h, m, s = int(h or 0), int(m or 0), int(s or 0)
            except ValueError:
                # Garbage in h:m:s fields; fall back to original time field.
                # Not sure if this is the right thing to do, but this seems
                # to match the behavior of SelectDateWidget.
                return data.get(name, None)
        else:
            # All empty: field is blank.
            return None

        meridiem = data.get(self.meridiem_field % name, '')

        # NOTE: if no meridiem, assume 24-hr
        if meridiem.lower().startswith('p') and h != 12:
            h = (h + 12) % 24
        elif meridiem.lower().startswith('a') and h == 12:
            h = 0

        return '%.2d:%.2d:%.2d' % (h, m, s)
