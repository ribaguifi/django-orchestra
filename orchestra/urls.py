from django.contrib import admin
from django.urls import include, re_path
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from orchestra.views import serve_private_media

from . import api
from .utils.apps import isinstalled
from orchestra.contrib.metrics.views import metrics_view

admin.autodiscover()
api.autodiscover()

urlpatterns = [
    # Admin
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^admin_tools/', include('admin_tools.urls')),
    # REST API
    re_path(r'^api/', include(api.router.urls)),
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^api-token-auth/', obtain_auth_token, name='api-token-auth'),
    re_path(r'^media/(.+)/(.+)/(.+)/(.+)/(.+)$', serve_private_media, name='private-media'),
#    re_path(r'search', 'orchestra.views.search', name='search'),

    # METRICS Prometheus
    # re_path(r'^metrics/', include('django_prometheus.urls')),
    re_path(r'^custom_metrics/', metrics_view, name='metrics'),

    # MUSICIAN
    path('panel/', include('orchestra.contrib.musician.urls')),
]


if isinstalled('debug_toolbar'):
    import debug_toolbar
    urlpatterns.append(
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    )
