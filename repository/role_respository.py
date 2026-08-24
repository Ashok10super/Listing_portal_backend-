import asyncpg


class RoleRepository:
    def __init__(self,database_connection: asyncpg.Connection):
        self.database_connection = database_connection

    async def get_role_id_by_role(self,role:str) -> dict:
        query = """SELECT role_id FROM "role" where role = $1 """

        role_id = await self.database_connection.fetchval(query, role)

        return role_id if role_id else None
