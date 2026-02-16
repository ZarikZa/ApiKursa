from django.apps import AppConfig


class ApihhMainConfig(AppConfig):
    name = 'apihh_main'
    def ready(self):
        import apihh_main.signals  