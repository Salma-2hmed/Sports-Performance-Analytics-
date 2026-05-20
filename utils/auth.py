import functools
from flask import request, jsonify
VALID_TOKENS = {
    "admin-token-001": {"role": "admin", "user": "admin"},
    "coach-token-002": {"role": "coach", "user": "coach1"},
    "analyst-token-003": {"role": "analyst", "user": "analyst1"},
}
def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        if token not in VALID_TOKENS:
            return jsonify({"error": "Invalid token"}), 403
        request.current_user = VALID_TOKENS[token]
        return f(*args, **kwargs)
    return wrapper

def require_role(*roles):
    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def wrapper(*args, **kwargs):
            user = getattr(request, "current_user", {})
            if user.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator