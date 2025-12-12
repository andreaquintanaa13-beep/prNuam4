from django import forms
from django.core.validators import RegexValidator, MinLengthValidator, MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from .models import Calificacion, Usuario, Corredor
from .security_utils import sanitize_input, validate_no_sql_injection
import re
from datetime import datetime, date
from django.contrib.auth.hashers import check_password


# forms.py
from django import forms
from .models import Calificacion, Corredor, Usuario

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['fecha', 'mercado', 'ano', 'descripcion', 'factor_actualizado', 'instrumento', 'secuencia_evento']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mercado': forms.Select(attrs={'class': 'form-control'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'factor_actualizado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'instrumento': forms.TextInput(attrs={'class': 'form-control'}),
            'secuencia_evento': forms.NumberInput(attrs={'class': 'form-control', 'min': '10001'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.corredor = kwargs.pop('corredor', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.corredor:
            instance.fk_id_corredor = self.corredor
        if commit:
            instance.save()
        return instance
    
    # ========== VALIDACIONES DE SEGURIDAD ==========
    
    def clean_instrumento(self):
        """Valida que el instrumento sea seguro"""
        instrumento = self.cleaned_data.get('instrumento', '').strip().upper()
        
        # Validar formato
        if not re.match(r'^[A-Z0-9\-_]{1,20}$', instrumento):
            raise forms.ValidationError(
                "Solo letras mayúsculas, números, guiones y guiones bajos (máx 20 caracteres)"
            )
        
        # Prevenir inyección SQL
        try:
            validate_no_sql_injection(instrumento)
        except ValidationError:
            raise forms.ValidationError("Instrumento contiene caracteres no permitidos")
        
        # Prevenir XSS
        dangerous_patterns = ['<script>', '</script>', 'javascript:', 'onload=']
        for pattern in dangerous_patterns:
            if pattern.lower() in instrumento.lower():
                raise forms.ValidationError("Instrumento contiene código malicioso")
        
        return instrumento
    
    def clean_secuencia_evento(self):
        """Valida la secuencia con reglas de negocio"""
        secuencia = self.cleaned_data.get('secuencia_evento')
        
        if secuencia is None:
            raise forms.ValidationError("La secuencia es requerida")
        
        # Validar rango
        if secuencia <= 10000:
            raise forms.ValidationError("La secuencia debe ser mayor a 10.000")
        
        if secuencia > 999999999:
            raise forms.ValidationError("La secuencia excede el límite permitido")
        
        # Verificar que sea un número válido
        try:
            int(secuencia)
        except (ValueError, TypeError):
            raise forms.ValidationError("La secuencia debe ser un número válido")
        
        return secuencia
    
    def clean_descripcion(self):
        """Sanitiza la descripción para prevenir XSS"""
        descripcion = self.cleaned_data.get('descripcion', '')
        
        # Sanitizar input
        descripcion = sanitize_input(descripcion)
        
        # Limitar longitud
        if len(descripcion) > 500:
            raise forms.ValidationError("La descripción no puede exceder 500 caracteres")
        
        return descripcion
    
    def clean_fecha(self):
        """Valida que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha')
        
        if fecha and fecha > date.today():
            raise forms.ValidationError("No se pueden crear calificaciones con fecha futura")
        
        return fecha
    
    def clean_ano(self):
        """Valida el año"""
        ano = self.cleaned_data.get('ano')
        
        if ano:
            # Validar rango
            if ano < 2000 or ano > 2100:
                raise forms.ValidationError("El año debe estar entre 2000 y 2100")
            
            # Validar que no sea futuro (con margen de 1 año)
            current_year = datetime.now().year
            if ano > current_year + 1:
                raise forms.ValidationError(f"El año no puede ser mayor a {current_year + 1}")
        
        return ano
    
    def clean_factor_actualizado(self):
        """Valida el factor/monto"""
        factor = self.cleaned_data.get('factor_actualizado')
        
        if factor is not None:
            # Validar que no sea negativo
            if factor < 0:
                raise forms.ValidationError("El factor no puede ser negativo")
            
            # Validar que no sea demasiado grande
            if factor > 9999999999.9999:  # 10 billones
                raise forms.ValidationError("El factor excede el límite permitido")
        
        return factor
    
    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        # Verificar que fecha y año sean coherentes
        fecha = cleaned_data.get('fecha')
        ano = cleaned_data.get('ano')
        
        if fecha and ano:
            if fecha.year != ano:
                self.add_error('ano', f"El año debe coincidir con la fecha ({fecha.year})")
        
        return cleaned_data
    
    def save(self, commit=True):
        calificacion = super().save(commit=False)
        
        if self.corredor:
            calificacion.fk_id_corredor = self.corredor
        
        calificacion.origen = 'manual'
        
        # Sanitizar campos antes de guardar (doble seguridad)
        if calificacion.descripcion:
            calificacion.descripcion = sanitize_input(calificacion.descripcion)
        
        if calificacion.instrumento:
            calificacion.instrumento = calificacion.instrumento.upper()
        
        if commit:
            calificacion.save()
            
        return calificacion

# ========== FORMULARIOS DE USUARIO ==========

class LoginForm(forms.Form):
    """Formulario de login seguro"""
    correo = forms.EmailField(
        label='Correo electrónico',
        max_length=100,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@correo.com',
            'autocomplete': 'email',
            'required': True
        })
    )
    
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'required': True
        })
    )
    
    remember_me = forms.BooleanField(
        label='Recordar sesión',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_correo(self):
        """Valida y sanitiza el correo"""
        correo = self.cleaned_data.get('correo', '').strip().lower()
        
        # Validar formato
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', correo):
            raise forms.ValidationError('Formato de correo inválido')
        
        # Prevenir inyección SQL
        try:
            validate_no_sql_injection(correo)
        except ValidationError:
            raise forms.ValidationError('Correo contiene caracteres no permitidos')
        
        return correo
    
    def clean_contrasena(self):
        """Valida la contraseña"""
        contrasena = self.cleaned_data.get('contrasena', '')
        
        # Validar longitud mínima
        if len(contrasena) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres')
        
        # Prevenir inyección SQL
        try:
            validate_no_sql_injection(contrasena)
        except ValidationError:
            raise forms.ValidationError('Contraseña contiene caracteres no permitidos')
        
        return contrasena

class RegistroForm(forms.Form):
    """Formulario de registro seguro"""
    nombre = forms.CharField(
        label='Nombre completo',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Juan Pérez',
            'required': True,
            'autocomplete': 'name'
        })
    )
    
    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'juan@ejemplo.com',
            'required': True,
            'autocomplete': 'email'
        })
    )
    
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres',
            'required': True,
            'autocomplete': 'new-password'
        })
    )
    
    confirmar_contrasena = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repite tu contraseña',
            'required': True,
            'autocomplete': 'new-password'
        })
    )
    
    def clean_nombre(self):
        """Valida el nombre"""
        nombre = self.cleaned_data.get('nombre', '').strip()
        
        # Validar longitud
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres')
        
        if len(nombre) > 50:
            raise forms.ValidationError('El nombre no puede exceder 50 caracteres')
        
        # Validar que solo contenga letras y espacios
        if not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúñÑ\s]+$', nombre):
            raise forms.ValidationError('El nombre solo puede contener letras y espacios')
        
        # Sanitizar
        nombre = sanitize_input(nombre)
        
        return nombre.title()
    
    def clean_correo(self):
        """Valida el correo"""
        correo = self.cleaned_data.get('correo', '').strip().lower()
        
        # Validar formato
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', correo):
            raise forms.ValidationError('Formato de correo inválido')
        
        # Verificar si ya existe
        if Usuario.objects.filter(correo=correo).exists():
            raise forms.ValidationError('Este correo ya está registrado')
        
        # Prevenir inyección SQL
        try:
            validate_no_sql_injection(correo)
        except ValidationError:
            raise forms.ValidationError('Correo contiene caracteres no permitidos')
        
        return correo
    
    def clean_contrasena(self):
        """Valida la contraseña"""
        contrasena = self.cleaned_data.get('contrasena', '')
        
        # Validaciones básicas
        if len(contrasena) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres')
        
        # Validar fortaleza
        errors = []
        if not re.search(r'[A-Z]', contrasena):
            errors.append('Debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', contrasena):
            errors.append('Debe contener al menos una letra minúscula')
        if not re.search(r'\d', contrasena):
            errors.append('Debe contener al menos un número')
        
        if errors:
            raise forms.ValidationError(errors)
        
        # Prevenir inyección SQL
        try:
            validate_no_sql_injection(contrasena)
        except ValidationError:
            raise forms.ValidationError('Contraseña contiene caracteres no permitidos')
        
        return contrasena
    
    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        contrasena = cleaned_data.get('contrasena')
        confirmar = cleaned_data.get('confirmar_contrasena')
        
        if contrasena and confirmar and contrasena != confirmar:
            self.add_error('confirmar_contrasena', 'Las contraseñas no coinciden')
        
        return cleaned_data

class CambiarContrasenaForm(forms.Form):
    """Formulario para cambiar contraseña"""
    contrasena_actual = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )
    
    nueva_contrasena = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres',
            'required': True
        })
    )
    
    confirmar_contrasena = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repite la nueva contraseña',
            'required': True
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
    
    def clean_contrasena_actual(self):
        """Valida la contraseña actual"""
        contrasena = self.cleaned_data.get('contrasena_actual')
        
        if self.usuario and not check_password(contrasena, self.usuario.contrasena):
            raise forms.ValidationError('La contraseña actual es incorrecta')
        
        return contrasena
    
    def clean_nueva_contrasena(self):
        """Valida la nueva contraseña"""
        nueva_contrasena = self.cleaned_data.get('nueva_contrasena')
        
        # Validaciones de fortaleza
        errors = []
        if len(nueva_contrasena) < 8:
            errors.append('Debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', nueva_contrasena):
            errors.append('Debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', nueva_contrasena):
            errors.append('Debe contener al menos una minúscula')
        if not re.search(r'\d', nueva_contrasena):
            errors.append('Debe contener al menos un número')
        
        if errors:
            raise forms.ValidationError(errors)
        
        # Verificar que no sea igual a la actual
        if self.usuario and check_password(nueva_contrasena, self.usuario.contrasena):
            raise forms.ValidationError('La nueva contraseña no puede ser igual a la actual')
        
        return nueva_contrasena
    
    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        nueva = cleaned_data.get('nueva_contrasena')
        confirmar = cleaned_data.get('confirmar_contrasena')
        
        if nueva and confirmar and nueva != confirmar:
            self.add_error('confirmar_contrasena', 'Las contraseñas no coinciden')
        
        return cleaned_data

# ========== FORMULARIO DE CARGA MASIVA ==========

class CargaMasivaForm(forms.Form):
    """Formulario para carga masiva de archivos"""
    archivo_csv = forms.FileField(
        label='Archivo CSV',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
            'required': True
        })
    )
    
    def clean_archivo_csv(self):
        """Valida el archivo CSV"""
        archivo = self.cleaned_data.get('archivo_csv')
        
        if not archivo:
            raise forms.ValidationError('Debe seleccionar un archivo')
        
        # Validar extensión
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError('Solo se permiten archivos CSV')
        
        # Validar tamaño (máximo 10MB)
        if archivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError('El archivo es demasiado grande (máximo 10MB)')
        
        # Validar nombre
        if not re.match(r'^[a-zA-Z0-9_\-\.\s]+$', archivo.name):
            raise forms.ValidationError('Nombre de archivo inválido')
        
        return archivo

class CargaPDFForm(forms.Form):
    """Formulario para carga de PDF"""
    archivo_pdf = forms.FileField(
        label='Archivo PDF',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'required': True
        })
    )
    
    def clean_archivo_pdf(self):
        """Valida el archivo PDF"""
        archivo = self.cleaned_data.get('archivo_pdf')
        
        if not archivo:
            raise forms.ValidationError('Debe seleccionar un archivo')
        
        # Validar extensión
        if not archivo.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Solo se permiten archivos PDF')
        
        # Validar tamaño (máximo 10MB)
        if archivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError('El archivo es demasiado grande (máximo 10MB)')
        
        return archivo