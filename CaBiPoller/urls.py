"""CaBiPoller URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.views.generic import TemplateView

from stations import views

urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'nobikes', views.nobikes, name='nobikes'),
	url(r'nodocks', views.nodocks, name='nodocks'),
	url(r'station/(?P<id>\d+)/', views.station_detail, name='station_detail'),
	url(r'status/about', TemplateView.as_view(template_name='status/about.html'), name='about'),
    url(r'^admin/', admin.site.urls),
]
