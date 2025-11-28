from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .forms import CalificacionForm
from datetime import date
import csv
from .models import Calificacion, Corredor, Usuario, Archivocarga, Auditoria, Factor
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import render
import io
from datetime import datetime
import pdfplumber
import re


def no_autorizado(request):
    return render(request, "no_autorizado.html")

# LOGIN / LOGOUT

def login_view(request):
    if request.method == "POST":
        correo = request.POST["correo"]
        contrasena = request.POST["contrasena"]

        try:
            usuario = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            messages.error(request, "Correo no registrado.")
            return redirect("login")

        if not check_password(contrasena, usuario.contrasena):
            messages.error(request, "Contraseña incorrecta.")
            return redirect("login")

        request.session["usuario_id"] = usuario.id_usuario
        request.session["rol"] = usuario.rol

        print(f"DEBUG: Usuario {usuario.nombre} con rol {usuario.rol}") 
        
        if usuario.rol == "admin":
            return redirect("dashboard_admin")
        elif usuario.rol == "corredor":
            return redirect("dashboard_corredor")
        else:
            messages.error(request, "Rol no válido.")
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
def dashboard_admin(request):
    buscar = request.GET.get('buscar', '')
    mercado_filter = request.GET.get('mercado', '')
    ano_filter = request.GET.get('ano', '')

    calificaciones = Calificacion.objects.all().select_related('fk_id_corredor')

    if buscar:
        calificaciones = calificaciones.filter(descripcion__icontains=buscar)
    if mercado_filter:
        calificaciones = calificaciones.filter(mercado=mercado_filter)
    if ano_filter:
        calificaciones = calificaciones.filter(ano=ano_filter)

    calificaciones = calificaciones.order_by('-fecha')

    return render(request, 'template_dashboard/template_dashboard_admin.html', {
        'calificaciones': calificaciones,
        'buscar': buscar,
        'mercado_filter': mercado_filter,
        'ano_filter': ano_filter
    })



# DASHBOARD CORREDOR


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
            'calificaciones': []
        })

    buscar = request.GET.get('buscar', '')
    mercado_filter = request.GET.get('mercado', '')
    ano_filter = request.GET.get('ano', '')

    calificaciones = Calificacion.objects.filter(fk_id_corredor=corredor)

    if buscar:
        calificaciones = calificaciones.filter(descripcion__icontains=buscar)
    if mercado_filter:
        calificaciones = calificaciones.filter(mercado=mercado_filter)
    if ano_filter:
        calificaciones = calificaciones.filter(ano=ano_filter)

    calificaciones = calificaciones.order_by('-fecha')

    return render(request, 'template_dashboard/template_dashboard_corredor.html', {
        'calificaciones': calificaciones,
        'usuario': usuario,
        'corredor': corredor,
        'buscar': buscar,
        'mercado_filter': mercado_filter,
        'ano_filter': ano_filter
    })



# AGREGAR CALIFICACION

