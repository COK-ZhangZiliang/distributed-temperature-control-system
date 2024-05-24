"""
URL configuration for server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from air_condition.views import *

urlpatterns = [
    # path('admin/', admin.site.urls),  # Django 默认页面
    path('', log_in),
    path('off/', client_off, name='client_off'),  # 默认页面
    path('on/', client_on),  # 开机
    path('power/', power),  # 开关机
    path('high/', change_high),
    path('mid/', change_mid),
    path('low/', change_low),
    path('up/', change_up),
    path('down/', change_down),

    # 空调管理员
    path('init/', init, name='init'),
    path('init_submit/', init_submit),
    path('monitor/', monitor),

    # 前台
    path('recp/', reception_init),
    path('recp_submit/', reception),

    # 经理
    path('manager/', manager),
    path('manager_month/', manager_month),
    path('manager_week/', manager_week),
]
