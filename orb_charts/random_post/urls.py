# myapp/urls.py

from django.urls import path
from . import views

app_name = 'random_post'

urlpatterns = [
    path('', views.random_post, name='random_post'), #путь для random_post view
]
