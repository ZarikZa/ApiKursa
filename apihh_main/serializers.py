from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import *

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'phone', 'password', 'password2', 'user_type')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone', 'user_type', 'first_name', 'last_name')
        read_only_fields = ('id', 'user_type')

class CompanySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ('created_at', 'status')

class CompanyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'status', 'admin_notes')
    
    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        
        # Логируем действие
        AdminLog.objects.create(
            admin=self.context['request'].user,
            action='company_approved' if instance.status == Company.STATUS_APPROVED else 'company_rejected',
            target_company=instance,
            details=f"Статус изменен на {instance.get_status_display()}"
        )
        return instance

class ApplicantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='__str__', read_only=True)
    
    class Meta:
        model = Applicant
        fields = '__all__'


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('id', 'name')


class ApplicantSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = ApplicantSkill
        fields = ('id', 'skill', 'skill_name', 'level')

    def validate_level(self, v):
        if v < 1 or v > 5:
            raise serializers.ValidationError('level должен быть от 1 до 5')
        return v


class ApplicantSkillUpsertSerializer(serializers.Serializer):
    """Приём пачки оценок навыков (upsert)."""

    skill_id = serializers.IntegerField()
    level = serializers.IntegerField(min_value=1, max_value=5)

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Employee
        fields = '__all__'

class WorkConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkConditions
        fields = '__all__'

class StatusVacanciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusVacancies
        fields = '__all__'

class StatusResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusResponse
        fields = '__all__'

class VacancyListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    work_conditions_name = serializers.CharField(source='work_conditions.work_conditions_name', read_only=True)
    status_name = serializers.CharField(source='status.status_vacancies_name', read_only=True)

    has_video = serializers.SerializerMethodField()
    video_id = serializers.SerializerMethodField()

    class Meta:
        model = Vacancy
        fields = (
            'id', 'position', 'company_name',
            'salary_min', 'salary_max',
            'city', 'category', 'experience',
            'work_conditions_name', 'status_name',
            'views', 'created_date',
            'has_video', 'video_id',
        )

    def get_has_video(self, obj):
        return obj.videos.exists()

    def get_video_id(self, obj):
        v = obj.videos.order_by('-created_at').first()
        return v.id if v else None


class VacancyDetailSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    work_conditions_name = serializers.CharField(source='work_conditions.work_conditions_name', read_only=True)
    status_name = serializers.CharField(source='status.status_vacancies_name', read_only=True)
    has_applied = serializers.SerializerMethodField()  # Убедитесь, что это поле есть!
    is_favorite = serializers.SerializerMethodField()
    
    class Meta:
        model = Vacancy
        fields = '__all__'
    
    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                applicant = request.user.applicant
                return Response.objects.filter(applicants=applicant, vacancy=obj).exists()
            except Applicant.DoesNotExist:
                return False
        return False
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                applicant = request.user.applicant
                return Favorites.objects.filter(applicant=applicant, vacancy=obj).exists()
            except Applicant.DoesNotExist:
                return False
        return False

class ComplaintSerializer(serializers.ModelSerializer):
    complainant_email = serializers.CharField(source='complainant.email', read_only=True)
    vacancy_position = serializers.CharField(source='vacancy.position', read_only=True)
    company_name = serializers.CharField(source='vacancy.company.name', read_only=True)
    
    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = ('complainant', 'created_at', 'resolved_at', 'status')

# serializers.py
from rest_framework import serializers
from .models import Response, StatusResponse, Applicant, Vacancy

class ResponseSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicants.__str__', read_only=True)
    vacancy_position = serializers.CharField(source='vacancy.position', read_only=True)
    company_name = serializers.CharField(source='vacancy.company.name', read_only=True)
    status_name = serializers.CharField(source='status.status_response_name', read_only=True)
    vacancy_id = serializers.IntegerField(source='vacancy.id', read_only=True)
    company_id = serializers.IntegerField(source='vacancy.company.id', read_only=True)
    
    class Meta:
        model = Response
        fields = [
            'id',
            'applicant_name',
            'vacancy_position',
            'company_name',
            'status_name',
            'vacancy_id',
            'company_id',
            'response_date',
            'status',  # только для чтения в этом сериализаторе
            'applicants'  # только для чтения
        ]
        read_only_fields = [
            'id', 'response_date', 'status', 'applicants',
            'applicant_name', 'vacancy_position', 'company_name', 
            'status_name', 'vacancy_id', 'company_id'
        ]

class CreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['vacancy']  # Только эти поля можно отправлять
    
    def validate(self, data):
        user = self.context['request'].user
        
        if user.user_type != 'applicant':
            raise serializers.ValidationError("Только соискатели могут создавать отклики")
        
        try:
            applicant = user.applicant
        except Applicant.DoesNotExist:
            raise serializers.ValidationError("Профиль соискателя не найден")
        
        # Проверяем вакансию
        vacancy = data.get('vacancy')
        if not vacancy:
            raise serializers.ValidationError({"vacancy": "Вакансия обязательна"})
        
        # Проверяем, активна ли вакансия
        if hasattr(vacancy, 'is_active') and not vacancy.is_active:
            raise serializers.ValidationError("Нельзя откликнуться на неактивную вакансию")
        
        # Проверяем, не откликался ли уже
        if Response.objects.filter(applicants=applicant, vacancy=vacancy).exists():
            raise serializers.ValidationError("Вы уже откликались на эту вакансию")
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        applicant = user.applicant
        
        # Получаем статус по умолчанию
        try:
            default_status = StatusResponse.objects.get(status_response_name="Отправлен")
        except StatusResponse.DoesNotExist:
            # Если нет статуса "Отправлен", берем первый доступный
            default_status = StatusResponse.objects.first()
            if not default_status:
                raise serializers.ValidationError("Нет доступных статусов отклика")
        
        # Создаем отклик
        response = Response.objects.create(
            applicants=applicant,
            status=default_status,
            **validated_data
        )
        return response

class CheckResponseSerializer(serializers.Serializer):
    has_responded = serializers.BooleanField()
    response_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    
    def to_representation(self, instance):
        """
        instance - это словарь с данными о отклике
        """
        return {
            'has_responded': instance['has_responded'],
            'response_id': instance['response_id'],
            'status': instance['status']
        }

class FavoritesSerializer(serializers.ModelSerializer):
    vacancy_details = VacancyListSerializer(source='vacancy', read_only=True)
    
    class Meta:
        model = Favorites
        fields = ('id', 'vacancy', 'vacancy_details', 'added_date')
        read_only_fields = ('added_date',)

class AdminLogSerializer(serializers.ModelSerializer):
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    company_name = serializers.CharField(source='target_company.name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AdminLog
        fields = '__all__'

class BackupSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    
    class Meta:
        model = Backup
        fields = '__all__'
        read_only_fields = ('file_size', 'created_at')


class BaseUserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'phone', 'password', 'password2')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

