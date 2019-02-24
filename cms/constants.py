import datetime
from django.utils.translation import ugettext_lazy as _

MEMBER_EVENT = 0
NOTICE = 1
OUTSIDE_EVENT = 2

DAILY = _('daily')
WEEKLY = _('weekly')
MONTHLY = _('monthly')
ANNUALLY = _('annually')

REPETITION_UNTIL = _('repetition_until')
NB_REPETITIONS = _('nb_repetitions')

THIS_EVENT = _('This Event Only')
THIS_EVENT_AND_FOLLOWING = _('This event and following events in series')
ALL_EVENTS = _('All events in series')

DEFAULT_START_TIME = datetime.time(9, 00)
DEFAULT_END_TIME = datetime.time(17, 00)
DEFAULT_REGISTRATION_OPEN_TIME = datetime.time(0, 0, 1)
DEFAULT_REGISTRATION_CLOSE_TIME = datetime.time(23, 59, 59)