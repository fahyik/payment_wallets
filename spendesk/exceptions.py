"""
This is my personal exception_handler written for handling errors through exceptions in
Django Rest Framework
"""

from django.http import Http404, JsonResponse

from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    ParseError,
    PermissionDenied
)
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as SerializerValidationError
from rest_framework.views import set_rollback


class BaseApiError(Exception):
    """
    Base error class that provides a method to return the defined
    http error response in a python dictionary
    """

    error_type = None
    status_code = None

    def __init__(self, message="", data=None, *args, **kwargs):

        if not self.error_type:
            raise NotImplementedError(
                "Please define attribute 'error_type' on class {}".format(self.__class__.__name__)
            )

        if not self.status_code:
            raise NotImplementedError(
                "Please define attribute 'status_code' on class {}".format(self.__class__.__name__)
            )

        self.message = str(message)
        self.data = data
        super(BaseApiError, self).__init__(message, *args, **kwargs)

    def to_dict(self):

        return {
            "error_type": self.error_type,
            "status_code": self.status_code,
            "message": self.message,
            "data": self.data
        }


class AuthorizationError(BaseApiError):

    error_type = 'authentication_error'
    status_code = 401
    auth_header = ''


class BadRequestError(BaseApiError):
    """ Generic 400 BAD REQUEST error """

    error_type = 'bad_request'
    status_code = 400


class InternalServerError(BaseApiError):

    error_type = 'internal_server_error'
    status_code = 500


class MethodNotAllowedError(BaseApiError):

    error_type = 'method_not_allowed'
    status_code = 405


class NotFoundError(BaseApiError):

    error_type = 'not_found'
    status_code = 404


class PermissionDeniedError(BaseApiError):

    error_type = 'authentication_error'
    status_code = 403


class ValidationError(BadRequestError):

    error_type = 'validation_error'


def _parse_drf_serializer_validation_error(exc):

    messages = []
    for err, detail in exc.items():

        msg = "Field: '{}' is {}".format(err, detail[0]['code'])

        if detail[0]['code'] == 'invalid':
            msg = "{}. {}".format(msg, detail[0]['message'])

        messages.append(msg)

    return messages


def django_handler_404(request, *args, **kwargs):
    """
    Generic 404 error handler in JSON
    """

    exc = NotFoundError("The resource '{}' does not exist".format(request.path))

    return JsonResponse(
        data=exc.to_dict(),
        status=exc.status_code
    )


def django_handler_500(request, *args, **kwargs):
    """
    Generic 500 error handler in JSON
    """
    exc = InternalServerError("Internal server error")

    return JsonResponse(
        data=exc.to_dict(),
        status=exc.status_code
    )


def exception_handler(exc, context):
    """
    Custom exception handler for Django Rest Framework
    Returns the defined error format for each Error type in json
    for e.g.:
    {
        "error_type": "api_error",
        "status_code": 400,
        "message": "Unable to create layout"
        "data": null (optional)
    }
    """
    headers = {
        'content-type': 'application/json'
    }

    if isinstance(exc, Http404):
        exc = NotFoundError("The resource '{}' does not exist".format(context['request'].path))

    elif isinstance(exc, MethodNotAllowed):
        exc = MethodNotAllowedError(
            "Method {} not allowed on resource '{}'".format(
                context['request'].method,
                context['request'].path
            )
        )

    elif isinstance(exc, PermissionDenied):
        exc = PermissionDeniedError(exc)

    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        exc = AuthorizationError(exc)

    elif isinstance(exc, ParseError):
        exc = ValidationError(exc)

    elif isinstance(exc, SerializerValidationError):
        """
        Reformat the default DRF serializer validation error

        We need two ways of handing the SerializerValidationError,
        if many=True is passed to serializer, it will return a list of error objects,
        other just an error object

        Set error_type as validation_error
        """
        messages = []

        if isinstance(exc.get_full_details(), list):
            for each in exc.get_full_details():
                messages.append(_parse_drf_serializer_validation_error(each))
        else:
            messages = _parse_drf_serializer_validation_error(exc.get_full_details())

        exc = ValidationError("Invalid request parameters or data", data=messages)

    elif isinstance(exc, BaseApiError):
        pass

    else:
        exc = InternalServerError(exc)

    # important to set_rollback here
    # transaction will be rolled back if ATOMIC_REQUESTS for DATABASE is set to True
    set_rollback()

    return Response(
        data=exc.to_dict(),
        status=exc.status_code,
        headers=headers
    )
