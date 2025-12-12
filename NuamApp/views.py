from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .forms import CalificacionForm
from datetime import date
import csv
from django.db.models import Q, Count
from .models import Calificacion, Corredor, Usuario, Archivocarga, Auditoria, Factor
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import render
import io
from datetime import datetime
import pdfplumber
import re
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .decorators import login_required_custom, audit_action
from django.utils import timezone
import time
from django.views.decorators.csrf import csrf_protect  


def no_autorizado(request):
    return render(request, "no_autorizado.html")

# LOGIN / LOGOUT


@csrf_protect
def login_view(request):
    """Login simplificado"""
    
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip().lower()
        contrasena = request.POST.get("contrasena", "")
        
        # Validación
        if not correo or not contrasena:
            messages.error(request, "Correo y contraseña son requeridos")
            return redirect("login")
        
        try:
            usuario = Usuario.objects.get(correo=correo)
            
            if not check_password(contrasena, usuario.contrasena):
                messages.error(request, "Credenciales incorrectas")
                return redirect("login")
            
            if usuario.estado.lower() != "activo":
                messages.error(request, "Cuenta desactivada")
                return redirect("login")
            
            # Login exitoso
            request.session["usuario_id"] = usuario.id_usuario
            request.session["rol"] = usuario.rol
            request.session["usuario_nombre"] = usuario.nombre
            
            # Auditoría CON detalles (ahora SÍ funciona)
            Auditoria.objects.create(
                accion='LOGIN_EXITOSO',
                fecha_hora=timezone.now(),
                resultado=f'Login exitoso: {usuario.nombre}',
                fk_usuario=usuario,
            )
            
            messages.success(request, f"Bienvenido, {usuario.nombre}")
            
            if usuario.rol == "admin":
                return redirect("dashboard_admin")
            else:
                return redirect("dashboard_corredor")
                
        except Usuario.DoesNotExist:
            messages.error(request, "Credenciales incorrectas")
            return redirect("login")
    
    return render(request, "template_login/template_login.html")

def logout_view(request):
    request.session.flush()
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')


def login_required_custom(view_func):
    def wrapper(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            messages.error(request, 'Debes iniciar sesión para acceder')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# REGISTRO

def registro_view(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        correo = request.POST['correo']
        contrasena = request.POST['contrasena']

        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, 'Este correo ya está registrado.')
            return render(request, 'template_login/template_registro.html')

        try:
            usuario = Usuario.objects.create(
            nombre=nombre[:15],
            correo=correo,
            contrasena=make_password(contrasena), 
            rol='corredor',
            estado='inactivo'
)

            Corredor.objects.create(
                fk_usuario=usuario,
                nombre=nombre[:15],
                rut="PENDIENTE",
                telefono="PENDIENTE",
                correo=correo,
                fecha_registro=date.today()
            )

            messages.success(request, 'Registro enviado. Espere activación.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Error en el registro: {str(e)}')

    return render(request, 'template_login/template_registro.html')


# DASHBOARD ADMIN

@login_required_custom
@audit_action('VIEW_ADMIN_DASHBOARD')
def dashboard_admin(request):
    # Verificar que sea admin
    if request.session.get('rol') != 'admin':
        messages.error(request, 'Acceso restringido a administradores')
        return redirect('dashboard_corredor')
    
    # ========== PARÁMETROS DE FILTRO ==========
    buscar = request.GET.get('buscar', '')
    mercado_filter = request.GET.get('mercado', '')
    ano_filter = request.GET.get('ano', '')
    corredor_filter = request.GET.get('corredor', '')
    usuario_filter = request.GET.get('usuario', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    tab_activa = request.GET.get('tab', 'resumen')  # resumen, calificaciones, usuarios, auditoria
    
    # ========== DATOS GENERALES PARA FILTROS ==========
    todos_corredores = Corredor.objects.all()
    todos_usuarios = Usuario.objects.all()
    
    # ========== PANEL DE RESUMEN (PESTAÑA 1) ==========
    
    # 1. CALIFICACIONES DE TODOS LOS USUARIOS
    calificaciones_todos = Calificacion.objects.all().select_related('fk_id_corredor', 'fk_id_corredor__fk_usuario')
    
    if buscar:
        calificaciones_todos = calificaciones_todos.filter(
            Q(descripcion__icontains=buscar) | 
            Q(instrumento__icontains=buscar) |
            Q(fk_id_corredor__nombre__icontains=buscar)
        )
    
    if mercado_filter:
        calificaciones_todos = calificaciones_todos.filter(mercado=mercado_filter)
    
    if ano_filter:
        calificaciones_todos = calificaciones_todos.filter(ano=ano_filter)
    
    if corredor_filter:
        calificaciones_todos = calificaciones_todos.filter(fk_id_corredor_id=corredor_filter)
    
    if usuario_filter:
        calificaciones_todos = calificaciones_todos.filter(fk_id_corredor__fk_usuario_id=usuario_filter)
    
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            calificaciones_todos = calificaciones_todos.filter(fecha__gte=fecha_inicio_dt)
        except:
            pass
    
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            calificaciones_todos = calificaciones_todos.filter(fecha__lte=fecha_fin_dt)
        except:
            pass
    
    calificaciones_todos = calificaciones_todos.order_by('-fecha')[:100]  # Últimas 100
    
    # 2. ACTIVIDAD RECIENTE DE TODOS LOS USUARIOS (Auditoría)
    auditoria_todos = Auditoria.objects.all().select_related('fk_usuario').order_by('-fecha_hora')[:50]
    
    # 3. CARGAS MASIVAS DE TODOS
    cargas_todos = Archivocarga.objects.all().select_related('fk_id_usuario').order_by('-fecha_carga')[:20]
    
    # ========== ESTADÍSTICAS GLOBALES ==========
    
    # Por usuario
    usuarios_con_actividad = []
    for usuario in todos_usuarios:
        calificaciones_usuario = Calificacion.objects.filter(
            fk_id_corredor__fk_usuario=usuario
        ).count()
        
        auditorias_usuario = Auditoria.objects.filter(
            fk_usuario=usuario
        ).count()
        
        if calificaciones_usuario > 0 or auditorias_usuario > 0:
            usuarios_con_actividad.append({
                'usuario': usuario,
                'total_calificaciones': calificaciones_usuario,
                'total_auditorias': auditorias_usuario,
                'ultima_actividad': Auditoria.objects.filter(
                    fk_usuario=usuario
                ).order_by('-fecha_hora').first()
            })
    
    # Totales generales
    total_calificaciones = Calificacion.objects.count()
    total_usuarios_activos = Usuario.objects.filter(estado='activo').count()
    total_corredores = Corredor.objects.count()
    total_auditorias = Auditoria.objects.count()
    
    # Distribución por mercado
    distribucion_mercado = Calificacion.objects.values('mercado').annotate(
        total=Count('id_calificacion')
    ).order_by('-total')
    
    # Distribución por origen
    distribucion_origen = Calificacion.objects.values('origen').annotate(
        total=Count('id_calificacion')
    ).order_by('-total')
    
    # Actividad por día (últimos 7 días)
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    
    fecha_limite = datetime.now().date() - timedelta(days=7)
    actividad_diaria = Auditoria.objects.filter(
        fecha_hora__date__gte=fecha_limite
    ).annotate(
        dia=TruncDate('fecha_hora')
    ).values('dia').annotate(
        total=Count('id_auditoria')
    ).order_by('dia')
    
    # ========== PESTAÑA ESPECÍFICA: CALIFICACIONES DETALLADAS ==========
    if tab_activa == 'calificaciones':
        # Más detalles para la pestaña de calificaciones
        calificaciones_detalladas = calificaciones_todos
        
    # ========== PESTAÑA ESPECÍFICA: ACTIVIDAD DE USUARIOS ==========
    elif tab_activa == 'usuarios':
        # Ordenar usuarios por actividad
        usuarios_con_actividad.sort(key=lambda x: x['total_calificaciones'] + x['total_auditorias'], reverse=True)
    
    # ========== PESTAÑA ESPECÍFICA: AUDITORÍA COMPLETA ==========
    elif tab_activa == 'auditoria':
        # Filtros específicos para auditoría
        accion_filter = request.GET.get('accion_filter', '')
        tipo_usuario_filter = request.GET.get('tipo_usuario', '')  # admin/corredor
        
        auditoria_filtrada = Auditoria.objects.all().select_related('fk_usuario')
        
        if accion_filter:
            auditoria_filtrada = auditoria_filtrada.filter(accion=accion_filter)
        
        if tipo_usuario_filter:
            if tipo_usuario_filter == 'admin':
                auditoria_filtrada = auditoria_filtrada.filter(fk_usuario__rol='admin')
            elif tipo_usuario_filter == 'corredor':
                auditoria_filtrada = auditoria_filtrada.filter(fk_usuario__rol='corredor')
        
        auditoria_todos = auditoria_filtrada.order_by('-fecha_hora')[:100]
    
    # ========== CONTEXTO COMPLETO ==========
    context = {
        # Parámetros de filtro
        'buscar': buscar,
        'mercado_filter': mercado_filter,
        'ano_filter': ano_filter,
        'corredor_filter': corredor_filter,
        'usuario_filter': usuario_filter,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'tab_activa': tab_activa,
        
        # Datos para filtros
        'todos_corredores': todos_corredores,
        'todos_usuarios': todos_usuarios,
        
        # Datos principales
        'calificaciones_todos': calificaciones_todos,
        'auditoria_todos': auditoria_todos,
        'cargas_todos': cargas_todos,
        'usuarios_con_actividad': usuarios_con_actividad,
        
        # Estadísticas
        'total_calificaciones': total_calificaciones,
        'total_usuarios_activos': total_usuarios_activos,
        'total_corredores': total_corredores,
        'total_auditorias': total_auditorias,
        'distribucion_mercado': distribucion_mercado,
        'distribucion_origen': distribucion_origen,
        'actividad_diaria': list(actividad_diaria),
        
        # Para templates
        'MESES': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
    }
    
    return render(request, 'template_dashboard/template_dashboard_admin.html', context)


# DASHBOARD CORREDOR CORREGIDO

@login_required_custom
def dashboard_corredor(request):
    usuario_id = request.session["usuario_id"]
    usuario = Usuario.objects.get(id_usuario=usuario_id)

    try:
        corredor = Corredor.objects.get(fk_usuario=usuario)
    except Corredor.DoesNotExist:
        messages.error(request, "No tienes un corredor asociado.")
        return render(request, 'template_dashboard/template_dashboard_corredor.html', {
            'sin_corredor': True,
            'calificaciones': [],
            'total_calificaciones': 0,
            'calificaciones_hoy': 0,
            'calificaciones_mes': 0,
            'cargas_realizadas': 0,
        })

    buscar = request.GET.get('buscar', '')
    mercado_filter = request.GET.get('mercado', '')
    ano_filter = request.GET.get('ano', '')

    calificaciones = Calificacion.objects.filter(fk_id_corredor=corredor)

    # FILTROS
    if buscar:
        calificaciones = calificaciones.filter(
            Q(descripcion__icontains=buscar) | 
            Q(instrumento__icontains=buscar) |
            Q(fk_id_corredor__nombre__icontains=buscar)
        )
    if mercado_filter:
        calificaciones = calificaciones.filter(mercado=mercado_filter)
    if ano_filter:
        calificaciones = calificaciones.filter(ano=ano_filter)

    calificaciones = calificaciones.order_by('-fecha')

    # ----------------------------
    # KPI: Cálculos reales CORREGIDOS
    # ----------------------------
    hoy = timezone.now().date()
    
    # Total de calificaciones (con filtros aplicados)
    total_calificaciones = calificaciones.count()

    # Calificaciones de hoy (sin filtros de búsqueda)
    calificaciones_hoy = Calificacion.objects.filter(
        fk_id_corredor=corredor,
        fecha=hoy
    ).count()

    # Calificaciones del mes (sin filtros de búsqueda)
    primer_dia_mes = hoy.replace(day=1)
    calificaciones_mes = Calificacion.objects.filter(
        fk_id_corredor=corredor,
        fecha__gte=primer_dia_mes,
        fecha__lte=hoy
    ).count()

    # Cargas realizadas (usando Archivocarga)
    cargas_realizadas = Archivocarga.objects.filter(
        fk_id_usuario=usuario
    ).count()

    return render(request, 'template_dashboard/template_dashboard_corredor.html', {
        'calificaciones': calificaciones,
        'usuario': usuario,
        'corredor': corredor,
        'buscar': buscar,
        'mercado_filter': mercado_filter,
        'ano_filter': ano_filter,

        # KPI enviados al template
        'total_calificaciones': total_calificaciones,
        'calificaciones_hoy': calificaciones_hoy,
        'calificaciones_mes': calificaciones_mes,
        'cargas_realizadas': cargas_realizadas,
    })



# AGREGAR CALIFICACION

# views.py - Modifica la función agregar_calificacion
@login_required_custom
def agregar_calificacion(request):
    usuario_id = request.session['usuario_id']
    usuario = Usuario.objects.get(id_usuario=usuario_id)
    corredor = Corredor.objects.get(fk_usuario=usuario)

    if request.method == 'POST':
        form = CalificacionForm(request.POST, corredor=corredor)

        print("=" * 50)
        print("DEBUG: Formulario POST recibido")
        print(f"Datos POST: {request.POST}")
        print(f"Formulario válido? {form.is_valid()}")
        
        if not form.is_valid():
            print("ERRORES DEL FORMULARIO:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
        
        if form.is_valid():
            print("Guardando calificación...")
            calificacion = form.save(commit=False)
            
            # Tu lógica adicional
            instrumento = request.POST.get('instrumento', '')
            secuencia = request.POST.get('secuencia_evento', '')
            
            calificacion.descripcion = f"{form.cleaned_data['descripcion']} | Inst: {instrumento} | Sec: {secuencia}"
            calificacion.fk_id_corredor = corredor
            calificacion.save()

            print(f"✅ Calificación guardada. ID: {calificacion.id_calificacion}")
            
            messages.success(request, 'Calificación añadida.')
            return redirect('dashboard_corredor')  # Esto daría código 302
        else:
            # Muestra los errores en messages también
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    else:
        form = CalificacionForm(corredor=corredor)

    return render(request, 'template_calificaciones/template_agregarCalificacion.html', {'form': form})

# EDITAR CALIFICACION

@login_required_custom
def editar_calificacion_view(request, calificacion_id):

    usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
    corredor = Corredor.objects.get(fk_usuario=usuario)

    calificacion = get_object_or_404(Calificacion, id_calificacion=calificacion_id, fk_id_corredor=corredor)

    if request.method == 'POST':
        calificacion.fecha = request.POST['fecha']
        calificacion.mercado = request.POST['mercado']
        calificacion.ano = request.POST['ano']
        calificacion.descripcion = request.POST.get('descripcion', '')
        calificacion.save()

        messages.success(request, 'Calificación actualizada.')
        return redirect('dashboard_corredor')

    return render(request, 'template_calificaciones/template_editarCalificacion.html', {
        'calificacion': calificacion
    })


# ELIMINAR CALIFICACION

@login_required_custom
def eliminar_calificacion_view(request, calificacion_id):

    usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
    corredor = Corredor.objects.get(fk_usuario=usuario)

    calificacion = get_object_or_404(Calificacion, id_calificacion=calificacion_id, fk_id_corredor=corredor)

    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, 'Calificación eliminada.')
        return redirect('dashboard_corredor')

    return render(
        request,
        'template_calificaciones/template_confirmar_eliminar.html',
        {'calificacion': calificacion}
    )

from django.contrib.auth.hashers import make_password

def fix_passwords(request):
    usuarios = Usuario.objects.all()
    for u in usuarios:
        if not u.contrasena.startswith("pbkdf2_"):
            u.contrasena = make_password(u.contrasena)
            u.save()

    return HttpResponse("Contraseñas convertidas correctamente")

@login_required_custom
def carga_factores(request):
    if request.method == 'POST':
        archivo_csv = request.FILES.get('archivo_csv')
        if not archivo_csv:
            messages.error(request, 'Debes seleccionar un archivo CSV')
            return redirect('carga_factores')
        if not archivo_csv.name.endswith('.csv'):
            messages.error(request, 'El archivo debe ser CSV')
            return redirect('carga_factores')
        try:
            data_set = archivo_csv.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            required_columns = ['nombre_factor', 'valor_factor', 'fecha_inicio']
            if not all(col in reader.fieldnames for col in required_columns):
                messages.error(request, f'El CSV debe contener: {", ".join(required_columns)}')
                return redirect('carga_factores')
            
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            carga = Archivocarga.objects.create(
                tipo_archivo='factores',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )
            
            registros_procesados, registros_fallidos = 0, 0
            for row_num, row in enumerate(reader, start=2):
                try:
                    fecha_inicio = datetime.strptime(row['fecha_inicio'], '%Y-%m-%d').date()
                    fecha_fin = datetime.strptime(row.get('fecha_fin', row['fecha_inicio']), '%Y-%m-%d').date()
                    Factor.objects.create(
                        nombre_factor=row['nombre_factor'],
                        valor_factor=int(row['valor_factor']),
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin
                    )
                    registros_procesados += 1
                except Exception as e:
                    registros_fallidos += 1
                    print(f"Fila {row_num} error: {e}")
            
            carga.estado = 'completado'
            carga.save()
            messages.success(request, f'{registros_procesados} factores procesados, {registros_fallidos} fallidos')
            return redirect('dashboard_admin' if request.session.get('rol')=='admin' else 'dashboard_corredor')
        
        except Exception as e:
            messages.error(request, f'Error procesando CSV: {str(e)}')
            return redirect('carga_factores')

    return render(request, 'template_cargas/carga_factor.html')


@login_required_custom
def carga_montos(request):
    if request.method == 'POST':
        archivo_csv = request.FILES.get('archivo_csv')
        if not archivo_csv:
            messages.error(request, 'Debes seleccionar un archivo CSV')
            return redirect('carga_montos')
        try:
            data_set = archivo_csv.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)
            delimiter = ';' if ';' in data_set.splitlines()[0] else ','
            reader = csv.DictReader(io_string, delimiter=delimiter)
            
            required_columns = ['fecha','mercado','ano','monto','descripcion']
            if not all(col in reader.fieldnames for col in required_columns):
                messages.error(request, f'El CSV debe contener: {", ".join(required_columns)}')
                return redirect('carga_montos')
            
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            carga = Archivocarga.objects.create(
                tipo_archivo='montos',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )

            registros_procesados, registros_fallidos = 0, 0
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Manejar diferentes formatos de número
                    monto_str = row['monto']
                    # Remover puntos de miles y reemplazar coma decimal por punto
                    monto_str = monto_str.replace('.', '').replace(',', '.')
                    # Remover símbolos de moneda
                    monto_str = monto_str.replace('$', '').replace('€', '').strip()
                    monto = float(monto_str)
                    
                    Calificacion.objects.create(
                        fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                        mercado=row['mercado'],
                        ano=int(row['ano']),
                        descripcion=row['descripcion'],
                        factor_actualizado=monto,
                        fk_id_corredor=corredor
                    )
                    registros_procesados += 1
                except Exception as e:
                    registros_fallidos += 1
                    print(f"Fila {row_num} error: {e}")
                    print(f"Datos de la fila: {row}")

            carga.estado = 'completado'
            carga.save()
            messages.success(request, f'{registros_procesados} montos procesados, {registros_fallidos} fallidos')
            return redirect('dashboard_admin' if request.session.get('rol') == 'admin' else 'dashboard_corredor')
        
        except Exception as e:
            messages.error(request, f'Error procesando CSV: {str(e)}')
            return redirect('carga_montos')
    return render(request, 'template_cargas/carga_monto.html')

@login_required_custom
def listado_cargas(request):
    cargas = Archivocarga.objects.all().order_by('-fecha_carga')
    
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        cargas = cargas.filter(tipo_archivo=tipo_filtro)
    

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        cargas = cargas.filter(estado=estado_filtro)
    

    total_cargas = cargas.count()
    cargas_completadas = cargas.filter(estado='completado').count()
    cargas_procesando = cargas.filter(estado='procesando').count()
    cargas_error = cargas.filter(estado='error').count()
    
    context = {
        'cargas': cargas,
        'total_cargas': total_cargas,
        'cargas_completadas': cargas_completadas,
        'cargas_procesando': cargas_procesando,
        'cargas_error': cargas_error,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
    }
    
    return render(request, 'template_cargas/listar_cargas.html', context)

@login_required_custom
def carga_masiva_montos(request):
    if request.method == 'POST':
        archivo_csv = request.FILES.get('archivo_csv')
        
        if not archivo_csv:
            messages.error(request, 'Debes seleccionar un archivo CSV')
            return redirect('carga_montos')
        
        if not archivo_csv.name.endswith('.csv'):
            messages.error(request, 'El archivo debe ser CSV')
            return redirect('carga_montos')

        try:
            # Leer contenido con soporte BOM
            data_set = archivo_csv.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)

            # Detectar si Excel usó ; en lugar de ,
            first_line = data_set.splitlines()[0]
            delimiter = ';' if ';' in first_line else ','

            reader = csv.DictReader(io_string, delimiter=delimiter)

            # Normalizar nombres de columnas (quita BOM / espacios)
            fieldnames = [fn.strip().replace('\ufeff', '') for fn in reader.fieldnames]

            required_columns = ['fecha', 'mercado', 'ano', 'monto', 'descripcion']
            if not all(col in fieldnames for col in required_columns):
                messages.error(request, f'El CSV debe contener las columnas: {", ".join(required_columns)}')
                return redirect('carga_montos')

            # Mapa limpio
            reader.fieldnames = fieldnames

            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)

            carga = Archivocarga.objects.create(
                tipo_archivo='montos',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )

            registros_procesados = 0
            registros_fallidos = 0
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Normalizar monto (quita comas o puntos)
                    monto_str = row['monto']
                    # Limpiar el string
                    monto_str = monto_str.replace('$', '').replace('€', '').strip()
                    # Reemplazar comas decimales por punto
                    monto_str = monto_str.replace(',', '.')
                    # Eliminar puntos de miles
                    if '.' in monto_str and monto_str.count('.') > 1:
                        # Si hay múltiples puntos, son separadores de miles
                        parts = monto_str.split('.')
                        if len(parts[-1]) == 2:  # Posiblemente decimales
                            monto_str = ''.join(parts[:-1]) + '.' + parts[-1]
                        else:
                            monto_str = ''.join(parts)
                    
                    monto_float = float(monto_str)

                    Calificacion.objects.create(
                        fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                        mercado=row['mercado'],
                        ano=int(row['ano']),
                        descripcion=row['descripcion'],
                        factor_actualizado=monto_float,
                        fk_id_corredor=corredor
                    )

                    registros_procesados += 1

                except Exception as e:
                    registros_fallidos += 1
                    print(f"Error en fila {row_num}: {e}")

            carga.estado = 'completado'
            carga.save()

            Auditoria.objects.create(
                accion='CARGA_MONTOS',
                fecha_hora=datetime.now(),
                resultado=f'{registros_procesados} procesados, {registros_fallidos} fallidos',
                fk_usuario=usuario
            )

            messages.success(request, f'Carga completada: {registros_procesados} OK, {registros_fallidos} fallidos')
            return redirect('dashboard_admin' if request.session.get('rol') == 'admin' else 'dashboard_corredor')

        except Exception as e:
            messages.error(request, f'Error procesando archivo: {str(e)}')
            return redirect('carga_montos')

    return render(request, 'template_cargas/carga_monto.html')


