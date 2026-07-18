from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Profil


def role_requis(*roles):
    """Décorateur Django qui n'autorise que les utilisateurs dont le rôle
    correspond à l'un des rôles indiqués.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            profil = getattr(request.user, "profil", None)
            if profil is None or profil.role not in roles:
                raise PermissionDenied("Accès refusé : rôle insuffisant.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
