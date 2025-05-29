from django.core.mail import EmailMessage
import os
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import BasePermission


class IsAdminUserCustom(BasePermission):
    """
    Allows access only to admin users (is_admin=True).
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


def get_tokens_for_user(user):
  """
    Generate JWT refresh and access tokens for a given user.

    Args:
        user (User): The user instance for whom the tokens are to be generated.

    Returns:
        dict: A dictionary containing 'refresh' and 'access' JWT tokens as strings.
  """
  refresh = RefreshToken.for_user(user)
  return {
      'refresh': str(refresh),
      'access': str(refresh.access_token),
  }


