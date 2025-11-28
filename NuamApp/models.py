from django.db import models

class Archivocarga(models.Model):
    id_archivo = models.AutoField(db_column='ID_archivo', primary_key=True)  # Field name made lowercase.
    tipo_archivo = models.CharField(max_length=30)
    fecha_carga = models.DateTimeField()
    estado = models.CharField(max_length=20)
    archivo_url = models.CharField(max_length=150, blank=True, null=True)
    fk_id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='FK_ID_usuario')  # Field name made lowercase.

    class Meta:
        db_table = 'archivocarga'


class Auditoria(models.Model):
    id_auditoria = models.AutoField(db_column='ID_auditoria', primary_key=True)  # Field name made lowercase.
    accion = models.CharField(max_length=20)
    fecha_hora = models.DateTimeField()
    resultado = models.CharField(max_length=50)
    fk_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='FK_usuario_ID')  # Field name made lowercase.

    class Meta:
        db_table = 'auditoria'


class Calificacion(models.Model):
    id_calificacion = models.AutoField(db_column='ID_calificacion', primary_key=True)  # Field name made lowercase.
    fecha = models.DateField()
    mercado = models.CharField(max_length=30)
    ano = models.IntegerField()
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    factor_actualizado = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    fk_id_corredor = models.ForeignKey('Corredor', models.DO_NOTHING, db_column='FK_ID_corredor')  # Field name made lowercase.

    class Meta:
        db_table = 'calificacion'


class CalificacionFactor(models.Model):
    id_calificacion_factor = models.AutoField(db_column='ID_calificacion_factor', primary_key=True)  # Field name made lowercase.
    fk_id_calificacion = models.ForeignKey(Calificacion, models.DO_NOTHING, db_column='FK_ID_calificacion')  # Field name made lowercase.
    fk_id_factor = models.ForeignKey('Factor', models.DO_NOTHING, db_column='FK_ID_factor')  # Field name made lowercase.

    class Meta:
        db_table = 'calificacion_factor'


class Corredor(models.Model):
    id_corredor = models.AutoField(db_column='ID_corredor', primary_key=True)  # Field name made lowercase.
    nombre = models.CharField(max_length=30)
    rut = models.CharField(max_length=12)
    telefono = models.CharField(max_length=20)
    correo = models.CharField(max_length=50)
    fecha_registro = models.DateField()
    fk_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='FK_usuario_ID')  # Field name made lowercase.

    class Meta:
        db_table = 'corredor'


class Factor(models.Model):
    id_factor = models.AutoField(db_column='ID_factor', primary_key=True)  # Field name made lowercase.
    nombre_factor = models.CharField(max_length=50)
    valor_factor = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        db_table = 'factor'


class Permiso(models.Model):
    id_permiso = models.AutoField(db_column='ID_permiso', primary_key=True)  # Field name made lowercase.
    nombre_permiso = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100)

    class Meta:
        db_table = 'permiso'


class Reporte(models.Model):
    id_reporte = models.AutoField(db_column='ID_reporte', primary_key=True)  # Field name made lowercase.
    tipo_reporte = models.CharField(max_length=30)
    fecha_generacion = models.DateField()
    archivo_url = models.CharField(max_length=150, blank=True, null=True)
    fk_id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='FK_ID_usuario')  # Field name made lowercase.

    class Meta:
        db_table = 'reporte'


class Usuario(models.Model):
    id_usuario = models.AutoField(db_column='ID_usuario', primary_key=True)  # Field name made lowercase.
    nombre = models.CharField(max_length=15)
    correo = models.CharField(max_length=50)
    contrasena = models.CharField(max_length=128)
    rol = models.CharField(max_length=20)
    estado = models.CharField(max_length=10)

    class Meta:
        db_table = 'usuario'


class UsuarioPermiso(models.Model):
    id_usuario_permiso = models.AutoField(db_column='ID_usuario_permiso', primary_key=True)  # Field name made lowercase.
    fecha_asignacion = models.DateField()
    fk_id_usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='FK_ID_usuario')  # Field name made lowercase.
    fk_id_permiso = models.ForeignKey(Permiso, models.DO_NOTHING, db_column='FK_ID_permiso')  # Field name made lowercase.

    class Meta:
        db_table = 'usuario_permiso'