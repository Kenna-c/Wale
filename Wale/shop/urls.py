from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('',                          views.home,            name='home'),
    path('shop/',                     views.product_list,    name='product_list'),
    path('search/',                   views.search,          name='search'),
    path('product/<slug:slug>/',      views.product_detail,  name='product_detail'),
    path('favorites/',                views.favorites,       name='favorites'),
    path('favorites/toggle/<int:pk>/',views.toggle_favorite, name='toggle_favorite'),
]