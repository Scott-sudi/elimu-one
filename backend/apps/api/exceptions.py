from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        errors = response.data
        message = "Une erreur est survenue."
        if isinstance(errors, dict):
            detail = errors.get("detail")
            if detail:
                message = str(detail)
        elif isinstance(errors, list) and errors:
            message = str(errors[0])
        response.data = {
            "success": False,
            "message": message,
            "data": {},
            "errors": errors,
        }
    return response
