import uuid
from typing import Any, Optional, Dict

from fastapi import UploadFile, File
from google.cloud.storage import bucket
from starlette.concurrency import run_in_threadpool

from config import AllowedImageExtensions, MAX_FILE_SIZE
from error_codes.media_error_codes import MediaServiceErrorCode
from google_bucket_initiation import GoogleBucketStorage


class MediaService:
    # def __init__(self,Media_repository):
    #     self.Media_repository = Media_repository

    async def upload_image(self,property_id: str,file: UploadFile = File(...)):
        try:
            if not file:
                return self.__media_service_response(code=MediaServiceErrorCode.MS101.name,message=MediaServiceErrorCode.MS101.value,data=None)
            if file.content_type not in (AllowedImageExtensions.jpeg.value, AllowedImageExtensions.png.value ,AllowedImageExtensions.webp.value):
                return self.__media_service_response(code=MediaServiceErrorCode.MS102.name,message=MediaServiceErrorCode.MS102.value,data=None)
            max_bytes_size = MAX_FILE_SIZE
            if file.size > max_bytes_size:
                return self.__media_service_response(code=MediaServiceErrorCode.MS103.name,message=MediaServiceErrorCode.MS103.value,data=None)

            bucket_connection = GoogleBucketStorage.bucket_connection_object
            if bucket is None:
                raise RuntimeError("Google Cloud Storage is not initialized")

            extension_by_type = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }
            contents = await file.read(MAX_FILE_SIZE + 1)

            extension = extension_by_type[file.content_type]
            object_name = f"properties/{property_id}/{uuid.uuid4()}.{extension}"
            blob = bucket.blob(object_name)

            await run_in_threadpool(
                blob.upload_from_string,
                contents,
                content_type=file.content_type,
            )

            return self.__media_service_response(
                code="200",
                message="Image uploaded successfully",
                data={
                    "property_id": property_id,
                    "object_name": object_name,
                    "content_type": file.content_type,
                    "size": len(contents),
                }
            )







        except Exception as e:
            raise e

    @staticmethod
    def __media_service_response(code: str, message: str, is_error: bool = True, data: Any = None, return_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        return {
            "is_error": is_error,
            "response": {"code": code, "message": message, "data": data},
            "return_data": return_data,
        }
