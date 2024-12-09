from django.conf.urls import include, url, handler500


urlpatterns = [
    url(r'', include('orchestra.urls')),
]

handler500 = 'orchestra.views.error_500'
