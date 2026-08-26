import os
from datetime import datetime, timezone ,timedelta
import asyncpg
import bcrypt
import logging
import dotenv
import jwt
from config import Role
from error_codes.auth_error_code import AuthErrorCode
from repository.auth_repository import AuthRepository
from repository.user_repository import UserRepository
from repository.role_respository import RoleRepository

dotenv.load_dotenv()

class AuthService:
    def __init__(self, user_repository: UserRepository,role_repository: RoleRepository, auth_repository: AuthRepository):
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.auth_repository = auth_repository

    async def register_user(self, username: str, email: str, phone:str,password:str,role:str) -> dict:
        try:
            if await self.__is_username_exists(username):
                return self.__get_service_response(AuthErrorCode.AU113.name, AuthErrorCode.AU113.value)

            if await self.__is_email_exists(email):
                return self.__get_service_response(AuthErrorCode.AU113.name, AuthErrorCode.AU113.value)

            auth_id_dict = await self.__create_auth(password)

            if not auth_id_dict:
                return self.__get_service_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value)

            auth_id = auth_id_dict.get("auth_id")

            role_id = await self.role_repository.get_role_id_by_role(role)

            if not role_id:
                return self.__get_service_response(AuthErrorCode.AU115.name, AuthErrorCode.AU115.value)

            print("auth_id",auth_id,"role_id",role_id)
            user = await self.user_repository.create_user(username, email, phone,auth_id, role_id)
            return self.__get_service_response(
                AuthErrorCode.AU114.name,
                AuthErrorCode.AU114.value,
                is_error=False,
                data=user,
            )
        except asyncpg.exceptions.UniqueViolationError as e:
            logging.info(str(e))
            return self.__get_service_response(AuthErrorCode.AU113.name, AuthErrorCode.AU113.value)
        except asyncpg.exceptions.PostgresError as e:
            logging.info(str(e))
            return self.__get_service_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value)

    async def __is_email_exists(self, email: str) -> bool:
        return await self.user_repository.get_user_by_email(email) is not None

    async def __is_username_exists(self, username: str) -> bool:
        return await self.user_repository.get_user_by_username(username) is not None

    async def __create_auth(self,password:str):
        hashed_password = self.__get_hashed_password(password)
        return await self.auth_repositor.create_auth_record(hashed_password)

    async def get_login(self,data:str,password:str)-> dict:
        try:
            user = None #holds the user data

            if self.__data_is_email(data):
                user = await self.user_repository.get_user_for_login(data,is_email=True)
            else:
                user = await self.user_repository.get_user_for_login(data)

            if not user:
                return self.__get_service_response(AuthErrorCode.AU117.name, AuthErrorCode.AU117.value)


            hashed_password = user.get("hash_password")

            is_password_valid = self.__verfiy_password(password, hashed_password)

            if is_password_valid:
                role = user.get("role")
                cookie_expiry_time = self.__set_cookie_expiry_time_based_on_role(role)
                jwt_token = self.__generate_jwt_token({"user_id": user.get("user_id"),"role":role})
                return self.__get_service_response(
                    AuthErrorCode.AU118.name,
                    AuthErrorCode.AU118.value,
                    is_error=False,
                    data=None,return_data={"cookie_expiry_time": cookie_expiry_time,"jwt_token":jwt_token})
            else:
                return self.__get_service_response(AuthErrorCode.AU119.name, AuthErrorCode.AU119.value)
        except asyncpg.exceptions.PostgresError as e:
            logging.info(str(e))
            return self.__get_service_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value)

    def get_logout(self) -> dict:
        return self.__get_service_response(AuthErrorCode.AU120.name, AuthErrorCode.AU120.value)

    @staticmethod
    def get_decoded_jwt_token(token: str):
        try:
            payload = jwt.decode(
                token,
                os.getenv("SECRET_KEY"),
                algorithms=os.getenv("ALGORITHM"),
            )
            return AuthService.__get_service_response(AuthErrorCode.AU122.name, AuthErrorCode.AU122.value,is_error=False,data=None,return_data={"payload":payload})
        except jwt.exceptions.PyJWTError as e:
            return AuthService.__get_service_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value)
    def __data_is_email(self,data)->bool:
        if "@" in data:
            return True
        else:
            return False

    def __verfiy_password(self,password:str,hash_password:str)->bool:
        return bcrypt.checkpw(password.encode('utf-8'),hash_password.encode('utf-8'))

    def __set_cookie_expiry_time_based_on_role(self, role: str):
        expiry_hours = {
            Role.SUPER_ADMIN.value: 2,
            Role.ADMIN.value: 8,
            Role.EXECUTIVE.value: 12,
            Role.USER.value: 24,
        }

        hours = expiry_hours.get(role, 1)

        return datetime.now(timezone.utc) + timedelta(
            hours=hours
        )


    def __generate_jwt_token(self,payload:dict)->str:
        return jwt.encode(payload, algorithm=os.getenv("ALGORITHM"),key=os.getenv("SECRET_KEY"))
    @staticmethod
    def __get_service_response(code: str, message: str, is_error: bool = True, data=None,return_data:dict=None) -> dict:
        return {
            "is_error": is_error,
            "response": {"code": code, "message": message, "data": data},
            "return_data": return_data,
        }
    def __get_hashed_password(self, password: str) -> str:
        return (bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())).decode("utf-8")