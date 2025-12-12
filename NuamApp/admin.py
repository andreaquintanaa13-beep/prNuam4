from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import messages
from django.db.models import Count
from .models import Usuario, Corredor, Calificacion, Factor, Archivocarga, Reporte, Auditoria, Permiso, UsuarioPermiso, CalificacionFactor

# ==================== FILTROS PERSONALIZADOS ====================
class ConRelacionesFilter(admin.SimpleListFilter):
    """Filtro para mostrar usuarios con/sin relaciones"""
    title = 'tiene relaciones'
    parameter_name = 'con_relaciones'

    def lookups(self, request, model_admin):
        return (
            ('si', 'Con relaciones'),
            ('no', 'Sin relaciones'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'si':
            # Usuarios que tienen al menos una relación
            return queryset.filter(
                id_usuario__in=Usuario.objects.annotate(
                    rel_count=Count('corredor') + Count('archivocarga') + Count('reporte') + Count('auditoria') + Count('usuariopermiso')
                ).filter(rel_count__gt=0)
            )
        if self.value() == 'no':
            # Usuarios sin relaciones
            return queryset.filter(
                id_usuario__in=Usuario.objects.annotate(
                    rel_count=Count('corredor') + Count('archivocarga') + Count('reporte') + Count('auditoria') + Count('usuariopermiso')
                ).filter(rel_count=0)
            )
        return queryset


# ==================== USUARIO ADMIN ====================
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'nombre', 'correo', 'rol', 'estado', 'get_related_info', 'actions_column')
    list_filter = ('estado', 'rol', ConRelacionesFilter)
    search_fields = ('nombre', 'correo', 'rol')
    list_editable = ('estado',)
    list_per_page = 20
    actions = ['activate_users', 'deactivate_users', 'delete_selected_safe']
    readonly_fields = ('get_related_details', 'date_joined', 'last_login')
    fieldsets = (
        ('Información Principal', {
            'fields': ('nombre', 'correo', 'contrasena', 'rol', 'estado')
        }),
        ('Relaciones', {
            'fields': ('get_related_details',),
            'classes': ('collapse',),
        }),
        ('Auditoría', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',),
        }),
    )
    
    def get_related_info(self, obj):
        """Muestra información concisa de relaciones"""
        info = []
        
        # Corredor
        if hasattr(obj, 'corredor'):
            info.append('👤')
        
        # Conteo de otros objetos
        from django.db.models import Count
        counts = {
            '📁': Archivocarga.objects.filter(fk_id_usuario=obj).count(),
            '📊': Reporte.objects.filter(fk_id_usuario=obj).count(),
            '🔐': UsuarioPermiso.objects.filter(fk_id_usuario=obj).count(),
            '📝': Auditoria.objects.filter(fk_usuario=obj).count(),
        }
        
        for icon, count in counts.items():
            if count > 0:
                info.append(f"{icon}{count}")
        
        return ' '.join(info) if info else '—'
    get_related_info.short_description = 'Relaciones'
    
    def get_related_details(self, obj):
        """Muestra detalles de relaciones en vista de edición"""
        details = []
        
        # Corredor
        if hasattr(obj, 'corredor'):
            url = reverse('admin:NuamApp_corredor_change', args=[obj.corredor.id_corredor])
            details.append(format_html(
                '<strong>Corredor:</strong> <a href="{}">{}</a> (RUT: {})',
                url, obj.corredor.nombre, obj.corredor.rut
            ))
        
        # Archivos
        archivos = Archivocarga.objects.filter(fk_id_usuario=obj)
        if archivos.exists():
            url = reverse('admin:NuamApp_archivocarga_changelist') + f'?fk_id_usuario__id_usuario={obj.id_usuario}'
            details.append(format_html(
                '<strong>Archivos de carga:</strong> <a href="{}">{} archivo(s)</a>',
                url, archivos.count()
            ))
        
        # Reportes
        reportes = Reporte.objects.filter(fk_id_usuario=obj)
        if reportes.exists():
            url = reverse('admin:NuamApp_reporte_changelist') + f'?fk_id_usuario__id_usuario={obj.id_usuario}'
            details.append(format_html(
                '<strong>Reportes:</strong> <a href="{}">{} reporte(s)</a>',
                url, reportes.count()
            ))
        
        # Permisos
        permisos = UsuarioPermiso.objects.filter(fk_id_usuario=obj)
        if permisos.exists():
            url = reverse('admin:NuamApp_usuariopermiso_changelist') + f'?fk_id_usuario__id_usuario={obj.id_usuario}'
            details.append(format_html(
                '<strong>Permisos:</strong> <a href="{}">{} permiso(s)</a>',
                url, permisos.count()
            ))
        
        # Auditorías
        auditorias = Auditoria.objects.filter(fk_usuario=obj)
        if auditorias.exists():
            url = reverse('admin:NuamApp_auditoria_changelist') + f'?fk_usuario__id_usuario={obj.id_usuario}'
            details.append(format_html(
                '<strong>Auditorías:</strong> <a href="{}">{} registro(s)</a>',
                url, auditorias.count()
            ))
        
        return format_html('<br>'.join(details)) if details else "No hay objetos relacionados"
    get_related_details.short_description = "Detalles de Relaciones"
    
    def actions_column(self, obj):
        """Columna con acciones rápidas"""
        delete_url = reverse('admin:NuamApp_usuario_delete', args=[obj.id_usuario])
        change_url = reverse('admin:NuamApp_usuario_change', args=[obj.id_usuario])
        
        return format_html(
            '<a href="{}" class="button" title="Editar">✏️</a>&nbsp;'
            '<a href="{}" class="button" style="color: #dc3545;" title="Eliminar">🗑️</a>',
            change_url, delete_url
        )
    actions_column.short_description = 'Acciones'
    
    def activate_users(self, request, queryset):
        """Acción para activar usuarios"""
        updated = queryset.update(estado='activo')
        self.message_user(request, f'{updated} usuario(s) activado(s) correctamente.', messages.SUCCESS)
    activate_users.short_description = "Activar usuarios seleccionados"
    
    def deactivate_users(self, request, queryset):
        """Acción para desactivar usuarios"""
        updated = queryset.update(estado='inactivo')
        self.message_user(request, f'{updated} usuario(s) desactivado(s) correctamente.', messages.SUCCESS)
    deactivate_users.short_description = "Desactivar usuarios seleccionados"
    
    def delete_selected_safe(self, request, queryset):
        """Eliminación segura con confirmación"""
        count = queryset.count()
        deleted = 0
        for obj in queryset:
            try:
                # Primero verificar si tiene corredor
                if hasattr(obj, 'corredor'):
                    self.message_user(
                        request, 
                        f"No se puede eliminar {obj.nombre}: tiene corredor asociado", 
                        messages.ERROR
                    )
                    continue
                    
                obj.delete()
                deleted += 1
            except Exception as e:
                self.message_user(request, f"Error eliminando {obj.nombre}: {str(e)}", messages.ERROR)
        
        if deleted > 0:
            self.message_user(request, f"{deleted} usuario(s) eliminado(s) exitosamente.", messages.SUCCESS)
    delete_selected_safe.short_description = "Eliminar seleccionados (seguro)"
    
    # Campos ficticios para el fieldset
    def date_joined(self, obj):
        return "—"
    date_joined.short_description = "Fecha de registro"
    
    def last_login(self, obj):
        return "—"
    last_login.short_description = "Último acceso"


