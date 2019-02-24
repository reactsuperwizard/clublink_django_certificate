from django.http import Http404
from rest_framework import pagination, permissions, status, viewsets
from rest_framework.decorators import detail_route
from rest_framework.views import Response

from clublink.base.api.viewsets import UpdateOrCreateModelViewSet
from clublink.users.api.serializers import (
    ClubCorpSerializer,
    MemberAddressSerializer,
    MemberSerializer,
    UserCategorySerializer,
    UserSerializer,
    UserTypeSerializer,
)
from clublink.users.models import Address, ClubCorp, User, UserCategory, UserType


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [
        permissions.IsAdminUser,
    ]
    pagination_class = pagination.LimitOffsetPagination


class MemberViewSet(UpdateOrCreateModelViewSet):
    queryset = User.objects.exclude(membership_number=None)
    serializer_class = MemberSerializer
    lookup_field = 'membership_number'
    permission_classes = [
        permissions.IsAdminUser,
    ]
    pagination_class = pagination.LimitOffsetPagination


class ClubCorpViewSet(UpdateOrCreateModelViewSet):
    queryset = ClubCorp.objects.all()
    serializer_class = ClubCorpSerializer
    permission_classes = [
        permissions.IsAdminUser,
    ]


class UserCategoryViewSet(UpdateOrCreateModelViewSet):
    queryset = UserCategory.objects.all()
    serializer_class = UserCategorySerializer
    permission_classes = [
        permissions.IsAdminUser,
    ]


class UserTypeViewSet(UpdateOrCreateModelViewSet):
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer
    permission_classes = [
        permissions.IsAdminUser,
    ]


class MemberAddressViewSet(UpdateOrCreateModelViewSet):
    serializer_class = MemberAddressSerializer
    permission_classes = [
        permissions.IsAdminUser,
    ]
    lookup_field = 'type'

    def get_queryset(self):
        membership_number = self.request.resolver_match.kwargs.get('membership_number')

        try:
            user = User.objects.get(membership_number=membership_number)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            raise Http404

        return Address.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        membership_number = kwargs.get('membership_number')
        request.data.update(membership_number=membership_number)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        membership_number = kwargs.get('membership_number')
        request.data.update(membership_number=membership_number)
        return super().update(request, *args, **kwargs)

    @detail_route(methods=['POST'])
    def make_mailing_address(self, request, *args, **kwargs):
        address = self.get_object()
        profile = address.user.profile
        profile.mailing_address = address
        profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(methods=['POST'])
    def make_billing_address(self, request, *args, **kwargs):
        address = self.get_object()
        profile = address.user.profile
        profile.billing_address = address
        profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
