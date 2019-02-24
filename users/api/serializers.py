from rest_framework import serializers

from clublink.clubs.models import Club
from clublink.users.models import Address, ClubCorp, Profile, User, UserCategory, UserType


class ClubCorpSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubCorp
        fields = (
            'id',
            'name',
        )


class UserCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCategory
        fields = (
            'id',
            'name',
        )


class UserTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserType
        fields = (
            'id',
            'name',
            'is_corp',
        )


class MemberAddressSerializer(serializers.ModelSerializer):
    membership_number = serializers.SlugRelatedField(
        'membership_number', source='user', write_only=True,
        queryset=User.objects.exclude(membership_number=None))

    class Meta:
        model = Address
        fields = (
            'type',
            'membership_number',
            'address1',
            'address2',
            'cell_phone',
            'city',
            'country',
            'email',
            'phone',
            'state',
            'postal_code',
        )


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            'joined',
            'title',
            'dob',
            'gender',
            'employer',
            'position',
            'statement_cycle_id',
            'show_in_roster',
            'prepaid_cart',
            'email_dues_notice',
            'email_statement',
            'subscribe_score',
            'subscribe_clublink_info',
            'subscribe_club_info',
        )


class MemberRosterSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('pk', 'first_name', 'last_name', 'display_name')

    def get_display_name(self, obj):
        return '{} {} ({})'.format(
            obj.first_name,
            obj.last_name,
            obj.option_club.name
        )


class UserSerializer(serializers.ModelSerializer):
    middle_name = serializers.CharField(required=False)
    category = serializers.PrimaryKeyRelatedField(
        queryset=UserCategory.objects.all(), required=False)
    clubcorp = serializers.PrimaryKeyRelatedField(
        queryset=ClubCorp.objects.all(), required=False)
    home_club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all(), required=False)
    home_club_alternate_1 = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(), required=False)
    home_club_alternate_2 = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(), required=False)
    option_club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.all(), required=False)
    type = serializers.PrimaryKeyRelatedField(queryset=UserType.objects.all(), required=False)
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'membership_number',
            'first_name',
            'last_name',
            'middle_name',
            'email',
            'is_active',
            'is_staff',
            'category',
            'clubcorp',
            'clubcorp_number',
            'customer_id',
            'home_club',
            'home_club_alternate_1',
            'home_club_alternate_2',
            'option_club',
            'preferred_language',
            'status',
            'type',
            'profile',
        )

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        user = super().create(validated_data)
        Profile.objects.update_or_create(user=user, defaults=profile_data)
        return user

    def update(self, instance, validated_data):
        if 'profile' in validated_data:
            profile_data = validated_data.pop('profile')
            Profile.objects.update_or_create(user=instance, defaults=profile_data)
        return super().update(instance, validated_data)


class MemberSerializer(UserSerializer):
    membership_number = serializers.CharField(required=True)
    home_club = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field='code', required=False)
    home_club_alternate_1 = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field='code', required=False)
    home_club_alternate_2 = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field='code', required=False)
    option_club = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field='code', required=False)
    is_staff = serializers.BooleanField(read_only=True)
