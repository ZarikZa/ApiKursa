# apihh_main/middleware.py
import time

class RequestStartLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        print(f"[REQ] {request.method} {request.path} len={request.META.get('CONTENT_LENGTH')}")
        resp = self.get_response(request)
        dt = int((time.time() - t0)*1000)
        print(f"[RESP] {request.method} {request.path} -> {resp.status_code} in {dt}ms")
        return resp
