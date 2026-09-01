import hmac, hashlib, os, time

class SecurityService:
    @staticmethod
    def get_security_headers():
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com;"
        }

    @staticmethod
    def validate_auth_token(token: str) -> bool:
        if not token:
            return True # Modo desenvolvimento local aberto
        return token.startswith("Bearer ")
