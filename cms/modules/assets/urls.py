from django.conf.urls import url

from clublink.cms.modules.assets import views


urlpatterns = [
    url(r'^$', views.AssetsView.as_view(), name='assets.home'),
    url(r'^browser/$', views.FileBrowserView.as_view(), name='assets.browser'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/$', views.FileBrowserView.as_view(),
        name='assets.browser'),
    url(r'^browser/new-folder/$', views.NewFolderView.as_view(), name='assets.browser.new-folder'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/new-folder/$', views.NewFolderView.as_view(),
        name='assets.browser.new-folder'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/delete/$', views.FolderDeleteView.as_view(),
        name='assets.browser.folder-delete'),
    url(r'^browser/new-file/$', views.NewFileView.as_view(), name='assets.browser.new-file'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/new-file/$', views.NewFileView.as_view(),
        name='assets.browser.new-file'),
    url(r'^browser/file/(?P<file_pk>[0-9]+)/delete/$',
        views.FileDeleteView.as_view(), name='assets.browser.file-delete'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/file/(?P<file_pk>[0-9]+)/delete/$',
        views.FileDeleteView.as_view(), name='assets.browser.file-delete'),
    url(r'^browser/(?P<folder_pk>[0-9]+)/new-folder/$', views.NewFolderView.as_view(),
        name='assets.browser.new-folder'),
]
