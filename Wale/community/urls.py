from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('',                         views.feed,          name='feed'),
    path('post/new/',                views.create_post,   name='create_post'),
    path('post/<int:pk>/',           views.post_detail,   name='post_detail'),
    path('post/<int:pk>/like/',      views.like_post,     name='like_post'),
    path('chat/',                    views.chat_list,     name='chat_list'),
    path('chat/<slug:slug>/',        views.chat_room,     name='chat'),
]
