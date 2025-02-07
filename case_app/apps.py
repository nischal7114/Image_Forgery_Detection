from django.apps import AppConfig

class CaseAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'case_app'

    def ready(self):
        import case_app.signals  # Ensure signals are imported only once
