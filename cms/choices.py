from django.utils.translation import ugettext_lazy as _

from clublink.cms.constants import DAILY, WEEKLY, MONTHLY, ANNUALLY, REPETITION_UNTIL, NB_REPETITIONS,\
    THIS_EVENT, THIS_EVENT_AND_FOLLOWING, ALL_EVENTS, MEMBER_EVENT, NOTICE, OUTSIDE_EVENT

RECURRENCE_PATTERN = (
    (DAILY, _("Day")),
    (WEEKLY, _("Week")),
    (MONTHLY, _("Month")),
    (ANNUALLY, _("Year")),
)

RECURRENCE_REPETITION_TYPES = (
    (REPETITION_UNTIL, _("Until")),
    (NB_REPETITIONS, _("Repetitions")),
)

EVENTS_EDIT_DELETE_CHOICES = (
    (THIS_EVENT, 'This Event Only'),
    (THIS_EVENT_AND_FOLLOWING, 'This Event and Following Events in Series'),
    (ALL_EVENTS, 'All Events in Series'),
)

TYPE_CHOICES = (
        (MEMBER_EVENT, _('Member Event')),
        (NOTICE, _('Notice')),
        (OUTSIDE_EVENT, _('Outside Event')),
)