# ==================== CORREDOR ADMIN ====================
@admin.register(Corredor)
class CorredorAdmin(admin.ModelAdmin):
    list_display = ('id_corredor', 'nombre', 'rut', 'correo', 'telefono', 'fecha_registro', 'usuario_link', 'calificaciones_count')
    search_fields = ('nombre', 'rut', 'correo', 'telefono')
    list_filter = ('fecha_registro',)
    list_per_page = 20
    raw_id_fields = ('fk_usuario',)
    readonly_fields = ('calificaciones_list',)
    
    def usuario_link(self, obj):
        if obj.fk_usuario:
            url = reverse('admin:NuamApp_usuario_change', args=[obj.fk_usuario.id_usuario])
            return format_html('<a href="{}">{}</a>', url, obj.fk_usuario.nombre)
        return "—"
    usuario_link.short_description = "Usuario"
    
    def calificaciones_count(self, obj):
        count = Calificacion.objects.filter(fk_id_corredor=obj).count()
        if count > 0:
            url = reverse('admin:NuamApp_calificacion_changelist') + f'?fk_id_corredor__id_corredor={obj.id_corredor}'
            return format_html('<a href="{}">{} calif.</a>', url, count)
        return "—"
    calificaciones_count.short_description = "Calificaciones"
    
    def calificaciones_list(self, obj):
        """Lista de calificaciones en vista detalle"""
        calificaciones = Calificacion.objects.filter(fk_id_corredor=obj)
        if not calificaciones.exists():
            return "No hay calificaciones"
        
        items = []
        for cal in calificaciones:
            url = reverse('admin:NuamApp_calificacion_change', args=[cal.id_calificacion])
            items.append(format_html(
                '<li><a href="{}">{} - {} ({})</a></li>',
                url, cal.fecha, cal.mercado, cal.instrumento or "N/A"
            ))
        
        return format_html('<ul>{}</ul>', ''.join(items))
    calificaciones_list.short_description = "Calificaciones asociadas"
    
    fieldsets = (
        ('Información del Corredor', {
            'fields': ('nombre', 'rut', 'telefono', 'correo', 'fecha_registro')
        }),
        ('Relaciones', {
            'fields': ('fk_usuario', 'calificaciones_list'),
        }),
    )


