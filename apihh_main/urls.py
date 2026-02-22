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

# company cabinet
router.register(r'company/vacancies', views.CompanyVacancyViewSet, basename='company-vacancies')
router.register(r'company/responses', views.CompanyResponsesViewSet, basename='company-responses')
router.register(r'company/complaints', views.CompanyComplaintsViewSet, basename='company-complaints')
router.register(r'company/employees', views.CompanyEmployeesViewSet, basename='company-employees')

# admin cabinet
router.register(r'admin/companies', views.AdminCompaniesViewSet, basename='admin-companies')
router.register(r'admin/complaints', views.AdminComplaintsViewSet, basename='admin-complaints')
router.register(r'admin/skills', views.AdminSkillViewSet, basename='admin-skills')

urlpatterns = [
    path('', include(router.urls)),

    # company profile without id
    path('company/me/', views.CompanyMeAPIView.as_view(), name='company-me'),
    path('content-manager/profile/stats/', views.ContentManagerProfileStatsAPIView.as_view(), name='cm-profile-stats'),
    path('content-manager/profile/stats/pdf/', views.ContentManagerProfileStatsPdfAPIView.as_view(), name='cm-profile-stats-pdf'),

    path('vacancy-videos/feed/', views.VacancyVideoFeedView.as_view(), name='vacancy-video-feed'),

    path('auth/login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('auth/password-reset/request/', views.PasswordResetRequestAPIView.as_view()),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmAPIView.as_view()),
]
