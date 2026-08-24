import asyncpg


class AuthRepository:
    def __init__(self, database_connection: asyncpg.Connection):
        self.database_connection = database_connection

    async def create_auth_record(self,password: str) -> dict | None:
        query = """ insert into auth (hash_password,is_user_active)
        Values ($1, $2) returning auth_id"""
        auth = await self.database_connection.fetchrow(query, password, True)
        return dict(auth)

    async def get_auth_by_auth_id(self,user_id: int) -> dict | None:
        query = """ select * from auth where auth_id = $1 LIMIT 1"""
        auth = await self.database_connection.fetchrow(query, user_id)
        return dict(auth) if auth else None