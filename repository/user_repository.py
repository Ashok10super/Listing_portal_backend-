from datetime import datetime
import asyncpg


class UserRepository:
    def __init__(self, database_connection: asyncpg.Pool):
        self.database_connection = database_connection

    async def create_user(self,username: str, email: str,phone:str, auth_id:str,role_id:int,) -> dict:
        query = """
            INSERT INTO "user" (user_name,email,phone,role_id,auth_id,created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING user_id, user_name, email, role_id
        """
        user = await self.database_connection.fetchrow(query, username, email, phone, role_id, auth_id, datetime.now())

        return dict(user)

    async def get_user_by_email(self, email: str) -> dict | None:
        query = """
            SELECT user_id, user_name, email, role_id, auth_id
            FROM "user"
            WHERE email = $1
            LIMIT 1
        """
        user = await self.database_connection.fetchrow(query, email)
        return dict(user) if user else None

    async def get_user_by_username(self, username: str) -> dict | None:
        query = """
            SELECT user_id, user_name, email, role_id
            FROM "user"
            WHERE user_name = $1
            LIMIT 1
        """
        user = await self.database_connection.fetchrow(query, username)
        return dict(user) if user else None

    async def get_user_by_id(self, user_id: int) -> dict | None:
        query = """
            SELECT user_id, user_name, email, role
            FROM user
            WHERE user_id = $1
            LIMIT 1
        """
        user = await self.database_connection.fetchrow(query, user_id)
        return dict(user) if user else None

    async def update_password(self, user_id: int, password: str) -> dict | None:
        query = """
            UPDATE user
            SET password = $1
            WHERE id = $2
            RETURNING id, user_name, email, role_id
        """
        user = await self.database_connection.fetchrow(query, password, user_id)
        return dict(user) if user else None

    async def delete_user(self, user_id: int) -> str:
        query = "DELETE FROM user WHERE id = $1"
        return await self.database_connection.execute(query, user_id)


