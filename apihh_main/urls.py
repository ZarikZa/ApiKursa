from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import CustomTokenObtainPairView

router = DefaultRouter()
router.register('companies', views.CompanyViewSet)
router.register('vacancies', views.VacancyViewSet)
router.register('applicants', views.ApplicantViewSet)
router.register('skills', views.SkillViewSet, basename='skill')
router.register('employees', views.EmployeeViewSet)
router.register('complaints', views.ComplaintViewSet)
router.register('responses', views.ResponseViewSet, basename='response')
router.register('favorites', views.FavoritesViewSet)
router.register('work-conditions', views.WorkConditionsViewSet)
router.register('status-vacancies', views.StatusVacanciesViewSet)
router.register('status-responses', views.StatusResponseViewSet)
router.register('admin-logs', views.AdminLogViewSet)
router.register('backups', views.BackupViewSet)
router.register('user', views.UserViewSet, basename='user')
router.register('chats', views.ChatViewSet, basename='chat')
router.register('messages', views.MessageViewSet, basename='message')
router.register(r'feed/videos', views.VacancyVideoFeedViewSet, basename='video-feed')
router.register('vacancy-videos', views.VacancyVideoManageViewSet, basename='vacancy-videos')
router.register('content-manager/videos', views.ContentManagerVideoViewSet, basename='content-manager-videos')
router.register(r'content-manager/vacancies', views.ContentManagerVacancyViewSet, basename='cm-vacancies')
router.register(r'feed/videos/recommended', views.RecommendedVideoFeedViewSet, basename='feed-videos-recommended')

urlpatterns = [
    path('', include(router.urls)),

    path('vacancy-videos/feed/', views.VacancyVideoFeedView.as_view(), name='vacancy-video-feed'),

    path('auth/login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
]
