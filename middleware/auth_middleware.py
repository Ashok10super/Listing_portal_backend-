import re
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status
from error_codes.auth_error_code import AuthErrorCode
from service.auth_service import AuthService


async def auth_middleware(request: Request, call_next):
        public_routes = [r"^/v1/auth/login$",
                        r"^/v1/auth/register$"]
        # Check if the current path matches any of our regex patterns
        is_public = any(re.match(pattern, request.url.path) for pattern in public_routes)

        if request.method == "OPTIONS" or is_public:
            return await call_next(request)

        token = request.cookies.get('access_token')
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"data":{"code":AuthErrorCode.AU121.name, "message":AuthErrorCode.AU121.value,"data":None}},
            )

        service_response = AuthService.get_decoded_jwt_token(token)

        if service_response.get("is_error"):
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"data": service_response.get("response")})

        decoded_jwt_token = service_response.get("return_data").get("payload")
        print(decoded_jwt_token)
        request.state.user_id = decoded_jwt_token['user_id']
        request.state.role = decoded_jwt_token['role']
        user = request.state.user_id
        role = request.state.role
        print(f"User ID from middleware: {user}","role",role)
        return await call_next(request)