@login_required_custom
def agregar_calificacion(request):
    usuario_id = request.session['usuario_id']
    
    usuario = Usuario.objects.get(id_usuario=usuario_id)
    corredor = Corredor.objects.get(fk_usuario=usuario)

    if request.method == 'POST':
        form = CalificacionForm(request.POST, corredor=corredor)

        if form.is_valid():
            calificacion = form.save(commit=False)

            instrumento = request.POST.get('instrumento', '')
            secuencia = request.POST.get('secuencia_evento', '')

            calificacion.descripcion = f"{form.cleaned_data['descripcion']} | Inst: {instrumento} | Sec: {secuencia}"
            calificacion.fk_id_corredor = corredor
            calificacion.save()

            messages.success(request, 'Calificación añadida.')
            return redirect('dashboard_corredor')

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
            data_set = archivo_csv.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            
            required_columns = ['nombre_factor', 'valor_factor', 'fecha_inicio']
            if not all(col in reader.fieldnames for col in required_columns):
                messages.error(request, f'El CSV debe contener las columnas: {", ".join(required_columns)}')
                return redirect('carga_factores')
            
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            carga = Archivocarga.objects.create(
                tipo_archivo='factores',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )
            
            registros_procesados = 0
            registros_fallidos = 0
            
            for row_num, row in enumerate(reader, start=2): 
                try:
                    fecha_inicio = datetime.strptime(row['fecha_inicio'], '%Y-%m-%d').date()
                    fecha_fin = datetime.strptime(row['fecha_fin'], '%Y-%m-%d').date() if row.get('fecha_fin') else fecha_inicio
                    
                    Factor.objects.create(
                        nombre_factor=row['nombre_factor'],
                        valor_factor=int(row['valor_factor']),
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin
                    )
                    registros_procesados += 1
                    
                except Exception as e:
                    registros_fallidos += 1
                    print(f"Error en fila {row_num}: {row} - Error: {e}")
            
            carga.estado = 'completado'
            carga.save()
            
            Auditoria.objects.create(
                accion='CARGA_FACTORES',
                fecha_hora=datetime.now(),
                resultado=f'{registros_procesados} procesados, {registros_fallidos} fallidos',
                fk_usuario=usuario
            )
            
            messages.success(request, f'Carga completada: {registros_procesados} factores procesados, {registros_fallidos} fallidos')
            return redirect('dashboard_admin' if request.session.get('rol') == 'admin' else 'dashboard_corredor')
            
        except Exception as e:
            messages.error(request, f'Error procesando archivo: {str(e)}')
            return redirect('carga_factores')
    
    return render(request, 'template_cargas/carga_factor.html')

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
            data_set = archivo_csv.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
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
                    
                    calificacion = Calificacion.objects.create(
                        fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                        mercado=row['mercado'],
                        ano=int(row['ano']),
                        descripcion=row.get('descripcion', ''),
                        factor_actualizado=float(row['monto']),
                        fk_id_corredor=...  
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
                resultado=f'{registros_procesados} montos procesados',
                fk_usuario=usuario
            )
            
            messages.success(request, f'Carga de montos completada: {registros_procesados} registros')
            return redirect('dashboard_admin')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('carga_montos')
    
    return render(request, 'template_cargas/template_carga_montos.html')

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
            data_set = archivo_csv.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            
            required_columns = ['fecha', 'mercado', 'ano', 'monto', 'descripcion']
            if not all(col in reader.fieldnames for col in required_columns):
                messages.error(request, f'El CSV debe contener las columnas: {", ".join(required_columns)}')
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
            
            registros_procesados = 0
            registros_fallidos = 0
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    Calificacion.objects.create(
                        fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                        mercado=row['mercado'],
                        ano=int(row['ano']),
                        descripcion=row['descripcion'],
                        factor_actualizado=float(row['monto']), 
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
                resultado=f'{registros_procesados} montos procesados, {registros_fallidos} fallidos',
                fk_usuario=usuario
            )
            
            messages.success(request, f'Carga de montos completada: {registros_procesados} registros procesados, {registros_fallidos} fallidos')
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
        
        try:
            data_set = archivo_csv.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
            
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            carga = Archivocarga.objects.create(
                tipo_archivo='calificaciones',
                fecha_carga=datetime.now(),
                estado='procesando',
                archivo_url=archivo_csv.name,
                fk_id_usuario=usuario
            )
            
            registros_procesados = 0
            
            for row in reader:
                Calificacion.objects.create(
                    fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                    mercado=row['mercado'],
                    ano=int(row['ano']),
                    descripcion=row['descripcion'],
                    factor_actualizado=float(row.get('factor_actualizado', 0)),
                    fk_id_corredor=corredor
                )
                registros_procesados += 1
            
            carga.estado = 'completado'
            carga.save()
            
            messages.success(request, f'{registros_procesados} calificaciones cargadas')
            return redirect('dashboard_corredor')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
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
    """Vista mejorada para extraer datos específicos de PDFs de calificaciones"""
    
    if request.method == 'POST' and request.FILES.get('archivo_pdf'):
        archivo_pdf = request.FILES['archivo_pdf']
        
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            datos_extraidos = []
            
            with pdfplumber.open(archivo_pdf) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    
                    if text:
                        calificaciones_encontradas = buscar_patrones_calificaciones(text, page_num)
                        datos_extraidos.extend(calificaciones_encontradas)
            
            return render(request, 'template_pdf/confirmar_datos.html', {
                'datos_extraidos': datos_extraidos,
                'nombre_archivo': archivo_pdf.name,
                'corredor': corredor
            })
            
        except Exception as e:
            messages.error(request, f'Error procesando PDF: {str(e)}')
            return redirect('extraer_datos_pdf')
    
    return render(request, 'template_cargas/extraer_datos_pdf.html')

