from rest_framework import permissions


class IsAdminOrPropertyManager(permissions.BasePermission):
    """
    property_manager: can list/retrieve/create/update leases, upload, process,
    and ask questions.
    admin: everything property_manager can do, plus delete.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "destroy":
            return request.user.role == "admin"
        return request.user.role in ("admin", "property_manager")

    def has_object_permission(self, request, view, obj):
        if view.action == "destroy":
            return request.user.role == "admin"
        return request.user.role in ("admin", "property_manager")


class IsAdminForDelete(permissions.BasePermission):
    """Generic version of the above for non-ViewSet views that only need delete-gating."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return request.user.role == "admin"
        return True
