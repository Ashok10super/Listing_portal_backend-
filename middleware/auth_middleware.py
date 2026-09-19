import re
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status
from error_codes.auth_error_code import AuthErrorCode
from service.auth_service import AuthService


async def auth_middleware(request: Request, call_next):
    # Initialize request state
    request.state.user_id = None
    request.state.role = None

    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    method = request.method

    # Always public auth routes
    always_public_routes = [
        r"^/v1/auth/login$",
        r"^/v1/auth/register$",
        r"^/login$",
        r"^/register$",
    ]
    is_always_public = any(re.match(pattern, path) for pattern in always_public_routes)

    # Public property GET routes (excluding /liked and /{id}/like)
    is_public_property_get = (
        method == "GET" and (
            re.match(r"^/(v1/)?properties/?$", path) or
            re.match(r"^/(v1/)?properties/(owner_id|\d+)$", path) or
            re.match(r"^/(v1/)?properties/(metrics|stats|summary)$", path)
        )
    )

    is_public = is_always_public or is_public_property_get

    # Extract token from Authorization Bearer header or access_token cookie
    token = None
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")

    if token:
        service_response = AuthService.get_decoded_jwt_token(token)
        if not service_response.get("is_error"):
            decoded_jwt_token = service_response.get("return_data", {}).get("payload", {})
            request.state.user_id = decoded_jwt_token.get("user_id")
            request.state.role = decoded_jwt_token.get("role")

    if is_public:
        return await call_next(request)

    # Protected routes require valid token
    if not token or not request.state.user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": AuthErrorCode.AU121.value, "data": None}},
        )

    return await call_next(request)
