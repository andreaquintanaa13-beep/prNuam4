from django.apps import AppConfig


class NuamappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'NuamApp'

class NuamappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'NuamApp'

    def ready(self):
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )