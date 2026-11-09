import logging
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def safe_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    request = context.get("request")
    request_id = getattr(request, "request_id", None)
    logger.exception("Unhandled API exception", extra={"request_id": request_id})
    from rest_framework.response import Response
    return Response({"detail": "Внутренняя ошибка сервера", "request_id": request_id}, status=500)
