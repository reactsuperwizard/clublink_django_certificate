from django.db.models import Q
from rest_framework import viewsets
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from clublink.users.models import User
from clublink.users.api.serializers import MemberRosterSerializer
from clublink.clubs.models import ClubEvent

class MemberRosterViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Show those who have user.profile__show_in_roster = True
    '''
    permission_classes = (IsAuthenticated, )
    queryset = User.objects.filter(
        Q(membership_number__startswith='1') | Q(membership_number__startswith='5')
    ).prefetch_related().order_by('first_name', 'last_name')
    serializer_class = MemberRosterSerializer
    filter_backends = (filters.SearchFilter, )
    search_fields = ('first_name', 'last_name', 'option_club__name',)

    def get_queryset(self):

        ## Only from users within the same country
        queryset = super(MemberRosterViewSet, self).get_queryset().filter(
            option_club__site=self.request.site
        )
        # Allow admins to see all users
        if not self.request.user.is_staff or (self.request.user.is_staff and self.request.user != self.request.member):
            queryset = queryset.filter(profile__show_in_roster=True)

        ## TODO: Upon closer inspection, an event-specific endpoint can/should 
        ## be moved to someting like /api/v1/event/7685/get_possible_registrants
        ## However, there would be significant boilerplate that needs to be written. 
        ## Future rewrites should put in place a more fully-fledged API solution for 
        ## using across the application by a SPA.

        event = self.request.query_params.get('event', None)
        if event:
            eventObj = ClubEvent.objects.get(pk=event)
            # Exclude users already registered for this event
            queryset = queryset.exclude(
                pk__in=eventObj.rsvps.values_list('user__pk', flat=True)
                )

        ## Exclude those already selected in a dropdown
        exclude = self.request.query_params.getlist('except', None)
        if exclude:            
            queryset = queryset.exclude(pk__in=exclude)
        return queryset