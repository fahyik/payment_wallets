from rest_framework import permissions

from .models import Wallet, Card


class SpendeskIsOwnCompanyPermission(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    In this case, we restrict the permissions in two cases:
    If object being retrieved is Wallet:
        we check that wallet.company_id = request.auth['company_id']
    If object being retrieved is Card:
        we check that card.wallet.company_id = request.auth['company_id']
    """
    message = 'You do not have permission to access this card or wallet'

    def has_object_permission(self, request, view, obj):

        if isinstance(obj, Wallet):
            return obj.company_id == request.auth['company_id']

        if isinstance(obj, Card):
            return obj.wallet.company_id == request.auth['company_id']
