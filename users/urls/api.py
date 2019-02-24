from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter

from clublink.users.api import views


router = SimpleRouter()
router.register(r'user', views.UserViewSet)
router.register(r'member', views.MemberViewSet)
router.register(r'clubcorp', views.ClubCorpViewSet)
router.register(r'user_category', views.UserCategoryViewSet)
router.register(r'user_type', views.UserTypeViewSet)

address_router = SimpleRouter()
address_router.register('address', views.MemberAddressViewSet, base_name='address')

urlpatterns = [
    url(r'^v1/', include(router.urls)),
    url(r'^v1/member/(?P<membership_number>[^\/]+)/', include(address_router.urls))
]
