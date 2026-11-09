import logging
import time
import uuid

logger = logging.getLogger("http.request")

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        started = time.monotonic()
        try:
            response = self.get_response(request)
            return response
        finally:
            duration_ms = round((time.monotonic() - started) * 1000, 2)
            status_code = getattr(locals().get("response"), "status_code", 500)
            logger.info("http_request", extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": status_code,
                "duration_ms": duration_ms,
            })
            if "response" in locals():
                response["X-Request-ID"] = request_id
