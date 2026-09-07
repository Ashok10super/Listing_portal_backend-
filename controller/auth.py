from fastapi import APIRouter,Request
from starlette import status
from starlette.responses import JSONResponse
from data_validation.input_data_validator import validate_auth_input
from error_codes.auth_error_code import AuthErrorCode
from repository.user_repository import UserRepository
from repository.role_respository import RoleRepository
from repository.auth_repository import AuthRepository
from service.auth_service import AuthService

auth_router = APIRouter(tags=["auth"])


def _extract_caller_role(request: Request) -> str | None:
    role = getattr(request.state, "role", None)
    if role:
        return str(role).upper()

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")

    if token:
        token_res = AuthService.get_decoded_jwt_token(token)
        if not token_res.get("is_error"):
            payload = token_res.get("return_data", {}).get("payload", {})
            return str(payload.get("role", "")).upper()

    return None


@auth_router.post("/register")
@auth_router.post("/v1/auth/register")
async def register_user_or_admin(request: Request) -> JSONResponse:
    data = await request.body()
    validation_response = validate_auth_input(data, ["username", "email", "phone", "password", "role"])

    if validation_response.get("is_error"):
        return JSONResponse(status_code=validation_response.get("status_code"), content={"data": validation_response.get("response")})

    user_repository = UserRepository(request.app.state.database_connection)
    role_repository = RoleRepository(request.app.state.database_connection)
    auth_repository = AuthRepository(request.app.state.database_connection)

    auth_service = AuthService(user_repository=user_repository, role_repository=role_repository, auth_repository=auth_repository)

    data = validation_response.get("response").get("data")
    target_role = str(data.get("role", "")).upper()

    # Restrict ADMIN / SUPER_ADMIN creation to SUPER_ADMIN users only
    if target_role in ("ADMIN", "SUPER_ADMIN"):
        caller_role = _extract_caller_role(request)
        if caller_role != "SUPER_ADMIN":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"data": {"code": AuthErrorCode.AU121.name, "message": "Unauthorized: Only Super Admin can register Admin users", "data": None}}
            )

    service_response = await auth_service.register_user(
        data.get("username"),
        data.get("email"),
        data.get("phone"),
        data.get("password"),
        data.get("role"),
    )

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response").get("code") != AuthErrorCode.AU107.name:
            status_code = status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"data": service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"data": service_response.get("response")})


@auth_router.post("/login")
@auth_router.post("/v1/auth/login")
async def login(request: Request) -> JSONResponse:
    data = await request.body()
    validation_response = validate_auth_input(data, ["email_id", "password"], is_login=True)

    if validation_response.get("is_error"):
        return JSONResponse(status_code=validation_response.get("status_code"), content={"data": validation_response.get("response")})

    user_repository = UserRepository(request.app.state.database_connection)
    auth_repository = AuthRepository(request.app.state.database_connection)

    auth_service = AuthService(user_repository=user_repository, auth_repository=auth_repository, role_repository=None)

    input_data = validation_response.get("response").get("data")
    login_identifier = input_data.get("email_id") or input_data.get("email") or input_data.get("username") or input_data.get("data")

    service_response = await auth_service.get_login(data=login_identifier, password=input_data.get("password"))

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response").get("code") != AuthErrorCode.AU107.name:
            status_code = status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"data": service_response.get("response")})

    cookie_expiry_time = service_response.get("return_data").get("cookie_expiry_time")
    jwt_token = service_response.get("return_data").get("jwt_token")

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "data": service_response.get("response")
        }
    )

    response.set_cookie(
        key="access_token",
        value=jwt_token,
        expires=cookie_expiry_time,
        httponly=False,
        secure=False,
        samesite="lax"
    )

    return response


@auth_router.post("/logout")
@auth_router.post("/v1/auth/logout")
async def logout(request: Request) -> JSONResponse:
    auth_service = AuthService(user_repository=None, auth_repository=None, role_repository=None)
    service_response = auth_service.get_logout()
    response = JSONResponse(status_code=status.HTTP_200_OK, content={"data": service_response.get("response")})
    response.delete_cookie(key="access_token")
    return response


@auth_router.get("/users")
@auth_router.get("/v1/auth/users")
async def get_all_users(request: Request) -> JSONResponse:
    caller_role = _extract_caller_role(request)
    if caller_role != "SUPER_ADMIN":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": "Unauthorized: Only Super Admin can view user directory", "data": None}}
        )

    user_repository = UserRepository(request.app.state.database_connection)
    users = await user_repository.get_all_users()

    # Format datetime objects for JSON serialization
    serialized_users = []
    for u in users:
        u_dict = dict(u)
        if u_dict.get("created_at"):
            u_dict["created_at"] = u_dict["created_at"].isoformat()
        serialized_users.append(u_dict)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": {"code": "AU123", "message": "Users fetched successfully", "data": serialized_users}}
    )



