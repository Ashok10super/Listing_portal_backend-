import asyncpg
from config import IdentityGenerationModules

class GeneratedIdentityRepository:
    def __init__(self, database_connection: asyncpg.Connection):
        self.database_connection = database_connection

    async def fetch_generated_id_by_name(self,id_name) -> dict:

        query = f"""SELECT {id_name} FROM generated_module_identity"""

        id = await self.database_connection.fetchval(query)

        return {id_name:id}

    async def fetch_all_generated_id(self) -> dict:

        query = "SELECT * FROM generated_module_identity"

        id = await self.database_connection.fetchrow(query)

        return dict(id)


    async def update_generated_id_by_name(self,id_name,value) -> dict:
        if id_name != IdentityGenerationModules.property_unique_id.name:
            query = f"""UPDATE generated_module_identity SET {id_name} = {id_name + 1} RETURNING *"""

        else:

            query = f"""UPDATE generated_module_identity SET {id_name} = {value} RETURNING *"""

        updated_row = await self.database_connection.fetchrow(query)

        return dict(updated_row) if updated_row else {}

    async def bulk_update_generated_identity(self, unique_property_id) -> dict:
            query = f"""
                UPDATE generated_module_identity
                SET
                    {IdentityGenerationModules.property_id.value} =
                        {IdentityGenerationModules.property_id.value} + 1,
                    {IdentityGenerationModules.auction_id.value} =
                        {IdentityGenerationModules.auction_id.value} + 1,
                    {IdentityGenerationModules.property_unique_id.value} = $1
                RETURNING *
            """

            updated_rows = await self.database_connection.fetchrow(query, unique_property_id)

            return {
                "updated_rows":dict(updated_rows),
                "count": len(updated_rows),
            }


