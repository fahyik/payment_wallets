import uuid

from django.contrib.auth.models import User

from rest_framework import authentication, exceptions


class SpendeskAuthentication(authentication.BaseAuthentication):
    """
    Simple "Authentication" class to check for User-Id and Company-Id
    headers in request

    Sets an auth object on the request such that we can retrieve the two
    properties easily from within the view, i.e.
    request.auth['user-id'] and request.auth['company-id']
    """

    def authenticate(self, request):

        user_id = request.META.get('HTTP_USER_ID')
        company_id = request.META.get('HTTP_COMPANY_ID')

        if not user_id:
            raise exceptions.AuthenticationFailed('No user id provided')
        elif not company_id:
            raise exceptions.AuthenticationFailed('No company id provided')

        try:
            # sets a dummy Django user object on the request, required by framework
            user = User(
                id=uuid.UUID(user_id)
            )

            auth = dict(
                user_id=uuid.UUID(user_id),
                company_id=uuid.UUID(company_id)
            )

        except ValueError:
            raise exceptions.AuthenticationFailed('User and company ids have to be of type UUID')

        return (user, auth)
