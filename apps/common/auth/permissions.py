from rest_framework import permissions


class HasRole(permissions.BasePermission):
    """Permission factory: HasRole('admin','staff')."""

    def __init__(self, *roles: str) -> None:
        self.roles = set(roles)

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False) and user.role in self.roles)


def role_permission(*roles: str):
    """Returns a permission class bound to the given roles."""

    class _Bound(HasRole):
        def __init__(self) -> None:  # DRF instantiates without args
            super().__init__(*roles)

    _Bound.__name__ = f"HasRole_{'_'.join(roles)}"
    return _Bound


IsAdmin = role_permission("admin")
IsAdminOrStaff = role_permission("admin", "staff")
IsCustomer = role_permission("customer")
