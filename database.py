import sys
import asyncpg
import os
import dotenv
import logging
dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

class PostgresDatabase:
    __database_connection : asyncpg.Pool|None = None

    async def get_database_connection(self)->asyncpg.Pool:
        try:
            if self.__database_connection is  None:
                conn : asyncpg.Pool =  await asyncpg.create_pool(
                    dsn=os.getenv("POSTGRES_URL"),
                    min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
                    max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "10")),
                )
                self.__database_connection = conn
            return self.__database_connection
        except asyncpg.exceptions.PostgresConnectionError as e:
            logging.info(e)
            sys.exit(1)

    async def close_database_connection(self)->dict:
        try:
            if self.__database_connection is not None:
                await self.__database_connection.close()
                self.__database_connection = None
                return {"is_success": True, "message": "Database Connection Closed","error": None}
            else:
                return {"is_success": False, "message": "No Active Connections Found","error": None}
        except asyncpg.exceptions.PostgresError as e:
            logging.info(str(e))
            return {"is_success": False, "message": "Error Raised while closing the database connection","error": e}


