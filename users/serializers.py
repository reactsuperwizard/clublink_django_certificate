from rest_framework import serializers
from clublink.users.models import User

class MemberRosterSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('first_name', 'last_name')
