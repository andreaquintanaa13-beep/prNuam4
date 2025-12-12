# NuamApp/decorators.py
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import time
from .security_utils import get_client_ip

# ========== DECORADORES DE AUTENTICACIÓN ==========

def login_required_custom(view_func):
    """Decorador mejorado para verificar login"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            messages.error(request, 'Debes iniciar sesión para acceder')
            return redirect('login')
        
        # Verificar que el usuario todavía existe
        from .models import Usuario
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            
            # Verificar estado del usuario
            if usuario.estado.lower() != 'activo':
                messages.error(request, 'Tu cuenta está desactivada. Contacta al administrador.')
                request.session.flush()
                return redirect('login')
                
        except Usuario.DoesNotExist:
            # Usuario eliminado, limpiar sesión
            request.session.flush()
            messages.error(request, 'Tu sesión ha expirado')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    """Solo permite acceso a ciertos roles"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = request.session.get('rol')
            
            if user_role not in allowed_roles:
                messages.error(request, 'No tienes permisos para acceder a esta sección')
                return HttpResponseForbidden('Acceso denegado')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def admin_required(view_func):
    """Solo administradores"""
    return role_required(['admin'])(view_func)

def corredor_required(view_func):
    """Solo corredores"""
    return role_required(['corredor'])(view_func)

# ========== DECORADORES DE SEGURIDAD ==========

def prevent_brute_force(view_func):
    """Prevenir ataques de fuerza bruta en login"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST' and 'login' in request.path:
            ip = get_client_ip(request)
            key = f'login_attempts:{ip}'
            
            attempts = cache.get(key, 0)
            if attempts >= 10:  # 10 intentos fallidos
                messages.error(request, 'Demasiados intentos fallidos. Contacte al administrador.')
                return HttpResponseForbidden('Acceso bloqueado temporalmente')
            
            response = view_func(request, *args, **kwargs)
            
            # Si el login falló, incrementar contador
            if 'usuario_id' not in request.session:
                cache.set(key, attempts + 1, 300)  # 5 minutos
            else:
                # Login exitoso, resetear contador
                cache.delete(key)
            
            return response
        
        return view_func(request, *args, **kwargs)
    return wrapper

def require_https(view_func):
    """Forzar HTTPS en producción"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return redirect(f'https://{request.get_host()}{request.path}')
        return view_func(request, *args, **kwargs)
    return wrapper

def rate_limit(max_requests=5, window=60):
    """Decorador para rate limiting"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request)
            view_name = view_func.__name__
            key = f'ratelimit:{ip}:{view_name}'
            
            attempts = cache.get(key, [])
            now = time.time()
            
            # Filtrar intentos fuera de la ventana de tiempo
            attempts = [attempt for attempt in attempts if now - attempt < window]
            
            if len(attempts) >= max_requests:
                return JsonResponse({
                    'error': 'Demasiadas solicitudes. Intente más tarde.'
                }, status=429)
            
            attempts.append(now)
            cache.set(key, attempts, window)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def audit_action(action_type, model_name=None):
    """Decorador para auditar acciones"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Ejecutar la vista
            response = view_func(request, *args, **kwargs)
            
            # Registrar en auditoría si está autenticado
            if 'usuario_id' in request.session:
                from .models import Auditoria, Usuario
                try:
                    usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
                    
                    Auditoria.objects.create(
                        accion=action_type,
                        fecha_hora=timezone.now(),
                        resultado=f'{action_type} desde {get_client_ip(request)}',
                        fk_usuario=usuario,
                        detalles={
                            'path': request.path,
                            'method': request.method,
                            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        }
                    )
                except:
                    pass
            
            return response
        return wrapper
    return decorator

def validate_csrf_exempt_for_api(view_func):
    """Valida CSRF para APIs (excepción controlada)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Verificar token CSRF o API key
            csrf_token = request.headers.get('X-CSRF-Token') or request.POST.get('csrfmiddlewaretoken')
            api_key = request.headers.get('X-API-Key')
            
            if not csrf_token and not api_key:
                return JsonResponse({'error': 'Token CSRF o API Key requerido'}, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper

def prevent_clickjacking(view_func):
    """Previene clickjacking agregando headers"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        if hasattr(response, 'headers'):
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        
        return response
    return wrapper

def sanitize_inputs(view_func):
    """Sanitiza todos los inputs de la request"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .security_utils import sanitize_input
        
        # Sanitizar GET parameters
        if request.GET:
            sanitized_get = {}
            for key, value in request.GET.items():
                sanitized_get[key] = sanitize_input(value)
            request.GET = sanitized_get
        
        # Sanitizar POST parameters
        if request.POST:
            sanitized_post = {}
            for key, value in request.POST.items():
                sanitized_post[key] = sanitize_input(value)
            request.POST = sanitized_post
        
        return view_func(request, *args, **kwargs)
    return wrapper

# Import timezone para el decorador de auditoría
from django.utils import timezone