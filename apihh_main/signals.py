from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Response, Chat, Message

@receiver(post_save, sender=Response)
def create_chat_on_response(sender, instance, created, **kwargs):
    """Создать чат при создании отклика"""
    if created:
        try:
            # Получаем данные
            vacancy = instance.vacancy
            applicant = instance.applicants
            company = vacancy.company
            
            # Создаем чат, если его еще нет
            chat, created = Chat.objects.get_or_create(
                vacancy=vacancy,
                applicant=applicant,
                defaults={
                    'company': company,
                    'is_active': True
                }
            )
            
            if created:
                # Создаем первое системное сообщение
                Message.objects.create(
                    chat=chat,
                    sender=applicant.user,
                    message_type='system',
                    text=f"Соискатель откликнулся на вакансию '{vacancy.position}'"
                )
                
                print(f"Создан чат #{chat.id} для отклика #{instance.id}")
            else:
                print(f"Чат уже существует #{chat.id}")
                
        except Exception as e:
            print(f"Ошибка при создании чата: {e}")