from django.contrib import admin
from django.urls import path
from NuamApp import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # LOGIN
    path('', views.login_view, name='login'),

    # DASHBOARDS POR ROL
    path('dashboard-admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard-corredor/', views.dashboard_corredor, name='dashboard_corredor'),

    # LOGOUT
    path('logout/', views.logout_view, name='logout'),

    # REGISTRO
    path('registro/', views.registro_view, name='registro'),

    # CALIFICACIONES
    path('mis-calificaciones/', views.dashboard_corredor, name='calificaciones'),
    path('agregar-calificacion/', views.agregar_calificacion, name='agregar_calificacion'),
    path('editar-calificacion/<int:calificacion_id>/', views.editar_calificacion_view, name='editar_calificacion'),
    path('eliminar-calificacion/<int:calificacion_id>/', views.eliminar_calificacion_view, name='eliminar_calificacion'),

    # CARGAS MASIVAS
    path('carga-factores/', views.carga_factores, name='carga_factores'),
    path('carga-montos/', views.carga_masiva_montos, name='carga_montos'),
    path('listado-cargas/', views.listado_cargas, name='listado_cargas'),
    path('carga-masiva-calificaciones/', views.carga_masiva_calificaciones, name='carga_masiva_calificaciones'),
    path('detalles-carga/<int:carga_id>/', views.ver_detalles_carga, name='detalles_carga'),
    path('descargar-carga/<int:carga_id>/', views.descargar_reporte_carga, name='descargar_carga'),
    path('extraer-datos-pdf/', views.extraer_datos_pdf, name='extraer_datos_pdf'),
    path('guardar-datos-pdf/', views.guardar_datos_extraidos, name='guardar_datos_extraidos'),
    # ERROR DE PERMISOS
    path("no-autorizado/", views.no_autorizado, name="no_autorizado"),
    path("fix-passwords/", views.fix_passwords),

    # CRUD USUARIOS
    path('gestion-usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('crear-usuario/', views.crear_usuario, name='crear_usuario'),
    path('editar-usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('activar-usuario/<int:usuario_id>/', views.activar_usuario, name='activar_usuario'),
    path('desactivar-usuario/<int:usuario_id>/', views.desactivar_usuario, name='desactivar_usuario'),
    path('eliminar-usuario/<int:usuario_id>/', views.eliminar_usuario, name='eliminar_usuario'),
]