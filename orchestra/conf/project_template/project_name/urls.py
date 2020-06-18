from django.conf.urls import include, url
from rest_framework_swagger.views import get_swagger_view


schema_view = get_swagger_view(title='Orchestra API')


urlpatterns = [
    url(r'^swagger/$', schema_view),
    url(r'', include('orchestra.urls')),
]
