from django.db import models
from django.db.models import Q


class ClubManager(models.Manager):
    def for_user(self, user):
        if user.is_superuser:
            return self.all()
        return self.filter(Q(admins__in=[user]) | Q(departments__admins__in=[user]))


class DepartmentManager(models.Manager):
    def for_user(self, user):
        if user.is_superuser:
            return self.all()
        return self.filter(Q(admins__in=[user]))
