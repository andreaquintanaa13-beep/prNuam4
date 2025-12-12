# NuamApp/middleware.py
from django.shortcuts import redirect
from django.contrib import messages

class CheckUserStateMiddleware:
    """Middleware simple para verificar estado de usuario"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verifica si el usuario está logueado
        if request.user.is_authenticated:
            # Aquí puedes agregar más verificaciones si necesitas
            pass
        
        response = self.get_response(request)
        return response