# ==================== CALIFICACIÓN ADMIN ====================
@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('id_calificacion', 'fecha', 'mercado', 'instrumento', 'corredor_link', 'factores_count', 'origen')
    list_filter = ('mercado', 'fecha', 'origen')
    search_fields = ('instrumento', 'descripcion', 'fk_id_corredor__nombre')
    list_per_page = 20
    raw_id_fields = ('fk_id_corredor',)
    date_hierarchy = 'fecha'
    readonly_fields = ('factores_detalle', 'fecha_creacion', 'fecha_modificacion')
    
    def corredor_link(self, obj):
        if obj.fk_id_corredor:
            url = reverse('admin:NuamApp_corredor_change', args=[obj.fk_id_corredor.id_corredor])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_corredor.nombre)
        return "—"
    corredor_link.short_description = "Corredor"
    
    def factores_count(self, obj):
        count = CalificacionFactor.objects.filter(fk_id_calificacion=obj).count()
        if count > 0:
            url = reverse('admin:NuamApp_calificacionfactor_changelist') + f'?fk_id_calificacion__id_calificacion={obj.id_calificacion}'
            return format_html('<a href="{}">{} factor(es)</a>', url, count)
        return "—"
    factores_count.short_description = "Factores"
    
    def factores_detalle(self, obj):
        """Muestra los factores asociados en vista detalle"""
        factores = CalificacionFactor.objects.filter(fk_id_calificacion=obj).select_related('fk_id_factor')
        if not factores.exists():
            return "No hay factores asociados"
        
        items = []
        for cf in factores:
            factor_url = reverse('admin:NuamApp_factor_change', args=[cf.fk_id_factor.id_factor])
            items.append(format_html(
                '<li><a href="{}">{}</a> (ID: {})</li>',
                factor_url, cf.fk_id_factor.nombre_factor, cf.fk_id_factor.id_factor
            ))
        
        return format_html('<ul>{}</ul>', ''.join(items))
    factores_detalle.short_description = "Factores asociados"
    
    fieldsets = (
        ('Información de Calificación', {
            'fields': ('fecha', 'mercado', 'ano', 'instrumento', 'descripcion', 'factor_actualizado')
        }),
        ('Relaciones', {
            'fields': ('fk_id_corredor', 'factores_detalle'),
        }),
        ('Metadatos', {
            'fields': ('secuencia_evento', 'origen', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',),
        }),
    )


# ==================== FACTOR ADMIN ====================
@admin.register(Factor)
class FactorAdmin(admin.ModelAdmin):
    list_display = ('id_factor', 'nombre_factor', 'valor_factor', 'fecha_inicio', 'fecha_fin', 'uso_count')
    search_fields = ('nombre_factor',)
    list_filter = ('fecha_inicio', 'fecha_fin')
    list_per_page = 20
    readonly_fields = ('calificaciones_asociadas',)
    
    def uso_count(self, obj):
        count = CalificacionFactor.objects.filter(fk_id_factor=obj).count()
        if count > 0:
            url = reverse('admin:NuamApp_calificacionfactor_changelist') + f'?fk_id_factor__id_factor={obj.id_factor}'
            return format_html('<a href="{}">{} uso(s)</a>', url, count)
        return "—"
    uso_count.short_description = "Veces usado"
    
    def calificaciones_asociadas(self, obj):
        """Muestra calificaciones que usan este factor"""
        cal_factores = CalificacionFactor.objects.filter(fk_id_factor=obj).select_related('fk_id_calificacion')
        if not cal_factores.exists():
            return "No hay calificaciones que usen este factor"
        
        items = []
        for cf in cal_factores:
            cal_url = reverse('admin:NuamApp_calificacion_change', args=[cf.fk_id_calificacion.id_calificacion])
            items.append(format_html(
                '<li><a href="{}">Calificación #{}</a> - {} ({})</li>',
                cal_url, cf.fk_id_calificacion.id_calificacion,
                cf.fk_id_calificacion.fecha, cf.fk_id_calificacion.mercado
            ))
        
        return format_html('<ul>{}</ul>', ''.join(items))
    calificaciones_asociadas.short_description = "Calificaciones que usan este factor"
    
    fieldsets = (
        ('Información del Factor', {
            'fields': ('nombre_factor', 'valor_factor', 'fecha_inicio', 'fecha_fin')
        }),
        ('Uso en Calificaciones', {
            'fields': ('calificaciones_asociadas',),
            'classes': ('collapse',),
        }),
    )


# ==================== ARCHIVO CARGA ADMIN ====================
@admin.register(Archivocarga)
class ArchivocargaAdmin(admin.ModelAdmin):
    list_display = ('id_archivo', 'tipo_archivo', 'fecha_carga', 'estado', 'usuario_link', 'archivo_preview')
    list_filter = ('tipo_archivo', 'estado', 'fecha_carga')
    search_fields = ('tipo_archivo', 'archivo_url')
    list_per_page = 20
    readonly_fields = ('fecha_carga',)
    
    def usuario_link(self, obj):
        if obj.fk_id_usuario:
            url = reverse('admin:NuamApp_usuario_change', args=[obj.fk_id_usuario.id_usuario])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_usuario.nombre)
        return "—"
    usuario_link.short_description = "Usuario"
    
    def archivo_preview(self, obj):
        if obj.archivo_url:
            return format_html('<code>{}</code>', obj.archivo_url[:50] + "..." if len(obj.archivo_url) > 50 else obj.archivo_url)
        return "—"
    archivo_preview.short_description = "Archivo"
    
    fieldsets = (
        ('Información del Archivo', {
            'fields': ('tipo_archivo', 'estado', 'archivo_url')
        }),
        ('Metadatos', {
            'fields': ('fecha_carga', 'fk_id_usuario'),
        }),
    )