# En views.py
@login_required_custom
def carga_masiva_calificaciones(request):
    if request.method == 'POST':
        archivo_csv = request.FILES.get('archivo_csv')
        if not archivo_csv:
            messages.error(request, 'Debes seleccionar un CSV')
            return redirect('carga_calificaciones')
        try:
            data_set = archivo_csv.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            required_columns = ['fecha','mercado','ano','descripcion','factor_actualizado']
            if not all(col in reader.fieldnames for col in required_columns):
                messages.error(request, f'CSV debe tener: {", ".join(required_columns)}')
                return redirect('carga_calificaciones')

            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            carga = Archivocarga.objects.create(
                tipo_archivo='calificaciones',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )

            registros = 0
            for row in reader:
                # Manejar factor_actualizado
                factor_str = row.get('factor_actualizado', '0')
                factor_str = factor_str.replace('.', '').replace(',', '.').replace('$', '').strip()
                factor_val = float(factor_str) if factor_str else 0.0
                
                Calificacion.objects.create(
                    fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                    mercado=row['mercado'],
                    ano=int(row['ano']),
                    descripcion=row['descripcion'],
                    factor_actualizado=factor_val,
                    fk_id_corredor=corredor
                )
                registros += 1
            carga.estado = 'completado'
            carga.save()
            messages.success(request, f'{registros} calificaciones cargadas')
            return redirect('dashboard_corredor')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('carga_calificaciones')
    return render(request, 'template_cargas/template_carga_masiva.html')

