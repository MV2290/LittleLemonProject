# permissions.py
from rest_framework import permissions

class IsManagerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow managers to modify user records.
    """

    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow modification only if the user is a manager
        return request.user and request.user.is_staff
