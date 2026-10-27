from io import BytesIO

from fastapi import APIRouter, File
from fastapi import UploadFile
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse,StreamingResponse
from service.media_service import MediaService
from repository.media_repository import MediaRepository
from error_codes.media_error_codes import MediaServiceErrorCode

media_router = APIRouter(prefix="/v1/media")

def __get_media_service(request:Request) -> MediaService:
    db_connection = request.app.state.database_connection
    repository = MediaRepository(db_connection)
    media_service = MediaService(repository)
    return media_service


@media_router.post("/upload-images/{property_id}")
async def create_media(request: Request,property_id: int,image:UploadFile = File(...))->JSONResponse:

    service = __get_media_service(request)

    service_response = await service.upload_image(property_id,image)

    if service_response.get("is_error"):
        if service_response.get("response").get("code") == MediaServiceErrorCode.MS105.name:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,content=service_response.get("response"))
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content=service_response.get("response"))

    return JSONResponse(status_code=status.HTTP_201_CREATED,content=service_response.get("response"))


@media_router.get("/{property_id}/{image_name}")
async def get_media(request: Request,property_id: int,image_name: str):

    service = __get_media_service(request)

    service_response =  await service.fetch_media(property_id,image_name)

    if service_response.get("is_error"):
        if service_response.get("response").get("code") == MediaServiceErrorCode.MS105.name:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,content=service_response.get("response"))
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content=service_response.get("response"))

    image_data = service_response.get("return_data")

    return StreamingResponse(
        content=BytesIO(image_data["contents"]),
        media_type=image_data["content_type"],
    )