def buscar_patrones_calificaciones(texto, pagina):
    """Busca diferentes patrones de calificaciones en el texto del PDF"""
    
    patrones = []
    
    patron1 = re.findall(
        r'Fecha:\s*(\d{4}-\d{2}-\d{2})\s*Mercado:\s*(\w+)\s*Año:\s*(\d{4})\s*Factor:\s*([\d.]+)',
        texto
    )
    
    for fecha, mercado, ano, factor in patron1:
        patrones.append({
            'tipo': 'calificacion',
            'fecha': fecha,
            'mercado': mercado,
            'ano': int(ano),
            'factor_actualizado': float(factor),
            'descripcion': f'Extraído de PDF pág {pagina}',
            'pagina': pagina
        })
    
    patron2 = re.findall(
        r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\w+)\s*\|\s*(\d{4})\s*\|\s*([\d.,]+)\s*\|',
        texto
    )
    
    for fecha, mercado, ano, monto in patron2:
        monto_limpio = monto.replace('.', '').replace(',', '.')
        
        patrones.append({
            'tipo': 'monto',
            'fecha': fecha,
            'mercado': mercado,
            'ano': int(ano),
            'factor_actualizado': float(monto_limpio),
            'descripcion': f'Monto extraído de PDF pág {pagina}',
            'pagina': pagina
        })
    
    patron3 = re.findall(
        r'Factor\s+(\w+):\s*(\d+)',
        texto, re.IGNORECASE
    )
    
    for nombre_factor, valor in patron3:
        patrones.append({
            'tipo': 'factor',
            'nombre_factor': nombre_factor,
            'valor_factor': int(valor),
            'fecha_inicio': date.today(),
            'pagina': pagina
        })
    
    return patrones

@login_required_custom
def guardar_datos_extraidos(request):
    """Guardar los datos extraídos del PDF en la base de datos"""
    
    if request.method == 'POST':
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            datos_seleccionados = request.POST.getlist('datos_seleccionados')
            registros_guardados = 0
            
            for dato_idx in datos_seleccionados:
                fecha = request.POST.get(f'fecha_{dato_idx}')
                mercado = request.POST.get(f'mercado_{dato_idx}')
                ano = request.POST.get(f'ano_{dato_idx}')
                factor = request.POST.get(f'factor_{dato_idx}')
                descripcion = request.POST.get(f'descripcion_{dato_idx}')
                
                if all([fecha, mercado, ano, factor]):
                    Calificacion.objects.create(
                        fecha=datetime.strptime(fecha, '%Y-%m-%d').date(),
                        mercado=mercado,
                        ano=int(ano),
                        factor_actualizado=float(factor),
                        descripcion=descripcion,
                        fk_id_corredor=corredor
                    )
                    registros_guardados += 1
            
            messages.success(request, f'{registros_guardados} registros guardados desde PDF')
            return redirect('dashboard_corredor')
            
        except Exception as e:
            messages.error(request, f'Error guardando datos: {str(e)}')
            return redirect('extraer_datos_pdf')
    
    return redirect('extraer_datos_pdf')

@login_required_custom
def extraer_datos_pdf(request):
    """Vista mejorada para extraer datos específicos de PDFs de calificaciones"""
    
    if request.method == 'POST' and request.FILES.get('archivo_pdf'):
        archivo_pdf = request.FILES['archivo_pdf']
        
        try:
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            corredor = Corredor.objects.get(fk_usuario=usuario)
            
            datos_extraidos = []
            
            with pdfplumber.open(archivo_pdf) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    
                    if text:
                        calificaciones_encontradas = buscar_patrones_calificaciones(text, page_num)
                        datos_extraidos.extend(calificaciones_encontradas)
            
            return render(request, 'template_cargas/confirmar_datos.html', {
                'datos_extraidos': datos_extraidos,
                'nombre_archivo': archivo_pdf.name,
                'corredor': corredor
            })
            
        except Exception as e:
            messages.error(request, f'Error procesando PDF: {str(e)}')
            return redirect('extraer_datos_pdf')
    
    return render(request, 'template_cargas/extraer_datos_pdf.html')