@login_required_custom
def ver_detalles_carga(request, carga_id):
    """Vista para ver detalles de una carga específica"""
    try:
        carga = Archivocarga.objects.get(id_archivo=carga_id)
        
        if carga.tipo_archivo == 'factores':
            registros = Factor.objects.all().count()
        elif carga.tipo_archivo == 'montos':
            registros = Calificacion.objects.filter(
                factor_actualizado__isnull=False
            ).count()
        else: 
            registros = Calificacion.objects.all().count()
        
        context = {
            'carga': carga,
            'total_registros': registros,
        }
        return render(request, 'template_cargas/template_detalles_carga.html', context)
        
    except Archivocarga.DoesNotExist:
        messages.error(request, 'La carga no existe')
        return redirect('listado_cargas')

@login_required_custom
def descargar_reporte_carga(request, carga_id):
    """Vista para descargar reporte de una carga"""
    try:
        carga = Archivocarga.objects.get(id_archivo=carga_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reporte_carga_{carga_id}.csv"'
        
        writer = csv.writer(response)
        
        if carga.tipo_archivo == 'factores':
            writer.writerow(['ID', 'Nombre Factor', 'Valor', 'Fecha Inicio', 'Fecha Fin'])
            factores = Factor.objects.all()
            for factor in factores:
                writer.writerow([
                    factor.id_factor,
                    factor.nombre_factor,
                    factor.valor_factor,
                    factor.fecha_inicio,
                    factor.fecha_fin
                ])
        else: 
            writer.writerow(['ID', 'Fecha', 'Mercado', 'Año', 'Descripción', 'Factor/Monto'])
            calificaciones = Calificacion.objects.all()
            for cal in calificaciones:
                writer.writerow([
                    cal.id_calificacion,
                    cal.fecha,
                    cal.mercado,
                    cal.ano,
                    cal.descripcion,
                    cal.factor_actualizado
                ])
        
        return response
        
    except Archivocarga.DoesNotExist:
        messages.error(request, 'La carga no existe')
        return redirect('listado_cargas')

@login_required_custom
def carga_pdf_factores(request):
    if request.method == 'POST':
        archivo_pdf = request.FILES.get('archivo_pdf')
        
        if not archivo_pdf:
            messages.error(request, 'Debes seleccionar un archivo PDF')
            return redirect('carga_pdf')
        
        try:
            datos_extraidos = []
            
            with pdfplumber.open(archivo_pdf) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    
                    patrones = re.findall(r'Factor:\s*(\w+)\s*Valor:\s*(\d+)', text)
                    
                    for factor, valor in patrones:
                        datos_extraidos.append({
                            'nombre_factor': factor,
                            'valor_factor': int(valor),
                            'fecha_inicio': date.today(),
                            'fecha_fin': date(2025, 12, 31)
                        })
            
            for dato in datos_extraidos:
                Factor.objects.create(**dato)
            
            messages.success(request, f'PDF procesado: {len(datos_extraidos)} factores extraídos')
            return redirect('listado_cargas')
            
        except Exception as e:
            messages.error(request, f'Error procesando PDF: {str(e)}')
    
    return render(request, 'template_cargas/template_carga_pdf.html')

@login_required_custom
def carga_pdf(request):
    if request.method == 'POST' and request.FILES.get('archivo_pdf'):
        archivo_pdf = request.FILES['archivo_pdf']
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            datos_extraidos = []

            with pdfplumber.open(archivo_pdf) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text: 
                        continue
                    
                    print(f"=== DEBUG Página {page_num} ===")
                    print(text[:500])  # Ver primeros 500 caracteres para debug
                    
                    # PATRONES MEJORADOS para extracción de datos
                    patrones = [
                        # Patrón 1: Fecha - Mercado - Año - Monto/Factor
                        r'(\d{2,4}[-/]\d{1,2}[-/]\d{2,4})[^\d]*([A-Za-zñÑáéíóúÁÉÍÓÚ\s]+)[^\d]*(\d{4})[^\d]*([\d\.,]+)',
                        
                        # Patrón 2: Buscar montos grandes (con separadores de miles)
                        r'(\d{4}-\d{2}-\d{2})[^0-9]*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                        
                        # Patrón 3: Buscar por etiquetas específicas
                        r'Fecha[:\s]*(\d{4}-\d{2}-\d{2}).*?Mercado[:\s]*([A-Za-z]+).*?Año[:\s]*(\d{4}).*?(?:Monto|Factor)[:\s]*([\d\.,]+)',
                    ]
                    
                    for patron in patrones:
                        matches = re.findall(patron, text, re.IGNORECASE | re.DOTALL)
                        
                        for match in matches:
                            if len(match) >= 4:
                                try:
                                    fecha = match[0]
                                    mercado = match[1].strip()
                                    ano = match[2]
                                    monto_str = match[3]
                                    
                                    # Limpiar y convertir monto
                                    monto_str = monto_str.replace('.', '').replace(',', '.')
                                    monto_val = float(monto_str)
                                    
                                    # Validar mercado
                                    mercados_validos = ['Acciones', 'Bonos', 'Derivados', 'Monedas', 'Acción', 'Bono', 'Derivado', 'Moneda']
                                    mercado_validado = next((m for m in mercados_validos if m.lower() in mercado.lower()), 'Otro')
                                    
                                    datos_extraidos.append({
                                        'fecha': fecha,
                                        'mercado': mercado_validado,
                                        'ano': ano,
                                        'factor': monto_val,
                                        'descripcion': f'PDF Página {page_num} - Extracción automática'
                                    })
                                except Exception as e:
                                    print(f"Error procesando match: {match}, error: {e}")
                                    continue

            registros = 0
            for dato in datos_extraidos:
                try:
                    # Convertir fecha
                    fecha_dt = datetime.strptime(dato['fecha'], '%Y-%m-%d').date() if '-' in dato['fecha'] else datetime.strptime(dato['fecha'], '%d/%m/%Y').date()
                    
                    Calificacion.objects.create(
                        fecha=fecha_dt,
                        mercado=dato['mercado'],
                        ano=int(dato['ano']),
                        factor_actualizado=dato['factor'],
                        descripcion=dato['descripcion'],
                        fk_id_corredor=corredor
                    )
                    registros += 1
                except Exception as e:
                    print(f"Error guardando registro: {dato}, error: {e}")
                    continue

            # Crear registro de carga
            Archivocarga.objects.create(
                tipo_archivo='pdf_calificaciones',
                fecha_carga=datetime.now(),
                estado='completado',
                archivo_url=archivo_pdf.name,
                fk_id_usuario=usuario
            )

            messages.success(request, f'{registros} registros extraídos del PDF')
            return redirect('dashboard_corredor')
        except Exception as e:
            messages.error(request, f'Error procesando PDF: {str(e)}')
            return redirect('carga_pdf')
    return render(request, 'template_cargas/extraer_datos_pdf.html')

# CRUD USUARIOS - ADMIN

@login_required_custom
def gestion_usuarios(request):
    """Listar usuarios con filtros"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    usuarios = Usuario.objects.all()
    
    rol_filter = request.GET.get('rol', '')
    estado_filter = request.GET.get('estado', '')
    
    if rol_filter:
        usuarios = usuarios.filter(rol=rol_filter)
    if estado_filter:
        usuarios = usuarios.filter(estado=estado_filter)
    
    context = {
        'usuarios': usuarios,
        'rol_filter': rol_filter,
        'estado_filter': estado_filter,
        'total_usuarios': usuarios.count(),
    }
    return render(request, 'template_administracion/gestion_usuarios.html', context)

@login_required_custom
def crear_usuario(request):
    """Crear nuevo usuario"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    if request.method == 'POST':
        nombre = request.POST['nombre']
        correo = request.POST['correo']
        contrasena = request.POST['contrasena']
        rol = request.POST['rol']
        
        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, 'Este correo ya está registrado')
            return redirect('crear_usuario')
        
        try:
            usuario = Usuario.objects.create(
                nombre=nombre,
                correo=correo,
                contrasena=make_password(contrasena),
                rol=rol,
                estado='activo'
            )
            
            if rol == 'corredor':
                Corredor.objects.create(
                    fk_usuario=usuario,
                    nombre=nombre,
                    rut="PENDIENTE",
                    telefono="PENDIENTE",
                    correo=correo,
                    fecha_registro=date.today()
                )
            
            messages.success(request, f'Usuario {nombre} creado exitosamente')
            return redirect('gestion_usuarios')
            
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
    
    return render(request, 'template_administracion/crear_usuario.html')

