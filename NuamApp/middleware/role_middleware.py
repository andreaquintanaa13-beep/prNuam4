from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class CustomRoleMiddleware:
    """
    Middleware para restringir acceso según el rol almacenado en session.
    No usa modelos, solo verifica request.session['rol'].
    """

    # Rutas protegidas para cada tipo de usuario
    ROL_CORREDOR_PATHS = [
        "/dashboard-corredor/",
        "/mis-calificaciones/",
        "/agregar-calificacion/",
        "/editar-calificacion/",
        "/eliminar-calificacion/",
    ]

    ROL_ADMIN_PATHS = [
        "/gestion-usuarios/",
        "/crear-permisos/",
        "/editar-usuario/",
        "/eliminar-usuario/",
        "/permisos/",
        "/listado-cargas/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Obtiene el rol desde la sesión
        rol = request.session.get("rol", None)
        path = request.path

        # Permitir acceso público a login, logout y registro
        rutas_publicas = ["/", "/logout/", "/registro/"]
        if path in rutas_publicas:
            return self.get_response(request)

        # Si no está logueado → al login
        if rol is None:
            return redirect("/")

        # Validación para CORREDOR
        if rol == "corredor":
            if any(path.startswith(p) for p in self.ROL_CORREDOR_PATHS):
                return self.get_response(request)
            else:
                return redirect(reverse("no_autorizado"))

        # Validación para ADMIN
        if rol == "admin":
            if any(path.startswith(p) for p in self.ROL_ADMIN_PATHS):
                return self.get_response(request)
            else:
                return redirect(reverse("no_autorizado"))

        # Si el rol no coincide con nada → denegar
        return redirect(reverse("no_autorizado"))


ROLL_PERMISOS = {
    "/dashboard-admin/": ["admin"],
    "/dashboard-corredor/": ["corredor"],
}

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        ruta = request.path

        # Si la ruta está protegida
        if ruta in ROLL_PERMISOS:

            # Verifica que el usuario esté logueado
            if "rol" not in request.session:
                return redirect("login")

            rol_usuario = request.session.get("rol")

            # Si no tiene permiso
            if rol_usuario not in ROLL_PERMISOS[ruta]:
                return redirect("no_autorizado")

        return self.get_response(request)

class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # 1. PERMITIR ACCESO A DJANGO ADMIN COMPLETAMENTE
        if request.path.startswith("/admin/"):
            # Verificar si el usuario está autenticado en Django Admin
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            return self.get_response(request)

        # 2. Rutas públicas de TU aplicación
        rutas_publicas = [
            "/login/",
            "/registro/", 
            "/",
            "/logout/",
            "/static/",
            "/media/",
        ]

        # Si es ruta pública → permitir
        if any(request.path.startswith(ruta) for ruta in rutas_publicas):
            return self.get_response(request)

        # 3. Para TODAS las demás rutas, verificar TU sesión personalizada
        if "usuario_id" not in request.session:
            messages.error(request, "Debes iniciar sesión primero.")
            return redirect("login")

        return self.get_response(request)