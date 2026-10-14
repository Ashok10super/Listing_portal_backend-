from fastapi import APIRouter, File
from fastapi import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import

media_router = APIRouter(prefix="/v1/media",tags=["media"])


media_router.post("/upload-images/{property_id}")
async def create_media(request: Request,property_id: str,file:UploadFile = File(...))->JSONResponse:
    pass






