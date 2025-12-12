# PrNuam3/wsgi.py
"""
WSGI config for PrNuam3 project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PrNuam3.settings')

application = get_wsgi_application()

# Aplicar WhiteNoise para servir archivos estáticos
from whitenoise import WhiteNoise
application = WhiteNoise(application, root=os.path.join(os.path.dirname(__file__), 'staticfiles'))