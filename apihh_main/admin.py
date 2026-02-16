from django.contrib import admin

from .models import *
    
@admin.register(Applicant)
class AplicatAdmin(admin.ModelAdmin):
    pass

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    pass

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    pass

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    pass

@admin.register(StatusVacancies)
class StatusVacanciesAdmin(admin.ModelAdmin):
    pass

@admin.register(StatusResponse)
class StatusResponseAdmin(admin.ModelAdmin):
    pass

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    pass

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    pass

@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    pass

@admin.register(User)
class User(admin.ModelAdmin):
    pass


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['vacancy', 'complainant', 'complaint_type', 'status', 'created_at']
    list_filter = ['status', 'complaint_type', 'created_at']
    search_fields = ['vacancy__position', 'complainant__email', 'description']
    readonly_fields = ['created_at']
    actions = ['mark_as_resolved', 'mark_as_rejected']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
        self.message_user(request, f'{queryset.count()} жалоб отмечено как решенные')
    
    def mark_as_rejected(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} жалоб отклонено')
    
    mark_as_resolved.short_description = "Отметить выбранные жалобы как решенные"
    mark_as_rejected.short_description = "Отклонить выбранные жалобы"

@admin.register(VacancyVideo)
class VacancyVideoAdmin(admin.ModelAdmin):
    pass

@admin.register(VacancyVideoView)
class VacancyVideoViewAdmin(admin.ModelAdmin):
    pass

@admin.register(VacancyVideoLike)
class VacancyVideoLikeAdmin(admin.ModelAdmin):
    pass

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    pass