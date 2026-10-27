import asyncpg



class MediaRepository:
    def __init__(self,database_connection:asyncpg.Connection):
        self.__database_connection = database_connection

    async def insert_media_path(self,property_id:int,media_url:str):
        query = """
               INSERT INTO property_media_link (property_id, media_url)
               VALUES ($1, $2)
               RETURNING *
           """

        inserted_row = await self.__database_connection.fetchrow(
            query,
            property_id,
            media_url
        )

        return {
            "message": "Media path successfully added",
            "data": dict(inserted_row) if inserted_row else None
        }
