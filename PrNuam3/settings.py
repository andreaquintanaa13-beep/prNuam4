"""
Configuración Django para PrNuam3 - Versión Simplificada y Segura
"""

import os
from pathlib import Path

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# ========== CONFIGURACIÓN BÁSICA Y SEGURA ==========

# 1. CLAVE SECRETA (usa la que ya tenías)
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_temporal_para_local')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# 3. HOSTS PERMITIDOS (dónde puede correr tu app)
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.onrender.com',  # Para cuando subas a Render
]

# ========== APPS Y MIDDLEWARE ==========

# 4. APLICACIONES QUE USA TU PROYECTO
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'NuamApp',  # Tu aplicación
]

# 5. MIDDLEWARE (como filtros de seguridad)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # ¡IMPORTANTE!
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'NuamApp.middleware.CheckUserStateMiddleware',
]

# ========== URLs Y TEMPLATES ==========

# 6. ARCHIVO PRINCIPAL DE URLs
ROOT_URLCONF = 'PrNuam3.urls'

# 7. CONFIGURACIÓN DE PLANTILLAS HTML
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Carpeta donde están tus HTML
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ========== BASE DE DATOS ==========

# 8. BASE DE DATOS (SQLite es más fácil para empezar)
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}


# ========== CONTRASEÑAS ==========

# 9. VALIDACIÓN DE CONTRASEÑAS
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# ========== IDIOMA Y ZONA HORARIA ==========

# 10. IDIOMA ESPAÑOL CHILE
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ========== ARCHIVOS ESTÁTICOS ==========

# 11. ARCHIVOS CSS, JS, IMÁGENES
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para producción
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise para servir archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ========== ARCHIVOS SUBIDOS POR USUARIOS ==========

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== CONFIGURACIÓN DE LOGIN ==========

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_corredor'
LOGOUT_REDIRECT_URL = 'login'

# ========== SEGURIDAD PARA PRODUCCIÓN ==========

# 12. ESTO SE ACTIVA CUANDO DEBUG=False
if not DEBUG:
    # HTTPS obligatorio
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Headers de seguridad
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Prevenir clickjacking
    X_FRAME_OPTIONS = 'DENY'

# ========== CONFIGURACIÓN DE SESIONES ==========

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 semanas

# ========== CONFIGURACIÓN POR DEFECTO ==========

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'