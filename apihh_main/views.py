from rest_framework.response import Response as R

from .pagination import VacancyPagination
from .models import *
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from .filters import VacancyFilter

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserRegistrationSerializer, UserSerializer
from .jwt_serializers import CustomTokenObtainPairSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

from django.db.models import Exists, OuterRef

class VacancyViewSet(viewsets.ModelViewSet):
    queryset = Vacancy.objects.all()
    serializer_class = VacancyListSerializer  # ← ВАЖНО

    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = VacancyFilter

    ordering_fields = ['created_date', 'salary_min', 'salary_max']
    ordering = ['-created_date']

    pagination_class = VacancyPagination

    def get_queryset(self):
        queryset = Vacancy.objects.select_related(
            'company', 'work_conditions', 'status'
        )

        user = self.request.user
        if user.is_authenticated:
            try:
                applicant = user.applicant
                queryset = queryset.annotate(
                    is_favorite=Exists(
                        Favorites.objects.filter(
                            applicant=applicant,
                            vacancy=OuterRef('pk')
                        )
                    ),
                    has_applied=Exists(
                        Response.objects.filter(
                            applicants=applicant,
                            vacancy=OuterRef('pk')
                        )
                    )
                )
            except Applicant.DoesNotExist:
                pass

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VacancyDetailSerializer
        return VacancyListSerializer

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'put'], url_path='me/skills')
    def me_skills(self, request):
        # текущий соискатель
        try:
            applicant = request.user.applicant
        except Applicant.DoesNotExist:
            return R({"detail": "Профиль соискателя не найден"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ GET: вернуть текущие навыки
        if request.method == 'GET':
            qs = ApplicantSkill.objects.filter(applicant=applicant).select_related('skill').order_by('skill__name')
            return R(ApplicantSkillSerializer(qs, many=True).data)

        # ✅ PUT: принять пачку и сохранить (upsert)
        skills = request.data.get('skills', None)
        if not isinstance(skills, list):
            return R(
                {"detail": "Ожидается {\"skills\": [{\"skill_id\":1,\"level\":5}] }"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # валидируем пачку
        ser = ApplicantSkillUpsertSerializer(data=skills, many=True)
        ser.is_valid(raise_exception=True)

        # upsert
        for item in ser.validated_data:
            skill_id = item['skill_id']
            level = item['level']

            try:
                skill = Skill.objects.get(id=skill_id)
            except Skill.DoesNotExist:
                return R({"detail": f"Skill id={skill_id} не найден"}, status=status.HTTP_400_BAD_REQUEST)

            ApplicantSkill.objects.update_or_create(
                applicant=applicant,
                skill=skill,
                defaults={'level': level}
            )

        qs = ApplicantSkill.objects.filter(applicant=applicant).select_related('skill').order_by('skill__name')
        return R(ApplicantSkillSerializer(qs, many=True).data, status=status.HTTP_200_OK)

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class ResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления откликами.
    Использует разные сериализаторы для разных действий.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Фильтруем отклики в зависимости от типа пользователя.
        """
        user = self.request.user
        
        # Базовая оптимизация запросов
        queryset = Response.objects.select_related(
            'applicants',
            'vacancy',
            'vacancy__company',
            'status'
        ).all()
        
        # Если пользователь - соискатель, показываем только его отклики
        if user.user_type == 'applicant':
            try:
                applicant = user.applicant
                return queryset.filter(applicants=applicant)
            except Applicant.DoesNotExist:
                logger.warning(f"Applicant profile not found for user {user.id}")
                return Response.objects.none()
        
        # Если пользователь - работодатель, показываем отклики на его вакансии
        elif user.user_type == 'employer':
            try:
                # Получаем компанию работодателя
                employee = user.employee
                company = employee.company
                
                # Получаем все вакансии компании
                company_vacancies = Vacancy.objects.filter(company=company)
                
                # Фильтруем отклики на вакансии компании
                return queryset.filter(vacancy__in=company_vacancies)
            except (Employee.DoesNotExist, AttributeError):
                logger.warning(f"Employee profile not found for user {user.id}")
                return Response.objects.none()
        
        # Для администратора - показываем все отклики
        elif user.user_type == 'admin':
            return queryset
        
        # Для остальных пользователей - пустой queryset
        else:
            return Response.objects.none()
    
    def get_serializer_class(self):
        """
        Используем разные сериализаторы для разных действий.
        """
        if self.action == 'create':
            return CreateResponseSerializer
        elif self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return ResponseSerializer
        return ResponseSerializer
    
    def perform_create(self, serializer):
        """
        Автоматически назначаем соискателя при создании отклика.
        Этот метод теперь будет использовать CreateResponseSerializer,
        который сам устанавливает applicant и status.
        """
        # Валидация уже выполнена в сериализаторе
        serializer.save()
    
    def create(self, request, *args, **kwargs):
        """
        Переопределяем для лучшего логирования.
        """
        logger.info(f"Creating response. User: {request.user.id}, Type: {request.user.user_type}")
        logger.info(f"Request data: {request.data}")
        
        return super().create(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """
        Обновление отклика (например, изменение статуса работодателем).
        """
        user = self.request.user
        
        # Если пользователь - соискатель, проверяем что он обновляет свой отклик
        if user.user_type == 'applicant':
            try:
                applicant = user.applicant
                if serializer.instance.applicants != applicant:
                    raise PermissionDenied("Вы не можете изменять чужой отклик")
            except Applicant.DoesNotExist:
                raise ValidationError("Профиль соискателя не найден")
        
        # Если пользователь - работодатель, проверяем что отклик на его вакансию
        elif user.user_type == 'employer':
            try:
                employee = user.employee
                company = employee.company
                if serializer.instance.vacancy.company != company:
                    raise PermissionDenied("Вы не можете изменять отклики на чужие вакансии")
            except Employee.DoesNotExist:
                raise ValidationError("Профиль работодателя не найден")
        
        serializer.save()
    
    @action(detail=False, methods=['get'], url_path='check/(?P<vacancy_id>\d+)')
    def check_response(self, request, vacancy_id=None):
        """
        Проверяет, откликнулся ли текущий пользователь на вакансию.
        """
        user = request.user
        
        # Логируем информацию о пользователе
        logger.info(f"Check response: user_id={user.id}, user_type={user.user_type}, email={user.email}")
        logger.info(f"Vacancy ID: {vacancy_id}")
        
        # Только соискатели могут откликаться на вакансии
        if user.user_type != 'applicant':
            logger.warning(f"User {user.id} is not applicant (type: {user.user_type})")
            return Response(
                {"error": "Только соискатели могут откликаться на вакансии"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Получаем объект соискателя
            logger.info(f"Looking for Applicant with user_id={user.id}")
            applicant = user.applicant
            logger.info(f"Found applicant: {applicant.id}")
            
            # Получаем вакансию
            vacancy = Vacancy.objects.get(id=vacancy_id)
            logger.info(f"Found vacancy: {vacancy.id} - {vacancy.position}")
            
            # Проверяем, есть ли отклик
            try:
                response = Response.objects.get(applicants=applicant, vacancy=vacancy)
                logger.info(f"Found existing response: {response.id}, status: {response.status.status_response_name}")
                
                data = {
                    'has_responded': True,
                    'response_id': response.id,
                    'status': response.status.status_response_name
                }
            except Response.DoesNotExist:
                logger.info(f"No existing response found for applicant {applicant.id} on vacancy {vacancy.id}")
                data = {
                    'has_responded': False,
                    'response_id': None,
                    'status': None
                }
            
            serializer = CheckResponseSerializer(data)
            return Response(serializer.data)
            
        except Vacancy.DoesNotExist:
            logger.error(f"Vacancy {vacancy_id} not found")
            return Response(
                {"error": "Вакансия не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Applicant.DoesNotExist:
            logger.error(f"Applicant not found for user {user.id}")
            return Response(
                {"error": "Профиль соискателя не найден"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in check_response: {str(e)}")
            return Response(
                {"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Эндпоинт для обновления статуса отклика (для работодателей).
        """
        user = request.user
        
        if user.user_type != 'employer':
            return Response(
                {"error": "Только работодатели могут изменять статус отклика"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            response = self.get_object()
            new_status_id = request.data.get('status_id')
            
            if not new_status_id:
                return Response(
                    {"error": "Не указан ID нового статуса"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                new_status = StatusResponse.objects.get(id=new_status_id)
            except StatusResponse.DoesNotExist:
                return Response(
                    {"error": "Указанный статус не найден"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем, что работодатель имеет доступ к этой вакансии
            employee = user.employee
            if response.vacancy.company != employee.company:
                return Response(
                    {"error": "Вы не можете изменять статус отклика на чужую вакансию"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Обновляем статус
            response.status = new_status
            response.save()
            
            return Response({
                "message": "Статус отклика обновлен",
                "new_status": new_status.status_response_name,
                "response_id": response.id
            })
            
        except Response.DoesNotExist:
            return Response(
                {"error": "Отклик не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Employee.DoesNotExist:
            return Response(
                {"error": "Профиль работодателя не найден"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating response status: {str(e)}")
            return Response(
                {"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class FavoritesViewSet(viewsets.ModelViewSet):
    serializer_class = FavoritesSerializer
    permission_classes = [IsAuthenticated]
    queryset = Favorites.objects.all()
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.user_type != 'applicant':
            return Favorites.objects.none()

        try:
            applicant = user.applicant
        except Applicant.DoesNotExist:
            return Favorites.objects.none()

        return Favorites.objects.filter(applicant=applicant).select_related('vacancy', 'vacancy__company')

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type != 'applicant':
            # 403
            raise PermissionDenied("Только соискатель может добавлять вакансии в избранное")
        serializer.save(applicant=user.applicant)

    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle(self, request):
        """POST /api/favorites/toggle/ body: {"vacancy": <id>}"""
        user = request.user
        if user.user_type != 'applicant':
            return R({"error": "Только для соискателя"}, status=status.HTTP_403_FORBIDDEN)

        vacancy_id = request.data.get('vacancy')
        if not vacancy_id:
            return R({"error": "vacancy обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        vacancy = get_object_or_404(Vacancy, id=vacancy_id)
        applicant = user.applicant

        fav = Favorites.objects.filter(applicant=applicant, vacancy=vacancy).first()
        if fav:
            fav.delete()
            return R({"is_favorite": False}, status=status.HTTP_200_OK)

        Favorites.objects.create(applicant=applicant, vacancy=vacancy)
        return R({"is_favorite": True}, status=status.HTTP_200_OK)


class WorkConditionsViewSet(viewsets.ModelViewSet):
    queryset = WorkConditions.objects.all()
    serializer_class = WorkConditionsSerializer

class StatusVacanciesViewSet(viewsets.ModelViewSet):
    queryset = StatusVacancies.objects.all()
    serializer_class = StatusVacanciesSerializer

class StatusResponseViewSet(viewsets.ModelViewSet):
    queryset = StatusResponse.objects.all()
    serializer_class = StatusResponseSerializer

class AdminLogViewSet(viewsets.ModelViewSet):
    queryset = AdminLog.objects.all()
    serializer_class = AdminLogSerializer

class BackupViewSet(viewsets.ModelViewSet):
    queryset = Backup.objects.all()
    serializer_class = BackupSerializer

class UserViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action in ['register_applicant', 'register_company', 'register_employee']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'register_applicant':
            return ApplicantRegistrationSerializer
        elif self.action == 'register_company':
            return CompanyRegistrationSerializer
        elif self.action == 'register_employee':
            return EmployeeRegistrationSerializer
        elif self.action in ['profile', 'update_profile']:
            return UserProfileSerializer
        return UserSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register_applicant(self, request):
        """Регистрация соискателя"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return R({
                'user': UserSerializer(user).data,
                'message': 'Соискатель успешно зарегистрирован'
            }, status=status.HTTP_201_CREATED)
        return R(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register_company(self, request):
        """Регистрация компании"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return ReRsponse({
                'user': UserSerializer(user).data,
                'message': 'Компания успешно зарегистрирована и ожидает проверки'
            }, status=status.HTTP_201_CREATED)
        return R(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register_employee(self, request):
        """Регистрация HR-агента, Аналитика или Админа сайта"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return R({
                'user': UserSerializer(user).data,
                'message': f'{user.get_user_type_display()} успешно зарегистрирован'
            }, status=status.HTTP_201_CREATED)
        return R(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'patch', 'put'], url_path='profile', permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        GET: Получить полный профиль текущего пользователя
        PATCH/PUT: Обновить профиль (PATCH — частичное обновление)
        """
        user = request.user

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return R(serializer.data)

        # Обновление (PATCH или PUT)
        serializer = self.get_serializer(user, data=request.data, partial=(request.method == 'PATCH'))
        if serializer.is_valid():
            updated_user = serializer.save()

            # Возвращаем обновлённый профиль
            updated_serializer = self.get_serializer(updated_user)
            return R(updated_serializer.data)

        return R(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class ChatViewSet(viewsets.ModelViewSet):
    """Вьюсет для чатов с доступом для всех сотрудников компании"""
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтрация чатов по текущему пользователю"""
        user = self.request.user
        
        if user.user_type == 'applicant':
            # Соискатель видит только свои чаты
            return Chat.objects.filter(applicant=user.applicant)
        
        elif user.user_type == 'company':
            # Компания видит все чаты по своим вакансиям
            company = user.company
            return Chat.objects.filter(company=company)
        
        elif user.user_type in ['hragent', 'employee']:
            # Сотрудник/HR видят чаты своей компании
            try:
                employee = user.employee
                if employee.company:
                    return Chat.objects.filter(company=employee.company)
                else:
                    # Если сотрудник без компании, нет чатов
                    return Chat.objects.none()
            except Employee.DoesNotExist:
                return Chat.objects.none()
        
        return Chat.objects.none()
    
    def perform_create(self, serializer):
        """Автоматическое создание чата при отклике"""
        # Обычно чат создается автоматически, но на всякий случай
        user = self.request.user
        
        if user.user_type != 'applicant':
            raise serializers.ValidationError("Только соискатель может создавать чат через отклик")
        
        # Получаем данные
        vacancy_id = self.request.data.get('vacancy')
        
        try:
            vacancy = Vacancy.objects.get(id=vacancy_id)
            applicant = user.applicant
            
            # Проверяем, есть ли уже отклик
            response_exists = Response.objects.filter(
                applicants=applicant,
                vacancy=vacancy
            ).exists()
            
            if not response_exists:
                raise serializers.ValidationError("Сначала нужно откликнуться на вакансию")
            
            # Сохраняем чат
            chat = serializer.save(
                applicant=applicant,
                company=vacancy.company,
                vacancy=vacancy
            )
            
            # Создаем первое системное сообщение
            Message.objects.create(
                chat=chat,
                sender=user,
                sender_type='applicant',
                message_type='system',
                text=f"Соискатель откликнулся на вакансию '{vacancy.position}'",
                system_action='response_created',
                related_vacancy=vacancy,
                is_read_by_company=False,
                is_read_by_applicant=True
            )
            
        except Vacancy.DoesNotExist:
            raise serializers.ValidationError("Вакансия не найдена")
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Получить сообщения чата"""
        chat = self.get_object()
        user = request.user
        
        # Помечаем сообщения как прочитанные
        if user.user_type == 'applicant':
            # Соискатель прочитал сообщения компании
            chat.messages.filter(sender_type='company', is_read_by_applicant=False).update(is_read_by_applicant=True)
        else:
            # Компания прочитала сообщения соискателя
            chat.messages.filter(sender_type='applicant', is_read_by_company=False).update(is_read_by_company=True)
        
        messages = chat.messages.all().order_by('created_at')
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return R(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Отправить сообщение в чат"""
        chat = self.get_object()
        user = request.user
        
        # Проверяем, имеет ли пользователь доступ к чату
        if user.user_type == 'applicant':
            if chat.applicant.user != user:
                return R(
                    {"error": "Нет доступа к этому чату"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Для сотрудников компании проверяем, что чат принадлежит их компании
            try:
                if user.user_type == 'company':
                    user_company = user.company
                else:
                    # Для сотрудников/HR
                    user_company = user.employee.company
                
                if chat.company != user_company:
                    return R(
                        {"error": "Нет доступа к этому чату"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except (Company.DoesNotExist, Employee.DoesNotExist):
                return R(
                    {"error": "Нет доступа к этому чату"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = SendMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            # Определяем тип отправителя
            sender_type = 'applicant' if user.user_type == 'applicant' else 'company'
            
            message = serializer.save(
                chat=chat,
                sender=user,
                sender_type=sender_type,
                # Помечаем как прочитанное отправителем
                is_read_by_applicant=(sender_type == 'applicant'),
                is_read_by_company=(sender_type == 'company')
            )
            
            # Обновляем время последнего сообщения в чате
            chat.last_message_at = message.created_at
            chat.save()
            
            return R(MessageSerializer(message, context={'request': request}).data, 
                          status=status.HTTP_201_CREATED)
        
        return R(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_vacancy(self, request):
        """Получить чат по конкретной вакансии (для соискателя)"""
        vacancy_id = request.query_params.get('vacancy_id')
        user = request.user
        
        if not vacancy_id:
            return R({"error": "vacancy_id обязателен"}, status=400)
        
        if user.user_type != 'applicant':
            return R({"error": "Только для соискателей"}, status=403)
        
        try:
            vacancy = Vacancy.objects.get(id=vacancy_id)
            applicant = user.applicant
            
            # Ищем существующий чат
            chat = Chat.objects.filter(vacancy=vacancy, applicant=applicant).first()
            
            if chat:
                return R(ChatSerializer(chat, context={'request': request}).data)
            else:
                return R({"exists": False, "message": "Чат не создан. Сначала откликнитесь на вакансию."})
                
        except Vacancy.DoesNotExist:
            return R({"error": "Вакансия не найдена"}, status=404)
        
class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для сообщений (только чтение)"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтрация сообщений по доступным чатам"""
        user = self.request.user
        
        if user.user_type == 'applicant':
            try:
                applicant = user.applicant
                # Соискатель видит сообщения только из своих чатов
                chats = Chat.objects.filter(applicant=applicant)
                return Message.objects.filter(chat__in=chats)
            except Applicant.DoesNotExist:
                return Message.objects.none()
        
        elif user.user_type == 'company':
            try:
                company = user.company
                chats = Chat.objects.filter(company=company)
                return Message.objects.filter(chat__in=chats)
            except Company.DoesNotExist:
                return Message.objects.none()
        
        elif user.user_type in ['hragent', 'employee']:
            try:
                employee = user.employee
                if employee.company:
                    chats = Chat.objects.filter(company=employee.company)
                    return Message.objects.filter(chat__in=chats)
            except Employee.DoesNotExist:
                pass
        
        return Message.objects.none()

from rest_framework.parsers import MultiPartParser, FormParser
from .permissions import IsContentManager

class VacancyVideoManageViewSet(viewsets.ModelViewSet):
    queryset = VacancyVideo.objects.all()
    serializer_class = VacancyVideoAdminSerializer
    permission_classes = [IsAuthenticated, IsContentManager]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        employee = self.request.user.employee

        # Проверяем, что вакансия принадлежит компании сотрудника
        if serializer.validated_data['vacancy'].company != employee.company:
            raise PermissionDenied("Нельзя загружать видео для чужой компании")

        serializer.save(
            uploaded_by=self.request.user,
            is_active=False  # на будущее — модерация
        )


from django.shortcuts import get_object_or_404


from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import PermissionDenied

from .models import (
    VacancyVideo, VacancyVideoView, VacancyVideoLike
)
from .serializers import (
    ContentManagerVideoSerializer,
    ContentManagerVideoListSerializer,
    VacancyVideoFeedSerializer
)
from .permissions import IsContentManager


class ContentManagerVideoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsContentManager]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'employee') or not user.employee or not user.employee.company_id:
            return VacancyVideo.objects.none()

        # твоя логика: видео по вакансиям компании
        return VacancyVideo.objects.filter(vacancy__company=user.employee.company).order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ContentManagerVideoListSerializer
        return ContentManagerVideoSerializer

    def perform_create(self, serializer):
        employee = self.request.user.employee
        vacancy = serializer.validated_data['vacancy']

        if vacancy.company != employee.company:
            raise PermissionDenied("Нельзя загружать видео для чужой компании")

        # ВАЖНО: сохраняем!
        serializer.save()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        video = self.get_object()
        video.is_active = True
        video.save()
        return R({"status": "видео активировано", "video_id": video.id})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        video = self.get_object()
        video.is_active = False
        video.save()
        return R({"status": "видео деактивировано", "video_id": video.id})

class VacancyVideoFeedViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = VacancyVideoFeedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        applicant = self.request.user.applicant
        params = self.request.query_params

        qs = VacancyVideo.objects.filter(
            is_active=True
        ).select_related('vacancy', 'vacancy__company')

        # Исключаем просмотренные видео
        viewed = VacancyVideoView.objects.filter(
            applicant=applicant
        ).values_list('video_id', flat=True)
        qs = qs.exclude(id__in=viewed)

        # Фильтрация по параметрам
        if city := params.get('city'):
            qs = qs.filter(vacancy__city__iexact=city)
        if category := params.get('category'):
            qs = qs.filter(vacancy__category=category)
        if salary_from := params.get('salary_from'):
            qs = qs.filter(vacancy__salary_max__gte=salary_from)

        return qs

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        """Отметить видео как просмотренное"""
        video = get_object_or_404(VacancyVideo, pk=pk)
        VacancyVideoView.objects.get_or_create(
            applicant=request.user.applicant,
            video=video
        )
        return R({"status": "ok"})

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Лайк/анлайк видео"""
        video = get_object_or_404(VacancyVideo, pk=pk)
        applicant = request.user.applicant

        like_obj = VacancyVideoLike.objects.filter(applicant=applicant, video=video).first()
        if like_obj:
            like_obj.delete()
            return R({"liked": False})
        VacancyVideoLike.objects.create(applicant=applicant, video=video)
        return R({"liked": True})

from rest_framework.generics import ListAPIView

class VacancyVideoFeedView(ListAPIView):
    serializer_class = VacancyVideoFeedSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return VacancyVideo.objects.filter(
            is_active=True
        ).select_related(
            'vacancy',
            'vacancy__company'
        )

class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Skill.objects.all().order_by('name')
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ContentManagerVacancyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsContentManager]
    serializer_class = VacancyListSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "employee") or not user.employee or not user.employee.company_id:
            return Vacancy.objects.none()

        return Vacancy.objects.filter(company=user.employee.company).order_by('-created_date')


class RecommendedVideoFeedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VacancyVideoFeedSerializer

    def get_queryset(self):
        # пока просто активные видео, позже сделаем умную сортировку
        return VacancyVideo.objects.filter(is_active=True).order_by('-id')