@login_required_custom
def editar_usuario(request, usuario_id):
    """Editar usuario existente"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    
    if request.method == 'POST':
        usuario.nombre = request.POST['nombre']
        usuario.correo = request.POST['correo']
        usuario.rol = request.POST['rol']
        usuario.estado = request.POST['estado']
        
        nueva_contrasena = request.POST.get('contrasena')
        if nueva_contrasena:
            usuario.contrasena = make_password(nueva_contrasena)
        
        usuario.save()
        
        try:
            corredor = Corredor.objects.get(fk_usuario=usuario)
            corredor.nombre = usuario.nombre
            corredor.correo = usuario.correo
            corredor.save()
        except Corredor.DoesNotExist:
            pass
        
        messages.success(request, f'Usuario {usuario.nombre} actualizado')
        return redirect('gestion_usuarios')
    
    return render(request, 'template_administracion/editar_usuario.html', {'usuario': usuario})

@login_required_custom
def activar_usuario(request, usuario_id):
    """Activar usuario"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    usuario.estado = 'activo'
    usuario.save()
    
    messages.success(request, f'Usuario {usuario.nombre} activado')
    return redirect('gestion_usuarios')

@login_required_custom
def desactivar_usuario(request, usuario_id):
    """Desactivar usuario"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    usuario.estado = 'inactivo'
    usuario.save()
    
    messages.success(request, f'Usuario {usuario.nombre} desactivado')
    return redirect('gestion_usuarios')

@login_required_custom
def eliminar_usuario(request, usuario_id):
    """Eliminar usuario (solo corredores)"""
    if request.session.get('rol') != 'admin':
        return redirect('no_autorizado')
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    
    if usuario.rol == 'admin':
        messages.error(request, 'No se pueden eliminar administradores')
        return redirect('gestion_usuarios')
    
    if usuario.id_usuario == request.session.get('usuario_id'):
        messages.error(request, 'No puedes eliminar tu propio usuario')
        return redirect('gestion_usuarios')
    
    nombre = usuario.nombre
    usuario.delete()
    
    messages.success(request, f'Usuario {nombre} eliminado')
    return redirect('gestion_usuarios')

@login_required_custom
def extraer_datos_pdf(request):
    """Vista mejorada para extraer datos de PDF - Compatible con el template actual"""
    if request.method == 'POST' and request.FILES.get('archivo_pdf'):
        archivo_pdf = request.FILES['archivo_pdf']
        
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            # Registrar auditoría
            Auditoria.objects.create(
                accion='CARGA_PDF_INICIO',
                fecha_hora=timezone.now(),
                resultado=f'Inicio procesamiento PDF: {archivo_pdf.name}',
                fk_usuario=usuario
            )
            
            datos_extraidos = []
            registros_validos = []
            
            with pdfplumber.open(archivo_pdf) as pdf:
                total_paginas = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extraer texto de la página
                    text = page.extract_text()
                    
                    if not text or len(text.strip()) < 10:
                        continue  # Saltar páginas vacías
                    
                    print(f"=== DEBUG: Procesando página {page_num} ===")
                    print(f"Texto extraído (primeros 500 chars): {text[:500]}")
                    
                    # ====== PATRONES DE BÚSQUEDA MEJORADOS ======
                    
                    # 1. Patrón: Fecha - Mercado - Año - Monto
                    patron1 = r'(\d{2,4}[-/]\d{1,2}[-/]\d{2,4})[^\d]*(Acciones|Bonos|Derivados|Monedas)[^\d]*(\d{4})[^\d]*([\d\.,]+)'
                    matches1 = re.findall(patron1, text, re.IGNORECASE | re.DOTALL)
                    
                    for match in matches1:
                        if len(match) == 4:
                            registro = {
                                'fecha': match[0],
                                'mercado': match[1],
                                'ano': match[2],
                                'monto_original': match[3],
                                'descripcion': f'PDF Página {page_num} - Patrón directo',
                                'pagina': page_num
                            }
                            registros_validos.append(registro)
                    
                    # 2. Patrón: Buscar líneas con montos grandes
                    lineas = text.split('\n')
                    for linea_num, linea in enumerate(lineas):
                        linea = linea.strip()
                        if len(linea) < 20:
                            continue
                        
                        # Buscar números grandes (montos)
                        montos = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)', linea)
                        if montos:
                            # Filtrar montos válidos (grandes)
                            montos_validos = []
                            for monto in montos:
                                try:
                                    # Limpiar monto
                                    monto_limpio = monto.replace('.', '').replace(',', '.')
                                    valor = float(monto_limpio)
                                    if valor > 100:  # Solo montos significativos
                                        montos_validos.append({
                                            'texto': monto,
                                            'valor': valor,
                                            'posicion': linea.find(monto)
                                        })
                                except:
                                    continue
                            
                            if montos_validos:
                                # Ordenar por valor (más grande primero)
                                montos_validos.sort(key=lambda x: x['valor'], reverse=True)
                                monto_seleccionado = montos_validos[0]
                                
                                # Buscar fecha en la misma línea
                                fecha_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{2,4})', linea)
                                fecha = fecha_match.group(1) if fecha_match else None
                                
                                # Buscar mercado en la misma línea
                                mercado = None
                                mercados = ['Acciones', 'Bonos', 'Derivados', 'Monedas']
                                for m in mercados:
                                    if m.lower() in linea.lower():
                                        mercado = m
                                        break
                                
                                # Buscar año en la misma línea
                                ano_match = re.search(r'(?:20\d{2})', linea)
                                ano = ano_match.group(0) if ano_match else str(date.today().year)
                                
                                if fecha and mercado:
                                    registro = {
                                        'fecha': fecha,
                                        'mercado': mercado,
                                        'ano': ano,
                                        'monto_original': monto_seleccionado['texto'],
                                        'descripcion': f'PDF Página {page_num} - Línea {linea_num+1}',
                                        'pagina': page_num,
                                        'linea': linea
                                    }
                                    registros_validos.append(registro)
                    
                    # 3. Patrón: Buscar tablas estructuradas
                    # Si la página tiene tablas, extraerlas
                    if page.extract_tables():
                        tables = page.extract_tables()
                        for table_num, table in enumerate(tables):
                            for row_num, row in enumerate(table):
                                # Unir todas las celdas del row
                                row_text = ' '.join([str(cell) for cell in row if cell])
                                
                                # Buscar fecha
                                fecha_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{2,4})', row_text)
                                # Buscar monto
                                monto_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', row_text)
                                # Buscar mercado
                                mercado = None
                                for m in ['Acciones', 'Bonos', 'Derivados', 'Monedas']:
                                    if m.lower() in row_text.lower():
                                        mercado = m
                                        break
                                # Buscar año
                                ano_match = re.search(r'(?:20\d{2})', row_text)
                                
                                if fecha_match and monto_match and mercado:
                                    registro = {
                                        'fecha': fecha_match.group(1),
                                        'mercado': mercado,
                                        'ano': ano_match.group(0) if ano_match else str(date.today().year),
                                        'monto_original': monto_match.group(1),
                                        'descripcion': f'PDF Página {page_num} - Tabla {table_num+1}, Fila {row_num+1}',
                                        'pagina': page_num
                                    }
                                    registros_validos.append(registro)
            
            # Procesar y formatear los registros encontrados
            for i, registro in enumerate(registros_validos):
                try:
                    # Formatear fecha
                    fecha_str = registro['fecha']
                    fecha_formateada = fecha_str
                    
                    if '/' in fecha_str:
                        partes = fecha_str.split('/')
                        if len(partes) == 3:
                            dia, mes, ano = partes
                            if len(ano) == 2:
                                ano = '20' + ano
                            fecha_formateada = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                    elif '-' in fecha_str:
                        # Ya está en formato ISO o similar
                        pass
                    
                    # Limpiar y convertir monto
                    monto_str = str(registro['monto_original'])
                    monto_limpio = monto_str.replace('.', '').replace(',', '.').strip()
                    # Remover caracteres no numéricos excepto punto
                    monto_limpio = re.sub(r'[^\d.]', '', monto_limpio)
                    
                    try:
                        monto_valor = float(monto_limpio)
                    except:
                        monto_valor = 0.0
                    
                    datos_extraidos.append({
                        'index': i,
                        'fecha': registro['fecha'],
                        'fecha_formateada': fecha_formateada,
                        'mercado': registro['mercado'],
                        'ano': registro['ano'],
                        'monto_original': registro['monto_original'],
                        'monto_valor': monto_valor,
                        'descripcion': registro['descripcion'],
                        'pagina': registro['pagina']
                    })
                    
                except Exception as e:
                    print(f"Error procesando registro {i}: {e}")
                    continue
            
            # Filtrar duplicados (misma fecha, mercado, año y monto similar)
            datos_unicos = []
            visto = set()
            for dato in datos_extraidos:
                clave = f"{dato['fecha_formateada']}_{dato['mercado']}_{dato['ano']}_{dato['monto_valor']:.2f}"
                if clave not in visto:
                    visto.add(clave)
                    datos_unicos.append(dato)
            
            # Registrar resultados
            Auditoria.objects.create(
                accion='CARGA_PDF_EXTRAIDO',
                fecha_hora=timezone.now(),
                resultado=f'Encontrados {len(datos_unicos)} registros únicos de {len(registros_validos)} posibles',
                fk_usuario=usuario
            )
            
            # Si se encontraron datos, mostrar para confirmación
            if datos_unicos:
                # Obtener cargas recientes para el sidebar
                cargas_recientes = Archivocarga.objects.filter(
                    fk_id_usuario=usuario,
                    tipo_archivo='pdf_calificaciones'
                ).order_by('-fecha_carga')[:5]
                
                return render(request, 'template_cargas/extraer_datos_pdf.html', {
                    'datos_extraidos': datos_unicos,
                    'archivo_nombre': archivo_pdf.name,
                    'total_registros': len(datos_unicos),
                    'mostrar_confirmacion': True,
                    'cargas_recientes': cargas_recientes
                })
            else:
                # No se encontraron datos
                messages.warning(request, 
                    f'No se encontraron datos extraíbles en el PDF "{archivo_pdf.name}". '
                    f'Verifica que el PDF contenga información estructurada con:'
                    f'<ul class="mb-0 mt-2">'
                    f'<li>Fechas (ej: 2023-12-15 o 15/12/2023)</li>'
                    f'<li>Mercados (Acciones, Bonos, Derivados, Monedas)</li>'
                    f'<li>Montos o factores (números grandes)</li>'
                    f'<li>Años (2023, 2024, etc.)</li>'
                    f'</ul>'
                )
                
                # Obtener cargas recientes para el sidebar
                cargas_recientes = Archivocarga.objects.filter(
                    fk_id_usuario=usuario,
                    tipo_archivo='pdf_calificaciones'
                ).order_by('-fecha_carga')[:5]
                
                return render(request, 'template_cargas/extraer_datos_pdf.html', {
                    'mostrar_confirmacion': False,
                    'cargas_recientes': cargas_recientes
                })
                
        except Exception as e:
            error_msg = f'Error procesando PDF: {str(e)}'
            print(f"ERROR en extraer_datos_pdf: {error_msg}")
            
            messages.error(request, error_msg)
            
            try:
                usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
                Auditoria.objects.create(
                    accion='CARGA_PDF_ERROR',
                    fecha_hora=timezone.now(),
                    resultado=f'Error: {str(e)[:100]}...',
                    fk_usuario=usuario
                )
            except:
                pass
            
            # Obtener cargas recientes para el sidebar
            try:
                usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
                cargas_recientes = Archivocarga.objects.filter(
                    fk_id_usuario=usuario,
                    tipo_archivo='pdf_calificaciones'
                ).order_by('-fecha_carga')[:5]
            except:
                cargas_recientes = []
            
            return render(request, 'template_cargas/extraer_datos_pdf.html', {
                'mostrar_confirmacion': False,
                'cargas_recientes': cargas_recientes
            })
    
    # GET request - mostrar formulario vacío
    # Obtener cargas recientes para el sidebar
    try:
        usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
        cargas_recientes = Archivocarga.objects.filter(
            fk_id_usuario=usuario,
            tipo_archivo='pdf_calificaciones'
        ).order_by('-fecha_carga')[:5]
    except:
        cargas_recientes = []
    
    return render(request, 'template_cargas/extraer_datos_pdf.html', {
        'mostrar_confirmacion': False,
        'cargas_recientes': cargas_recientes
    })


def buscar_patrones_calificaciones(texto, pagina):
    resultados = []

    patrones = {
        "fecha": r"\d{4}-\d{2}-\d{2}",
        "mercado": r"(Acciones|Bonos|Derivados|Monedas)",
        "ano": r"Año[:\s]+(\d{4})",
        "factor": r"Factor[:\s]+([\d\.]+)",
        "monto": r"\b\d{1,3}(?:\.\d{3})*(?:,\d{2})?\b"
    }

    encontrado = {
        "pagina": pagina,
        "fechas": re.findall(patrones["fecha"], texto),
        "mercados": re.findall(patrones["mercado"], texto),
        "anos": re.findall(patrones["ano"], texto),
        "factores": re.findall(patrones["factor"], texto),
        "montos": re.findall(patrones["monto"], texto),
        "texto_completo": texto[:300]
    }

    if any([encontrado["fechas"], encontrado["mercados"], encontrado["anos"], encontrado["factores"], encontrado["montos"]]):
        resultados.append(encontrado)

    return resultados

@login_required_custom
def guardar_datos_extraidos(request):
    """Guardar datos extraídos del PDF después de confirmación"""
    if request.method == 'POST':
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            registros_guardados = 0
            registros_fallidos = 0
            
            # Obtener todos los registros del formulario
            i = 0
            while True:
                # Buscar campos con el patrón registro_X
                fecha = request.POST.get(f'fecha_{i}')
                if fecha is None:  # No hay más registros
                    break
                
                mercado = request.POST.get(f'mercado_{i}')
                ano = request.POST.get(f'ano_{i}')
                monto = request.POST.get(f'monto_{i}')
                descripcion = request.POST.get(f'descripcion_{i}', '')
                incluir = request.POST.get(f'incluir_{i}', 'off')
                
                # Solo procesar si está marcado para incluir
                if incluir == 'on' and fecha and mercado and ano and monto:
                    try:
                        # Convertir fecha
                        try:
                            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
                        except:
                            # Intentar otros formatos
                            if '/' in fecha:
                                partes = fecha.split('/')
                                if len(partes) == 3:
                                    fecha_dt = date(int(partes[2]), int(partes[1]), int(partes[0]))
                                else:
                                    fecha_dt = date.today()
                            else:
                                fecha_dt = date.today()
                        
                        # Limpiar monto
                        monto_limpio = str(monto).replace('.', '').replace(',', '.').strip()
                        # Remover símbolos de moneda
                        monto_limpio = re.sub(r'[^\d.]', '', monto_limpio)
                        
                        # Verificar que sea un número válido
                        if not monto_limpio.replace('.', '', 1).isdigit():
                            raise ValueError(f"Monto no válido: {monto}")
                            
                        monto_valor = float(monto_limpio)
                        
                        # Crear calificación
                        Calificacion.objects.create(
                            fecha=fecha_dt,
                            mercado=mercado.capitalize(),
                            ano=int(ano),
                            factor_actualizado=monto_valor,
                            descripcion=descripcion,
                            fk_id_corredor=corredor,
                            origen='pdf'
                        )
                        
                        registros_guardados += 1
                        print(f"✅ Registro guardado: {fecha_dt} - {mercado} - {monto_valor}")
                        
                    except Exception as e:
                        registros_fallidos += 1
                        print(f"❌ Error guardando registro {i}: {e}")
                
                i += 1
            
            # Registrar carga en Archivocarga si se guardó algo
            if registros_guardados > 0:
                Archivocarga.objects.create(
                    tipo_archivo='pdf_calificaciones',
                    fecha_carga=timezone.now(),
                    estado='completado',
                    archivo_url=request.POST.get('archivo_nombre', 'desconocido.pdf'),
                    fk_id_usuario=usuario,
                    registros_procesados=registros_guardados,
                    registros_fallidos=registros_fallidos
                )
            
            # Mensaje de resultado
            if registros_guardados > 0:
                messages.success(request, 
                    f'✅ {registros_guardados} registros guardados exitosamente desde PDF'
                    + (f' ({registros_fallidos} fallidos)' if registros_fallidos > 0 else '')
                )
            else:
                messages.warning(request, 
                    'No se guardaron registros. '
                    + ('Ninguno fue seleccionado.' if registros_fallidos == 0 else 'Todos los registros seleccionados tuvieron errores.')
                )
            
            # Auditoría
            Auditoria.objects.create(
                accion='CARGA_PDF_GUARDADO',
                fecha_hora=timezone.now(),
                resultado=f'PDF guardado: {registros_guardados} exitosos, {registros_fallidos} fallidos',
                fk_usuario=usuario
            )
            
            return redirect('dashboard_corredor')
            
        except Exception as e:
            error_msg = f'Error guardando datos del PDF: {str(e)}'
            messages.error(request, error_msg)
            print(f"ERROR en guardar_datos_extraidos: {error_msg}")
            
            return redirect('extraer_datos_pdf')
    
    return redirect('extraer_datos_pdf')

@require_GET
def health_check(request):
    """Health check endpoint para Render"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'NUAM Sistema de Calificaciones',
        'timestamp': timezone.now().isoformat()
    })

from django.contrib.auth.models import User

def create_superadmin():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )