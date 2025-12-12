from django.db import models

class Archivocarga(models.Model):
    id_archivo = models.AutoField(db_column='ID_archivo', primary_key=True)
    tipo_archivo = models.CharField(max_length=30)
    fecha_carga = models.DateTimeField()
    estado = models.CharField(max_length=20)
    archivo_url = models.CharField(max_length=150, blank=True, null=True)
    # CAMBIADO: Usar cadena 'Usuario'
    fk_id_usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, db_column='FK_ID_usuario')

    class Meta:
        db_table = 'archivocarga'


class Auditoria(models.Model):
    id_auditoria = models.AutoField(primary_key=True)
    accion = models.CharField(max_length=100)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=500)
    # ⚠️ Asegúrate de que esta línea ESTÉ COMENTADA o ELIMINADA:
    # detalles = models.JSONField(null=True, blank=True)  # ← COMENTADA
    fk_usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        db_table = 'auditoria'
        verbose_name = 'Auditoría'
        verbose_name_plural = 'Auditorías'
    
    def __str__(self):
        return f"{self.accion} - {self.fecha_hora}"


class Calificacion(models.Model):
    MERCADOS = [
        ('acciones', 'Acciones'),
        ('cfi', 'CFI'),
        ('fondos_mutuos', 'Fondos Mutuos'),
    ]
    
    id_calificacion = models.AutoField(primary_key=True)
    fecha = models.DateField()
    mercado = models.CharField(max_length=30, choices=MERCADOS)
    ano = models.IntegerField()
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    factor_actualizado = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    # CAMBIADO: Usar cadena 'Corredor'
    fk_id_corredor = models.ForeignKey('Corredor', on_delete=models.CASCADE)
    instrumento = models.CharField(max_length=20, blank=True, null=True)
    secuencia_evento = models.IntegerField(default=10001)
    origen = models.CharField(max_length=20, default='manual', 
                             choices=[('manual', 'Manual'), ('csv', 'CSV'), ('sistema', 'Sistema')])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calificacion'
        ordering = ['-fecha']


class CalificacionFactor(models.Model):
    id_calificacion_factor = models.AutoField(db_column='ID_calificacion_factor', primary_key=True)
    # OK: Calificacion ya está definida arriba
    fk_id_calificacion = models.ForeignKey(Calificacion, on_delete=models.CASCADE, db_column='FK_ID_calificacion')
    # CAMBIADO: Usar cadena 'Factor'
    fk_id_factor = models.ForeignKey('Factor', on_delete=models.PROTECT, db_column='FK_ID_factor')

    class Meta:
        db_table = 'calificacion_factor'


class Corredor(models.Model):
    id_corredor = models.AutoField(db_column='ID_corredor', primary_key=True)
    nombre = models.CharField(max_length=30)
    rut = models.CharField(max_length=12)
    telefono = models.CharField(max_length=20)
    correo = models.CharField(max_length=50)
    fecha_registro = models.DateField()
    # CAMBIADO: Usar cadena 'Usuario'
    fk_usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, db_column='FK_usuario_ID')

    class Meta:
        db_table = 'corredor'


class Factor(models.Model):
    id_factor = models.AutoField(db_column='ID_factor', primary_key=True)
    nombre_factor = models.CharField(max_length=50)
    valor_factor = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        db_table = 'factor'


class Permiso(models.Model):
    id_permiso = models.AutoField(db_column='ID_permiso', primary_key=True)
    nombre_permiso = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100)

    class Meta:
        db_table = 'permiso'


# AÑADE ESTA CLASE SI NO LA TIENES (pero veo que SÍ la tienes en tu código)
class Reporte(models.Model):
    id_reporte = models.AutoField(db_column='ID_reporte', primary_key=True)
    tipo_reporte = models.CharField(max_length=30)
    fecha_generacion = models.DateField()
    archivo_url = models.CharField(max_length=150, blank=True, null=True)
    # CAMBIADO: Usar cadena 'Usuario'
    fk_id_usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, db_column='FK_ID_usuario')

    class Meta:
        db_table = 'reporte'


class Usuario(models.Model):
    id_usuario = models.AutoField(db_column='ID_usuario', primary_key=True)
    nombre = models.CharField(max_length=15)
    correo = models.CharField(max_length=50)
    contrasena = models.CharField(max_length=128)
    rol = models.CharField(max_length=20)
    estado = models.CharField(max_length=10)

    class Meta:
        db_table = 'usuario'


class UsuarioPermiso(models.Model):
    id_usuario_permiso = models.AutoField(db_column='ID_usuario_permiso', primary_key=True)
    fecha_asignacion = models.DateField()
    # OK: Usuario ya está definido arriba
    fk_id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='FK_ID_usuario')
    # OK: Permiso ya está definido arriba
    fk_id_permiso = models.ForeignKey(Permiso, on_delete=models.PROTECT, db_column='FK_ID_permiso')

    class Meta:
        db_table = 'usuario_permiso'