
from django.contrib import admin
from .models import Usuario, Corredor, Calificacion, Factor, Archivocarga, Reporte, Auditoria, Permiso, UsuarioPermiso, CalificacionFactor

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'nombre', 'correo', 'rol', 'estado')
    list_filter = ('estado', 'rol')
    search_fields = ('nombre', 'correo')
    list_editable = ('estado',)

@admin.register(Corredor)
class CorredorAdmin(admin.ModelAdmin):
    list_display = ('id_corredor', 'nombre', 'rut', 'correo', 'fecha_registro')
    search_fields = ('nombre', 'rut')

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('id_calificacion', 'fecha', 'mercado', 'fk_id_corredor')
    list_filter = ('mercado', 'fecha')

@admin.register(Factor)
class FactorAdmin(admin.ModelAdmin):
    list_display = ('id_factor', 'nombre_factor', 'valor_factor')

# Registrar los demás modelos básicamente
admin.site.register(Archivocarga)
admin.site.register(Reporte)
admin.site.register(Auditoria)
admin.site.register(Permiso)
admin.site.register(UsuarioPermiso)
admin.site.register(CalificacionFactor)