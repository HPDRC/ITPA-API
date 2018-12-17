# itpa URL Configuration

from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers

from itpa import views, settings

router = routers.DefaultRouter(trailing_slash=True)

urlpatterns = [
    url(r'^$', views.hello),
    url(r'^admin/', admin.site.urls),
    url(r'^auth/', views.CustomAuthToken.as_view()),
    url(r'^api/', include(router.urls)),
    url(r'^user_rights', views.user_rights),
    url(r'^user_list', views.user_list),
    url(r'^login', views.login),
    url(r'^hello', views.hello),
]

if settings.DEBUG is True:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
