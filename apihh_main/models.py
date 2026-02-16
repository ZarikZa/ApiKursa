import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=80)
    
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username', 'phone'] 
    
    USER_TYPE_CHOICES = (
        ('applicant', 'Соискатель'),
        ('company', 'Владелец компании'),
        ('staff', 'Сотрудник компании'),
        ('adminsite', 'Администратор сайта'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='applicant')
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
      
class Company(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'На проверке'),
        (STATUS_APPROVED, 'Подтверждена'),
        (STATUS_REJECTED, 'Отклонена'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=10)
    industry = models.CharField(max_length=100)
    description = models.TextField()
    theme = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Статус аккаунта'
    )
    verification_document = models.FileField(
        upload_to='company_documents/%Y/%m/%d/',
        verbose_name='Подтверждающий документ (PDF)',
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Загрузите документ в формате PDF'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
    
    def __str__(self):
        return self.name
    
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

class Applicant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    resume = models.TextField(blank=True)
    theme = models.CharField(max_length=100, blank=True, null=True) 

    class Meta:
        db_table = 'applicants'
        verbose_name = 'Соискатель'
        verbose_name_plural = 'Соискатели'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def add_to_favorites(self, vacancy):
        favorite, created = Favorites.objects.get_or_create(
            applicant=self,
            vacancy=vacancy
        )
        return created
    
    def remove_from_favorites(self, vacancy):
        Favorites.objects.filter(applicant=self, vacancy=vacancy).delete()
    
    def get_favorites(self):
        return self.favorite_vacancies.all()
    
    def is_in_favorites(self, vacancy):
        return Favorites.objects.filter(applicant=self, vacancy=vacancy).exists()


class Skill(models.Model):
    """Справочник навыков (для теста/профиля навыков)."""

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        db_table = 'skills'
        verbose_name = 'Навык'
        verbose_name_plural = 'Навыки'

    def __str__(self):
        return self.name


class ApplicantSkill(models.Model):
    """Оценка навыка соискателя по шкале 1..5."""

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'applicant_skills'
        verbose_name = 'Навык соискателя'
        verbose_name_plural = 'Навыки соискателей'
        unique_together = ('applicant', 'skill')

class Employee(models.Model):
    ROLE_CHOICES = (
        ('site_admin', 'Администратор сайта'),
        ('hr', 'HR агент'),
        ('content_manager', 'Контент-менеджер'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='employees'
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)


class WorkConditions(models.Model):
    work_conditions_name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'work_conditions'
        verbose_name = 'Условие работы'
        verbose_name_plural = 'Условия работы'
    
    def __str__(self):
        return self.work_conditions_name

class StatusVacancies(models.Model):
    status_vacancies_name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'status_vacancies'
        verbose_name = 'Статус вакансии'
        verbose_name_plural = 'Статусы вакансий'
    
    def __str__(self):
        return self.status_vacancies_name

class StatusResponse(models.Model):
    status_response_name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'status_responses'
        verbose_name = 'Статус отклика'
        verbose_name_plural = 'Статусы откликов'
    
    def __str__(self):
        return self.status_response_name
    
class Vacancy(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)  
    work_conditions = models.ForeignKey('WorkConditions', on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    created_date = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey('StatusVacancies', on_delete=models.CASCADE)
    views = models.PositiveIntegerField(default=0)
    experience = models.CharField(max_length=20, choices=[
        ('Без опыта', 'Без опыта'),
        ('1-3 года', '1-3 года'),
        ('3-6 лет', '3-6 лет'),
        ('от 6 лет', 'от 6 лет'),
    ], blank=True, null=True)
    city = models.CharField(max_length=100, default='Москва')  
    category = models.CharField(max_length=50, choices=[
        ('IT', 'IT'),
        ('Маркетинг', 'Маркетинг'),
        ('Продажи', 'Продажи'),
        ('HR', 'HR'),
    ], default='IT') 
    work_conditions_details = models.TextField(blank=True, null=True) 

    class Meta:
        db_table = 'vacancies'
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
    
    def __str__(self):
        return f"{self.position} - {self.company.name}"
    
    
from django.utils import timezone
class Complaint(models.Model):
    COMPLAINT_TYPES = [
        ('spam', 'Спам'),
        ('fraud', 'Мошенничество'),
        ('inappropriate', 'Неуместный контент'),
        ('discrimination', 'Дискриминация'),
        ('false_info', 'Ложная информация'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('reviewed', 'Рассмотрено'),
        ('rejected', 'Отклонено'),
        ('resolved', 'Решено'),
    ]
    
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, verbose_name="Вакансия")
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Подавший жалобу")
    complaint_type = models.CharField(max_length=50, choices=COMPLAINT_TYPES, verbose_name="Тип жалобы")
    description = models.TextField(verbose_name="Описание проблемы", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата решения")
    admin_notes = models.TextField(blank=True, verbose_name="Заметки администратора")
    
    class Meta:
        db_table = 'complaints'
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
        unique_together = ['vacancy', 'complainant'] 
    
    def __str__(self):
        return f"Жалоба на {self.vacancy.position} от {self.complainant.email}"
    
    def save(self, *args, **kwargs):
        if self.status != 'pending' and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

class Response(models.Model):
    applicants = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE)
    response_date = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(StatusResponse, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'responses'
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        unique_together = ['applicants', 'vacancy']
    
    def __str__(self):
        return f"Отклик {self.applicants} на {self.vacancy}"

class Favorites(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, verbose_name="Соискатель")
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, verbose_name="Вакансия")
    added_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    
    class Meta:
        db_table = 'favorites'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные вакансии'
        unique_together = ['applicant', 'vacancy']
    
    def __str__(self):
        return f"{self.applicant} - {self.vacancy}"
    
class ActionType(models.Model):
    """Типы действий для логирования"""
    code = models.CharField(max_length=50, unique=True, verbose_name='Код действия')
    name = models.CharField(max_length=100, verbose_name='Название действия')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Тип действия'
        verbose_name_plural = 'Типы действий'
    
    def __str__(self):
        return self.name

class AdminLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    action = models.ForeignKey(ActionType, on_delete=models.CASCADE, verbose_name='Действие')
    target_company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Целевая компания')
    target_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID целевого объекта')
    target_content_type = models.CharField(max_length=100, blank=True, verbose_name='Тип целевого объекта')
    details = models.TextField(blank=True, verbose_name='Детали')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Лог действий'
        verbose_name_plural = 'Логи действий'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.admin.username} - {self.action.name} - {self.created_at}"

class Backup(models.Model):
    BACKUP_TYPES = [
        ('full', 'Полный бэкап'),
        ('database', 'Только база данных'),
        ('media', 'Только медиафайлы'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Название бэкапа')
    backup_file = models.FileField(upload_to='backups/%Y/%m/%d/', verbose_name='Файл бэкапа')
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES, default='database')
    file_size = models.BigIntegerField(default=0, verbose_name='Размер файла')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создан')
    
    class Meta:
        verbose_name = 'Бэкап'
        verbose_name_plural = 'Бэкапы'
        ordering = ['-created_at']
    
    def delete(self, *args, **kwargs):
        if self.backup_file:
            if os.path.isfile(self.backup_file.path):
                os.remove(self.backup_file.path)
        super().delete(*args, **kwargs)
    
    def get_file_size_display(self):
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = self.file_size
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.2f} {size_names[i]}"
    
    def __str__(self):
        return self.name
    
# models.py - обновляем модель Chat
class Chat(models.Model):
    """Чат по вакансии между соискателем и компанией"""
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, verbose_name="Вакансия")
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, verbose_name="Соискатель")
    
    # Убираем company_representative, так как доступ у всех сотрудников
    # Вместо этого связываем с компанией напрямую
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Компания")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    last_message_at = models.DateTimeField(auto_now=True, verbose_name="Последнее сообщение")
    
    class Meta:
        db_table = 'chats'
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        unique_together = ['vacancy', 'applicant']
        ordering = ['-last_message_at']  # Сортировка по последнему сообщению
    
    def __str__(self):
        return f"Чат по вакансии '{self.vacancy.position}' с {self.applicant}"
    
    def save(self, *args, **kwargs):
        # Автоматически определяем компанию из вакансии
        if not self.company_id and self.vacancy_id:
            self.company = self.vacancy.company
        super().save(*args, **kwargs)

class Message(models.Model):
    """Сообщение в чате"""
    MESSAGE_TYPES = [
        ('text', 'Текст'),
        ('system', 'Системное'),
        ('file', 'Файл'),
    ]
    
    SENDER_TYPES = [
        ('applicant', 'Соискатель'),
        ('company', 'Компания'),
        ('hr-agent', 'HR-агент'),
    ]
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name="Чат")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")  

    # Кто отправил
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Отправитель")
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES, verbose_name="Тип отправителя")
    
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text', verbose_name="Тип сообщения")
    text = models.TextField(verbose_name="Текст сообщения")
    
    # Для системных сообщений
    system_action = models.CharField(max_length=50, blank=True, null=True, verbose_name="Системное действие")
    
    # Ссылки
    related_vacancy = models.ForeignKey(Vacancy, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Связанная вакансия")
    related_response = models.ForeignKey(Response, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Связанный отклик")
    
    is_read_by_applicant = models.BooleanField(default=False, verbose_name="Прочитано соискателем")
    is_read_by_company = models.BooleanField(default=False, verbose_name="Прочитано компанией")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Сообщение от {self.sender.email} ({self.created_at})"
    
    def save(self, *args, **kwargs):
        # Автоматически определяем sender_type
        if not self.sender_type:
            if self.sender.user_type == 'applicant':
                self.sender_type = 'applicant'
            else:
                self.sender_type = 'company'
        super().save(*args, **kwargs)

class VacancyVideo(models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='Вакансия'
    )

    uploaded_by = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='videos'
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE)


    video = models.FileField(
        upload_to='vacancy_videos/%Y/%m/%d/',
        verbose_name='Видео файл'
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Описание'
    )

    is_active = models.BooleanField(
        default=False,
        verbose_name='Активно'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.uploaded_by.company != self.company:
            raise ValueError('Компания видео не совпадает с компанией сотрудника')

        if self.vacancy.company != self.company:
            raise ValueError('Видео можно добавлять только к вакансиям своей компании')

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'vacancy_videos'
        verbose_name = 'Видео вакансии'
        verbose_name_plural = 'Видео вакансий'
        ordering = ['-created_at']

    def __str__(self):
        return f"Видео для {self.vacancy.position}"



class VacancyVideoView(models.Model):
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE
    )
    video = models.ForeignKey(
        VacancyVideo,
        on_delete=models.CASCADE
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vacancy_video_views'
        unique_together = ('applicant', 'video')

class VacancyVideoLike(models.Model):
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE
    )
    video = models.ForeignKey(
        VacancyVideo,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vacancy_video_likes'
        unique_together = ('applicant', 'video')