# Регистрация соискателя
class ApplicantRegistrationSerializer(BaseUserRegistrationSerializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    birth_date = serializers.DateField()
    resume = serializers.CharField(required=False, allow_blank=True)
    
    class Meta(BaseUserRegistrationSerializer.Meta):
        fields = BaseUserRegistrationSerializer.Meta.fields + (
            'first_name', 'last_name', 'birth_date', 'resume'
        )
    
    def create(self, validated_data):
        # Извлекаем данные для Applicant
        applicant_data = {
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'birth_date': validated_data.pop('birth_date'),
            'resume': validated_data.pop('resume', '')
        }
        
        # Создаем пользователя
        validated_data.pop('password2')
        validated_data['user_type'] = 'applicant'
        user = User.objects.create_user(**validated_data)
        
        # Создаем Applicant
        Applicant.objects.create(user=user, **applicant_data)
        
        return user

# Регистрация компании
class CompanyRegistrationSerializer(BaseUserRegistrationSerializer):
    name = serializers.CharField(max_length=100)
    number = serializers.CharField(max_length=10)
    industry = serializers.CharField(max_length=100)
    description = serializers.CharField()
    verification_document = serializers.FileField(
        validators=[FileExtensionValidator(['pdf'])]
    )
    
    class Meta(BaseUserRegistrationSerializer.Meta):
        fields = BaseUserRegistrationSerializer.Meta.fields + (
            'name', 'number', 'industry', 'description', 'verification_document'
        )
    
    def create(self, validated_data):
        # Извлекаем данные для Company
        company_data = {
            'name': validated_data.pop('name'),
            'number': validated_data.pop('number'),
            'industry': validated_data.pop('industry'),
            'description': validated_data.pop('description'),
            'verification_document': validated_data.pop('verification_document')
        }
        
        # Создаем пользователя
        validated_data.pop('password2')
        validated_data['user_type'] = 'company'
        user = User.objects.create_user(**validated_data)
        
        # Создаем Company
        Company.objects.create(user=user, **company_data)
        
        return user

class EmployeeRegistrationSerializer(BaseUserRegistrationSerializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    role = serializers.ChoiceField(choices=[
        ('hr', 'HR агент'),
        ('content_manager', 'Контент-менеджер'),
        ('site_admin', 'Администратор сайта'),
    ])
    company_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta(BaseUserRegistrationSerializer.Meta):
        fields = BaseUserRegistrationSerializer.Meta.fields + (
            'first_name', 'last_name', 'role', 'company_id'
        )
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        
        # Для сотрудников компании (HR/Content Manager) компания обязательна
        if attrs.get('role') in ['hr', 'content_manager'] and not attrs.get('company_id'):
            raise serializers.ValidationError({
                "company_id": "Для HR-агента необходимо указать компанию"
            })
        
        return attrs
    
    def create(self, validated_data):
        # Извлекаем данные для Employee
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        role = validated_data.pop('role')
        
        company_id = validated_data.pop('company_id', None)
        
        # Создаем пользователя
        validated_data.pop('password2')
        # user_type для сотрудников — staff, для админа сайта — adminsite
        validated_data['user_type'] = 'adminsite' if role == 'site_admin' else 'staff'
        user = User.objects.create_user(**validated_data)
        
        company = None
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                raise serializers.ValidationError({"company_id": "Компания не найдена"})

        # Создаем Employee
        employee = Employee.objects.create(user=user, company=company, role=role)
        # Дублируем ФИО в User (удобно для админки/чата)
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])
        return user

# Сериализатор для отображения пользователя
class UserSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone', 'user_type', 
                 'user_type_display', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined')

# Детальный сериализатор с информацией о профиле
class UserProfileSerializer(serializers.ModelSerializer):
    # Поля из User
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    user_type = serializers.CharField(read_only=True)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    employee_role = serializers.SerializerMethodField(read_only=True)
    company_id = serializers.SerializerMethodField(read_only=True)

    # Поля, которые можно редактировать
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    # Поля из Applicant (только для соискателей)
    applicant_id = serializers.SerializerMethodField(read_only=True)
    birth_date = serializers.DateField(source='applicant.birth_date', required=False, allow_null=True)
    resume = serializers.CharField(source='applicant.resume', required=False, allow_blank=True, allow_null=True)
    # theme = serializers.CharField(source='applicant.theme', required=False, allow_blank=True)  # если есть

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'user_type', 'user_type_display',
            'first_name', 'last_name',
            'applicant_id', 'birth_date', 'resume',
            'employee_role', 'company_id',
        ]
        read_only_fields = ('id', 'username', 'email', 'user_type', 'user_type_display', 'applicant_id')

    def get_applicant_id(self, obj):
        try:
            return obj.applicant.id
        except Applicant.DoesNotExist:
            return None
        
    def get_employee_role(self, obj):
        try:
            return obj.employee.role
        except Employee.DoesNotExist:
            return None

    def get_company_id(self, obj):
        try:
            emp = obj.employee
            return emp.company_id
        except Employee.DoesNotExist:
            return None


    def update(self, instance, validated_data):
        # Обновляем поля User
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()

        # Обновляем Applicant, если данные пришли и пользователь — соискатель
        if instance.user_type == 'applicant':
            applicant_data = {}
            if 'birth_date' in validated_data:
                applicant_data['birth_date'] = validated_data.pop('birth_date')
            if 'resume' in validated_data:
                applicant_data['resume'] = validated_data.pop('resume')

            if applicant_data:
                try:
                    applicant = instance.applicant
                    for attr, value in applicant_data.items():
                        setattr(applicant, attr, value)
                    applicant.save()
                except Applicant.DoesNotExist:
                    # Если аппликанта нет — можно создать (но обычно он создаётся при регистрации)
                    Applicant.objects.create(user=instance, **applicant_data)

        return instance
    