# ==================== REPORTE ADMIN ====================
@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('id_reporte', 'tipo_reporte', 'fecha_generacion', 'usuario_link', 'archivo_preview')
    list_filter = ('tipo_reporte', 'fecha_generacion')
    search_fields = ('tipo_reporte', 'archivo_url')
    list_per_page = 20
    
    def usuario_link(self, obj):
        if obj.fk_id_usuario:
            url = reverse('admin:NuamApp_usuario_change', args=[obj.fk_id_usuario.id_usuario])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_usuario.nombre)
        return "—"
    usuario_link.short_description = "Usuario"
    
    def archivo_preview(self, obj):
        if obj.archivo_url:
            return format_html('<code>{}</code>', obj.archivo_url[:50] + "..." if len(obj.archivo_url) > 50 else obj.archivo_url)
        return "—"
    archivo_preview.short_description = "Archivo"


# ==================== AUDITORÍA ADMIN ====================
@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id_auditoria', 'accion', 'fecha_hora', 'resultado', 'usuario_link')
    list_filter = ('accion', 'resultado', 'fecha_hora')
    search_fields = ('accion', 'resultado')
    list_per_page = 20
    date_hierarchy = 'fecha_hora'
    
    def usuario_link(self, obj):
        if obj.fk_usuario:
            url = reverse('admin:NuamApp_usuario_change', args=[obj.fk_usuario.id_usuario])
            return format_html('<a href="{}">{}</a>', url, obj.fk_usuario.nombre)
        return "—"
    usuario_link.short_description = "Usuario"


