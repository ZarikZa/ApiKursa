from rest_framework import permissions
from .models import Applicant, Employee


class IsAdminSite(permissions.BasePermission):
    """Администратор сайта (user_type=adminsite) или superuser."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or getattr(u, 'user_type', None) == 'adminsite'))


class IsCompanyOwner(permissions.BasePermission):
    """Владелец компании (user_type=company)."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, 'user_type', None) == 'company')


class IsCompanyOwnerOrStaff(permissions.BasePermission):
    """Владелец компании или сотрудник (staff)."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, 'user_type', None) in ('company', 'staff'))


class ResponsePermission(permissions.BasePermission):
    """
    Права доступа для откликов
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.user_type == 'adminsite' or user.is_superuser:
            return True
        
        if user.user_type == 'applicant':
            try:
                return obj.applicants == user.applicant
            except Applicant.DoesNotExist:
                return False
        
        if user.user_type in ['company', 'staff']:
            try:
                # company owner
                if user.user_type == 'company':
                    company = getattr(user, 'company', None)
                    return bool(company and obj.vacancy.company_id == company.id)

                # staff
                employee = user.employee
                return bool(employee.company and obj.vacancy.company_id == employee.company_id)
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
