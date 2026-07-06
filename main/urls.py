from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('register/', views.register, name='register'),

    # Story
    path('story/<int:story_id>/', views.story_detail, name='story_detail'),
    path('story/create/', views.create_story, name='create_story'),
    path('story/<int:story_id>/edit/', views.edit_story, name='edit_story'),
    path('story/<int:story_id>/delete/', views.delete_story, name='delete_story'),
    path('story/file/<int:file_id>/', views.download_story_file, name='download_story_file'),

    # Challenge
    path('challenge/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    path('story/<int:story_id>/challenge/create/', views.create_challenge, name='create_challenge'),
    path('challenge/<int:challenge_id>/edit/', views.edit_challenge, name='edit_challenge'),
    path('challenge/<int:challenge_id>/delete/', views.delete_challenge, name='delete_challenge'),

    # Task
    path('challenge/<int:challenge_id>/task/create/', views.create_task, name='create_task'),
    path('task/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),

    # Files
    path('challenge/file/<int:file_id>/', views.download_challenge_file, name='download_challenge_file'),
]
