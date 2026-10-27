import os
import uuid
from typing import Any, Optional, Dict
import dotenv
from fastapi import UploadFile, File
from starlette.concurrency import run_in_threadpool
from config import AllowedImageExtensions, MAX_FILE_SIZE
from error_codes.media_error_codes import MediaServiceErrorCode
from google_bucket_initiation import GoogleBucketStorage
from repository.media_repository import MediaRepository
dotenv.load_dotenv()
class MediaService:
    def __init__(self,media_repository: MediaRepository):
        self.media_repository = media_repository

    async def upload_image(self,property_id: int,file: UploadFile = File(...)):
        try:
            if not file:
                return self.__media_service_response(code=MediaServiceErrorCode.MS101.name,message=MediaServiceErrorCode.MS101.value,data=None)
            print(file.content_type)
            if file.content_type not in (AllowedImageExtensions.jpeg.value, AllowedImageExtensions.png.value ,AllowedImageExtensions.webp.value):
                return self.__media_service_response(code=MediaServiceErrorCode.MS102.name,message=MediaServiceErrorCode.MS102.value,data=None)
            max_bytes_size = MAX_FILE_SIZE
            if file.size > max_bytes_size:
                return self.__media_service_response(code=MediaServiceErrorCode.MS103.name,message=MediaServiceErrorCode.MS103.value,data=None)

            bucket_connection = GoogleBucketStorage.bucket_connection_object
            if bucket_connection is None:
                raise RuntimeError("Google Cloud Storage is not initialized")

            extension_by_type = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }
            contents = await file.read(MAX_FILE_SIZE + 1)

            extension = extension_by_type[file.content_type]
            generated_uuid = str(uuid.uuid4())
            object_name = f"property/{property_id}/{generated_uuid}.{extension}"
            blob = bucket_connection.blob(object_name)

            await run_in_threadpool(
                blob.upload_from_string,
                contents,
                content_type=file.content_type,
            )

            #save the object path to the database
            media_path = f"{os.getenv("DOMAIN")}/v1/media/{property_id}/{generated_uuid}.{extension}"
            await self.media_repository.insert_media_path(property_id=property_id,media_url=media_path)

            return self.__media_service_response(
                code=MediaServiceErrorCode.MS104.name,
                message=MediaServiceErrorCode.MS104.value,
                data={
                    "property_id": property_id,
                    "object_name": object_name,
                    "content_type": file.content_type,
                    "size": (len(contents)),
                }
            )

        except Exception as e:
            print(e)
            return self.__media_service_response(MediaServiceErrorCode.MS105.name,message=MediaServiceErrorCode.MS105.value,data=None)

    @staticmethod
    def __media_service_response(code: str, message: str, is_error: bool = True, data: Any = None, return_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        return {
            "is_error": is_error,
            "response": {"code": code, "message": message, "data": data},
            "return_data": return_data,
        }

    async def fetch_media(
            self,
            property_id: int,
            image_name: str,
    ):
        try:

            bucket_connection = GoogleBucketStorage.bucket_connection_object


            if bucket_connection is None:
                raise RuntimeError(
                    "Google Cloud Storage is not initialized"
                )

            # Construct the GCS object path
            object_name = f"property/{property_id}/{image_name}"
            blob = bucket_connection.blob(object_name)

            exists = await run_in_threadpool(blob.exists)

            if not exists:
                return self.__media_service_response(
                    code=MediaServiceErrorCode.MS106.name,
                    message=MediaServiceErrorCode.MS106.value,
                    data=None,
                )

            contents = await run_in_threadpool(
                blob.download_as_bytes
            )

            return self.__media_service_response(
                code=MediaServiceErrorCode.MS107.name,
                message=MediaServiceErrorCode.MS107.value,
                is_error=False,
                data=None,
                return_data={
                    "contents": contents,
                    "content_type": blob.content_type or "application/octet-stream",
                }
            )

        except Exception as e:
            print(f"Fetch media error: {e}")

            return self.__media_service_response(
                code=MediaServiceErrorCode.MS105.name,
                message=MediaServiceErrorCode.MS105.value,
                data=None,
            )