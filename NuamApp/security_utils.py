# NuamApp/security_utils.py
import re
import hashlib
from datetime import datetime, timedelta
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from django.core.cache import cache
import secrets

# ========== FUNCIONES DE IP Y NETWORKING ==========
def get_client_ip(request):
    """Obtiene la IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def is_valid_ip(ip):
    """Valida que una IP tenga formato válido"""
    # IPv4 simple validation
    ipv4_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(ipv4_pattern, ip)
    if match:
        # Verificar que cada octeto esté entre 0-255
        for octet in match.groups():
            if not 0 <= int(octet) <= 255:
                return False
        return True
    return False

# ========== VALIDACIÓN DE INPUTS ==========

def sanitize_input(text):
    """Limpia texto de posibles ataques XSS"""
    if text is None:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # Eliminar etiquetas HTML peligrosas
    text = strip_tags(text)
    
    # Eliminar caracteres peligrosos
    dangerous_patterns = [
        '<script>', '</script>', 'javascript:', 'onload=', 'onerror=',
        'onclick=', 'onmouseover=', 'eval(', 'document.cookie',
        'window.location', 'alert(', 'confirm(', 'prompt(',
        'vbscript:', 'data:', '&lt;script', '&lt;/script'
    ]
    
    for pattern in dangerous_patterns:
        text = text.replace(pattern, '')
    
    # Limitar longitud para prevenir DoS
    if len(text) > 1000:
        text = text[:1000]
    
    return text.strip()

def validate_no_sql_injection(value):
    """Detecta posibles inyecciones SQL"""
    if value is None:
        return value
    
    if not isinstance(value, str):
        return value
    
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE',
        'UNION', 'JOIN', 'WHERE', 'OR', 'AND', '--', ';', '/*', '*/',
        "' OR '1'='1", '" OR "1"="1', '1=1', '1=1--', 'OR 1=1',
        'EXEC', 'EXECUTE', 'DECLARE', 'XP_', 'SP_'
    ]
    
    value_upper = value.upper()
    for keyword in sql_keywords:
        if keyword in value_upper:
            raise ValidationError('Contenido no permitido detectado')
    
    return value

def validate_email_seguro(email):
    """Valida email con regex seguro"""
    if not email:
        raise ValidationError('Email requerido')
    
    if not isinstance(email, str):
        raise ValidationError('Email inválido')
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError('Email inválido')
    
    # Prevenir inyección SQL
    validate_no_sql_injection(email)
    
    return email.lower()

def validate_password_strength(password):
    """Valida fortaleza de contraseña"""
    errors = []
    
    if not password:
        errors.append('Contraseña requerida')
        return errors
    
    if len(password) < 8:
        errors.append('La contraseña debe tener al menos 8 caracteres')
    
    if not re.search(r'[A-Z]', password):
        errors.append('Debe contener al menos una letra mayúscula')
    
    if not re.search(r'[a-z]', password):
        errors.append('Debe contener al menos una letra minúscula')
    
    if not re.search(r'\d', password):
        errors.append('Debe contener al menos un número')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Debe contener al menos un carácter especial')
    
    # Verificar contraseñas comunes
    common_passwords = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'password1', 'admin', 'welcome', 'contraseña', '123456789',
        '111111', 'sunshine', 'iloveyou', 'princess', 'admin123'
    ]
    
    if password.lower() in common_passwords:
        errors.append('La contraseña es demasiado común')
    
    return errors

# ========== SEGURIDAD DE ARCHIVOS ==========

def validate_file_upload(file):
    """Valida archivos subidos"""
    allowed_extensions = ['.csv', '.pdf', '.txt', '.xlsx', '.xls']
    max_size = 10 * 1024 * 1024  # 10MB
    
    # Verificar que sea un archivo
    if not hasattr(file, 'name'):
        raise ValidationError('Archivo inválido')
    
    # Verificar extensión
    file_name = file.name.lower()
    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        raise ValidationError(f'Tipo de archivo no permitido. Extensiones válidas: {", ".join(allowed_extensions)}')
    
    # Verificar tamaño
    if hasattr(file, 'size') and file.size > max_size:
        raise ValidationError(f'El archivo es demasiado grande (máximo {max_size/1024/1024}MB)')
    
    # Verificar nombre
    if not re.match(r'^[a-zA-Z0-9_\-\.\s]+$', file.name):
        raise ValidationError('Nombre de archivo contiene caracteres inválidos')
    
    return True

def sanitize_filename(filename):
    """Sanitiza nombres de archivo"""
    if not filename:
        return "archivo"
    
    # Eliminar caracteres peligrosos
    filename = re.sub(r'[^\w\-\.]', '_', filename)
    
    # Limitar longitud
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if len(name) > 95:
            name = name[:95]
        filename = f"{name}.{ext}" if ext else name
    
    return filename

# ========== TOKENS Y ENCRIPTACIÓN ==========

def generate_secure_token(length=32):
    """Genera un token seguro"""
    return secrets.token_urlsafe(length)

def generate_csrf_safe_token():
    """Genera token seguro para formularios"""
    import hashlib
    import time
    random_data = secrets.token_bytes(32) + str(time.time()).encode()
    return hashlib.sha256(random_data).hexdigest()

def hash_sensitive_data(data, salt=None):
    """Hashea datos sensibles"""
    if salt is None:
        salt = generate_secure_token(16)
    
    if not isinstance(data, str):
        data = str(data)
    
    return hashlib.sha256((data + salt).encode()).hexdigest()

# ========== RATE LIMITING ==========

def check_rate_limit(ip, action, limit=5, window=60):
    """Verifica rate limiting para una acción"""
    key = f'ratelimit:{ip}:{action}'
    
    attempts = cache.get(key, [])
    now = datetime.now()
    
    # Filtrar intentos fuera de la ventana de tiempo
    attempts = [attempt for attempt in attempts if (now - attempt).seconds < window]
    
    if len(attempts) >= limit:
        return False, limit - len(attempts)
    
    attempts.append(now)
    cache.set(key, attempts, window)
    
    return True, limit - len(attempts)

def reset_rate_limit(ip, action):
    """Resetea el rate limiting para una IP y acción"""
    key = f'ratelimit:{ip}:{action}'
    cache.delete(key)

# ========== AUDITORÍA Y LOGGING ==========

def log_security_event(user, event_type, ip_address, details=None):
    """Registra eventos de seguridad"""
    from .models import Auditoria
    
    try:
        Auditoria.objects.create(
            accion=f"SECURITY_{event_type}",
            fecha_hora=datetime.now(),
            resultado=f"Evento de seguridad: {event_type}",
            fk_usuario=user,
            detalles={
                'ip_address': ip_address,
                'event_type': event_type,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
        )
        return True
    except Exception as e:
        # Fallback logging si la base de datos falla
        print(f"[SECURITY_LOG] {event_type} - IP: {ip_address} - Error: {str(e)}")
        return False

# ========== VALIDACIÓN DE DATOS ==========

def validate_date_not_future(date_str):
    """Valida que una fecha no sea futura"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj > datetime.now().date():
            raise ValidationError('No se permiten fechas futuras')
        return date_obj
    except ValueError:
        raise ValidationError('Formato de fecha inválido. Use YYYY-MM-DD')

