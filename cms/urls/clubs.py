from django.conf.urls import url

from clublink.cms import views


urlpatterns = [
    url(r'^__cms__/richtext_snippet/$', views.RichTextSnippetView.as_view(),
        name='cms.richtext_snippet'),
    url(r'^__cms__/image/$', views.ImageView.as_view(), name='cms.image'),
]
