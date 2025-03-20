# myapp/urls.py

from django.urls import path
from . import views

app_name = 'probe_app'

urlpatterns = [
    path('orbitar_login/', views.orbitar_login, name='orbitar_login'),
    path('callback_orbitar/', views.callback_orbitar, name='callback_orbitar'),
    path('orbitar_all_feed_posts/', views.orbitar_all_feed_posts, name='orbitar_all_feed_posts'),
    path('orbitar_all_feed_posts/<str:sort_by>/', views.orbitar_all_feed_posts, name='orbitar_all_feed_posts_sorted'),]
