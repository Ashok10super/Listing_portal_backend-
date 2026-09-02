from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from database import PostgresDatabase
from controller.auth import auth_router
from middleware.auth_middleware import auth_middleware
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def life_span(app: FastAPI):
    database_object = PostgresDatabase() #database object
    connection = await database_object.get_database_connection()
    print("Database connection established",connection)
    app.state.database_connection = connection
    yield
    await database_object.close_database_connection()

app = FastAPI(lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(auth_middleware)

#middleware registration

#Router registration
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000,reload=True)