# ==================== PERMISO ADMIN ====================
@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('id_permiso', 'nombre_permiso', 'descripcion', 'usuarios_count')
    search_fields = ('nombre_permiso', 'descripcion')
    list_per_page = 20
    readonly_fields = ('usuarios_asociados',)
    
    def usuarios_count(self, obj):
        count = UsuarioPermiso.objects.filter(fk_id_permiso=obj).count()
        if count > 0:
            url = reverse('admin:NuamApp_usuariopermiso_changelist') + f'?fk_id_permiso__id_permiso={obj.id_permiso}'
            return format_html('<a href="{}">{} usuario(s)</a>', url, count)
        return "—"
    usuarios_count.short_description = "Usuarios con permiso"
    
    def usuarios_asociados(self, obj):
        """Muestra usuarios que tienen este permiso"""
        usuario_permisos = UsuarioPermiso.objects.filter(fk_id_permiso=obj).select_related('fk_id_usuario')
        if not usuario_permisos.exists():
            return "Ningún usuario tiene este permiso"
        
        items = []
        for up in usuario_permisos:
            user_url = reverse('admin:NuamApp_usuario_change', args=[up.fk_id_usuario.id_usuario])
            items.append(format_html(
                '<li><a href="{}">{}</a> (Asignado: {})</li>',
                user_url, up.fk_id_usuario.nombre, up.fecha_asignacion
            ))
        
        return format_html('<ul>{}</ul>', ''.join(items))
    usuarios_asociados.short_description = "Usuarios con este permiso"


# ==================== USUARIO PERMISO ADMIN ====================
@admin.register(UsuarioPermiso)
class UsuarioPermisoAdmin(admin.ModelAdmin):
    list_display = ('id_usuario_permiso', 'usuario_link', 'permiso_link', 'fecha_asignacion')
    list_filter = ('fecha_asignacion', 'fk_id_permiso')
    search_fields = ('fk_id_usuario__nombre', 'fk_id_permiso__nombre_permiso')
    list_per_page = 20
    raw_id_fields = ('fk_id_usuario', 'fk_id_permiso')
    
    def usuario_link(self, obj):
        if obj.fk_id_usuario:
            url = reverse('admin:NuamApp_usuario_change', args=[obj.fk_id_usuario.id_usuario])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_usuario.nombre)
        return "—"
    usuario_link.short_description = "Usuario"
    
    def permiso_link(self, obj):
        if obj.fk_id_permiso:
            url = reverse('admin:NuamApp_permiso_change', args=[obj.fk_id_permiso.id_permiso])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_permiso.nombre_permiso)
        return "—"
    permiso_link.short_description = "Permiso"


# ==================== CALIFICACIÓN FACTOR ADMIN ====================
@admin.register(CalificacionFactor)
class CalificacionFactorAdmin(admin.ModelAdmin):
    list_display = ('id_calificacion_factor', 'calificacion_link', 'factor_link')
    list_filter = ('fk_id_factor',)
    search_fields = ('fk_id_calificacion__id_calificacion', 'fk_id_factor__nombre_factor')
    list_per_page = 20
    raw_id_fields = ('fk_id_calificacion', 'fk_id_factor')
    
    def calificacion_link(self, obj):
        if obj.fk_id_calificacion:
            url = reverse('admin:NuamApp_calificacion_change', args=[obj.fk_id_calificacion.id_calificacion])
            return format_html('<a href="{}">Calificación #{}</a>', url, obj.fk_id_calificacion.id_calificacion)
        return "—"
    calificacion_link.short_description = "Calificación"
    
    def factor_link(self, obj):
        if obj.fk_id_factor:
            url = reverse('admin:NuamApp_factor_change', args=[obj.fk_id_factor.id_factor])
            return format_html('<a href="{}">{}</a>', url, obj.fk_id_factor.nombre_factor)
        return "—"
    factor_link.short_description = "Factor"


# ==================== PERSONALIZACIÓN DEL SITE ADMIN ====================
admin.site.site_header = "NUAM - Administración"
admin.site.site_title = "NUAM Admin"
admin.site.index_title = "Panel de Administración"
# Eliminé la línea problemática: admin.site.index_template = 'admin/custom_index.html'