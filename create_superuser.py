# create_superuser.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PrNuam3.settings')
django.setup()

from django.contrib.auth.models import User

def create_superuser():
    try:
        # Verificar si ya existe
        if not User.objects.filter(username='profesor').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@demo.com',
                password='admin123'
            )
            print("✅ SUPER USUARIO CREADO: admin / admin123")
        else:
            print("⚠️  El usuario 'admin' ya existe")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    create_superuser()