from rest_framework.permissions import BasePermission


class IsCoordinator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['COORDINATOR', 'ADMIN']
        )


class IsFieldStaffOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['FIELD_STAFF', 'COORDINATOR', 'ADMIN']
        )