def validate_number_range(value, min_val=None, max_val=None):
    """Valida que un número esté en un rango"""
    try:
        num = float(value) if '.' in str(value) else int(value)
        
        if min_val is not None and num < min_val:
            raise ValidationError(f'El valor debe ser mayor o igual a {min_val}')
        
        if max_val is not None and num > max_val:
            raise ValidationError(f'El valor debe ser menor o igual a {max_val}')
        
        return num
    except (ValueError, TypeError):
        raise ValidationError('Valor numérico inválido')

def validate_text_length(text, max_length=1000, field_name="texto"):
    """Valida longitud de texto"""
    if text and len(text) > max_length:
        raise ValidationError(f'{field_name} no puede exceder {max_length} caracteres')
    return text[:max_length] if text else text

# ========== UTILIDADES DE SEGURIDAD ==========

def generate_password_reset_token(user_id):
    """Genera token seguro para restablecimiento de contraseña"""
    import hashlib
    import time
    
    data = f"{user_id}{time.time()}{secrets.token_bytes(16)}"
    token = hashlib.sha256(data.encode()).hexdigest()
    
    # Guardar en cache por 1 hora
    cache.set(f'password_reset:{token}', user_id, 3600)
    
    return token

def verify_password_reset_token(token):
    """Verifica token de restablecimiento de contraseña"""
    user_id = cache.get(f'password_reset:{token}')
    if user_id:
        # Eliminar token después de verificar
        cache.delete(f'password_reset:{token}')
        return user_id
    return None

def escape_html(text):
    """Escapa caracteres HTML para prevenir XSS"""
    if not text:
        return ""
    
    escape_chars = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    for char, escaped in escape_chars.items():
        text = text.replace(char, escaped)
    
    return text

def create_session_fingerprint(request):
    """Crea huella digital para sesión"""
    import hashlib
    
    data = {
        'ip': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    }
    
    fingerprint = hashlib.sha256(str(data).encode()).hexdigest()
    return fingerprint