# serializers.py
class ChatSerializer(serializers.ModelSerializer):
    vacancy_title = serializers.CharField(source='vacancy.position', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    applicant_name = serializers.CharField(source='applicant.__str__', read_only=True)
    
    # Информация о вакансии
    vacancy_info = serializers.SerializerMethodField()
    
    # Информация о соискателе
    applicant_info = serializers.SerializerMethodField()
    
    # Кто может писать в чат (сотрудники компании)
    company_users = serializers.SerializerMethodField()
    
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'vacancy', 'vacancy_title', 'vacancy_info',
            'company', 'company_name', 'company_users',
            'applicant', 'applicant_name', 'applicant_info',
            'created_at', 'last_message_at', 'last_message',
            'unread_count', 'is_active'
        ]
        read_only_fields = ['created_at', 'last_message_at']
    
    def get_vacancy_info(self, obj):
        return {
            'id': obj.vacancy.id,
            'position': obj.vacancy.position,
            'salary_min': obj.vacancy.salary_min,
            'salary_max': obj.vacancy.salary_max,
            'city': obj.vacancy.city,
        }
    
    def get_applicant_info(self, obj):
        return {
            'id': obj.applicant.id,
            'full_name': f"{obj.applicant.first_name} {obj.applicant.last_name}",
            'email': obj.applicant.user.email,
            'phone': obj.applicant.user.phone,
        }
    
    def get_company_users(self, obj):
        """Сотрудники компании, которые могут писать в чат"""
        # Все сотрудники компании + сама компания (user)
        users = []
        
        # Добавляем пользователя компании
        if obj.company.user:
            users.append({
                'id': obj.company.user.id,
                'email': obj.company.user.email,
                'name': obj.company.name,
                'type': 'company_owner'
            })
        
        # Добавляем сотрудников
        employees = Employee.objects.filter(company=obj.company)
        for emp in employees:
            if emp.user:
                users.append({
                    'id': emp.user.id,
                    'email': emp.user.email,
                    'name': f"{emp.user.first_name} {emp.user.last_name}",
                    'type': emp.user.user_type
                })
        
        return users
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'text': last_msg.text[:100] + ('...' if len(last_msg.text) > 100 else ''),
                'sender_type': last_msg.sender_type,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        user = self.context['request'].user
        
        if user.user_type == 'applicant':
            # Для соискателя - непрочитанные сообщения от компании
            return obj.messages.filter(
                sender_type='company',
                is_read_by_applicant=False
            ).count()
        else:
            # Для компании - непрочитанные сообщения от соискателя
            return obj.messages.filter(
                sender_type='applicant',
                is_read_by_company=False
            ).count()
        

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    sender_name = serializers.SerializerMethodField()
    is_my_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'text', 'sender_email', 'sender_name',
            'is_my_message', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_sender_name(self, obj):
        sender = obj.sender
        if hasattr(sender, 'applicant'):
            return f"{sender.applicant.first_name} {sender.applicant.last_name}"
        elif hasattr(sender, 'company'):
            return sender.company.name
        return sender.email
    
    def get_is_my_message(self, obj):
        return obj.sender == self.context['request'].user

class SendMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text']
    
    def create(self, validated_data):
        return Message.objects.create(**validated_data)

class VacancyShortSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Vacancy
        fields = (
            'id',
            'position',
            'salary_min',
            'salary_max',
            'city',
            'company_name',
        )

class VacancyVideoFeedSerializer(serializers.ModelSerializer):
    vacancy = VacancyShortSerializer(read_only=True)

    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = VacancyVideo
        fields = (
            'id',
            'video',
            'description',
            'created_at',
            'vacancy',
            'likes_count',
            'is_liked',
        )

    def get_likes_count(self, obj):
        return obj.vacancyvideolike_set.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        try:
            applicant = request.user.applicant
        except:
            return False

        return obj.vacancyvideolike_set.filter(applicant=applicant).exists()



from rest_framework import serializers
from .models import VacancyVideo
from .utils import validate_video

class VacancyVideoAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = VacancyVideo
        fields = (
            'id',
            'vacancy',
            'video',
            'description',
            'is_active',
        )
        read_only_fields = ('is_active',)

    def create(self, validated_data):
        request = self.context['request']
        employee = request.user.employee

        instance = VacancyVideo.objects.create(
            uploaded_by=employee,
            company=employee.company,
            **validated_data
        )

        errors = validate_video(
            instance.video.path,
            instance.video.size
        )

        if not errors:
            instance.is_active = True
            instance.save()
        else:
            instance.is_active = False
            instance.save()

        return instance

class ContentManagerCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    company_id = serializers.IntegerField(write_only=True)  # ✅ ДОБАВЬ

    class Meta:
        model = Employee
        fields = ('email', 'password', 'first_name', 'last_name', 'company_id')  # ✅ ДОБАВЬ

    def create(self, validated_data):
        company = Company.objects.get(id=validated_data["company_id"])

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            user_type='staff'
        )

        return Employee.objects.create(
            user=user,
            role='content_manager',
            company=company
        )



class ContentManagerVideoSerializer(serializers.ModelSerializer):
    # отдаём нормальный URL на файл
    video = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VacancyVideo
        fields = ('id', 'vacancy', 'video', 'description', 'is_active')
        read_only_fields = ('id', 'video', 'is_active')

    def get_video(self, obj):
        request = self.context.get("request")
        if obj.video and hasattr(obj.video, "url"):
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None

    def validate_vacancy(self, value):
        user = self.context['request'].user

        if not hasattr(user, 'employee') or user.employee.role != 'content_manager':
            raise serializers.ValidationError("Только контент-менеджер может добавлять видео")

        if value.company != user.employee.company:
            raise serializers.ValidationError("Нельзя загружать видео для чужой компании")

        return value

    def create(self, validated_data):
        request = self.context['request']
        employee = request.user.employee

        # video файл берётся из request.FILES (MultiPartParser)
        video_file = request.FILES.get("video")
        if not video_file:
            raise serializers.ValidationError({"video": "Файл видео обязателен"})

        instance = VacancyVideo.objects.create(
            uploaded_by=employee,
            company=employee.company,
            video=video_file,
            **validated_data
        )

        # если хочешь модерацию — оставь False и убери автоактивацию
        # но я оставляю твою логику: валидное видео -> active True
        try:
            errors = validate_video(instance.video.path, instance.video.size)
        except Exception:
            errors = ["validate_error"]

        instance.is_active = (not errors)
        instance.save()
        return instance


class ContentManagerVideoListSerializer(serializers.ModelSerializer):
    video = serializers.SerializerMethodField(read_only=True)
    vacancy_position = serializers.CharField(source='vacancy.position', read_only=True)
    likes_count = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()

    class Meta:
        model = VacancyVideo
        fields = (
            'id', 'video', 'description',
            'vacancy', 'vacancy_position',
            'likes_count', 'views_count',
            'is_active'
        )

    def get_video(self, obj):
        request = self.context.get("request")
        if obj.video and hasattr(obj.video, "url"):
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None

    def get_likes_count(self, obj):
        return obj.vacancyvideolike_set.count()

    def get_views_count(self, obj):
        return obj.vacancyvideoview_set.count()