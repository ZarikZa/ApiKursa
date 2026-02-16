from rest_framework import permissions
from .models import Applicant, Employee
class ResponsePermission(permissions.BasePermission):
    """
    Права доступа для откликов
    """
    def has_permission(self, request, view):
        # Разрешаем всем аутентифицированным пользователям
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Администраторы имеют полный доступ
        if user.user_type == 'adminsite' or user.is_superuser:
            return True
        
        # Соискатели могут видеть только свои отклики
        if user.user_type == 'applicant':
            try:
                return obj.applicants == user.applicant
            except Applicant.DoesNotExist:
                return False
        
        # Компания-владелец или сотрудник компании могут видеть отклики на вакансии своей компании
        if user.user_type in ['company', 'staff']:
            try:
                employee = user.employee
                return obj.vacancy.company == employee.company
            except Employee.DoesNotExist:
                return False
        
        return False
    
from rest_framework.permissions import BasePermission

class CanManageVacancyVideo(BasePermission):
    """
    Доступ:
    - Django superuser
    - user_type = adminsite
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.user_type == 'adminsite'

class IsContentManager(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'employee')
            and request.user.employee.role == 'content_manager'
        )

class IsSameCompany(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.company == request.user.employee.company
