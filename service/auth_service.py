import asyncpg
import bcrypt
import logging
import dotenv
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

    async def get_login(self,data:str,password:str)->dict:
        try:
            user = None #holds the user data

            if self.__data_is_email(data):
                user = await self.user_repository.get_user_by_email(data)
            else:
                user = await self.user_repository.get_user_by_username(data)

            if not user:
                return self.__get_service_response(AuthErrorCode.AU117.name, AuthErrorCode.AU117.value)

            auth_id = user.get("auth_id")

            auth = await self.auth_repository.get_auth_by_auth_id(auth_id)

            hashed_password = auth.get("hash_password")

            is_password_valid = self.__verfiy_password(password, hashed_password)

            if is_password_valid:
                return self.__get_service_response(
                    AuthErrorCode.AU118.name,
                    AuthErrorCode.AU118.value,
                    is_error=False,
                    data=None)
            else:
                return self.__get_service_response(AuthErrorCode.AU119.name, AuthErrorCode.AU119.value)
        except asyncpg.exceptions.PostgresError as e:
            logging.info(str(e))
            return self.__get_service_response(AuthErrorCode.AU107.name, AuthErrorCode.AU107.value)


    def __data_is_email(self,data)->bool:
        if "@" in data:
            return True
        else:
            return False

    def __verfiy_password(self,password:str,hash_password:str)->bool:
        return bcrypt.checkpw(password.encode('utf-8'),hash_password.encode('utf-8'))



    def __get_service_response(self, code: str, message: str, is_error: bool = True, data=None) -> dict:
        return {
            "is_error": is_error,
            "response": {"code": code, "message": message, "data": data},
        }
    def __get_hashed_password(self, password: str) -> str:
        return (bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())).decode("utf-8")