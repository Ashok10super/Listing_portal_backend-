from fastapi import APIRouter,Request
from starlette import status
from starlette.responses import JSONResponse
from data_validation.input_data_validator import validate_auth_input
from error_codes.auth_error_code import AuthErrorCode
from repository.user_repository import UserRepository
from repository.role_respository import RoleRepository
from repository.auth_repository import AuthRepository
from service.auth_service import AuthService

auth_router = APIRouter(prefix="/v1/auth", tags=["auth"])

@auth_router.post("/register")
async def register_admin(request: Request)->JSONResponse:

    data = await request.body()

    validation_response  = validate_auth_input(data,["username","email","phone","password","role"])

    if validation_response.get("is_error"):
        return JSONResponse(status_code=validation_response.get("status_code"),content={"data":validation_response.get("response")})


    user_repository = UserRepository(request.app.state.database_connection)
    role_repository = RoleRepository(request.app.state.database_connection)
    auth_repository = AuthRepository(request.app.state.database_connection)

    auth_service = AuthService(user_repository=user_repository, role_repository=role_repository, auth_repository=auth_repository)

    data = validation_response.get("response").get("data")
    target_role = str(data.get("role", "")).upper()

    # Restrict ADMIN creation to SUPER_ADMIN users only
    if target_role == "ADMIN":
        token = request.cookies.get("access_token")
        if not token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"data": {"code": AuthErrorCode.AU121.name, "message": "Unauthorized: Only Super Admin can register Admin users", "data": None}}
            )
        token_res = AuthService.get_decoded_jwt_token(token)
        if token_res.get("is_error"):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"data": {"code": AuthErrorCode.AU121.name, "message": "Unauthorized: Invalid or expired token", "data": None}}
            )
        payload = token_res.get("return_data", {}).get("payload", {})
        if str(payload.get("role", "")).upper() != "SUPER_ADMIN":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"data": {"code": AuthErrorCode.AU121.name, "message": "Unauthorized: Only Super Admin can register Admin users", "data": None}}
            )

    print("This is the input data", data)

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
        return JSONResponse(status_code=status_code,content={"data":service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_201_CREATED,content={"data":service_response.get("response")})


@auth_router.post("/login")
async def login(request: Request)->JSONResponse:
    data = await request.body()
    validation_response = validate_auth_input(data,["email_id","password"],is_login=True)

    if validation_response.get("is_error"):
        return JSONResponse(status_code=validation_response.get("status_code"),content={"data":validation_response.get("response")})

    user_repository = UserRepository(request.app.state.database_connection)
    auth_repository = AuthRepository(request.app.state.database_connection)

    auth_service = AuthService(user_repository=user_repository,auth_repository=auth_repository,role_repository=None)

    input_data =  validation_response.get("response").get("data")
    login_identifier = input_data.get("email_id") or input_data.get("email") or input_data.get("data")

    service_response = await auth_service.get_login(data=login_identifier,password=input_data.get("password"))


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
async def logout(request: Request)->JSONResponse:
    auth_service = AuthService(user_repository=None,auth_repository=None,role_repository=None)
    service_response = auth_service.get_logout()
    response = JSONResponse(status_code=status.HTTP_200_OK,content={"data":service_response.get("response")})
    response.delete_cookie(key="access_token")
    return response



