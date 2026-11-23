"""Security headers, including a strict Content-Security-Policy with a per-request nonce."""
import secrets

from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        admin_path = "/" + settings.ADMIN_URL
        if request.path.startswith(admin_path):
            # Django's own admin needs inline scripts/styles; keep it on a separate, slightly looser policy.
            csp = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                   "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        else:
            csp = ("default-src 'self'; "
                   f"script-src 'self' 'nonce-{request.csp_nonce}'; "
                   "style-src 'self' https://fonts.googleapis.com; style-src-attr 'unsafe-inline'; "
                   "font-src 'self' https://fonts.gstatic.com; "
                   "img-src 'self' data: blob:; "
                   "connect-src 'self' ws: wss:; "
                   "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        header = "Content-Security-Policy-Report-Only" if settings.CSP_REPORT_ONLY else "Content-Security-Policy"
        response.headers.setdefault(header, csp)
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


def csp_nonce(request):
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
