import logging
import uuid
from typing import Dict, Any, Optional
from config import IdentityGenerationModules
from error_codes.property_error_code import PropertyErrorCode
from repository.generated_identity_repository import GeneratedIdentityRepository

class GeneratedIdentityService:
    def __init__(self, generate_identity_repo:GeneratedIdentityRepository):
        self.generate_identity_repo = generate_identity_repo

    async def get_all_available_id(self) -> Dict[str, Any]:
        try:
            property_id_dict = await self.generate_identity_repo.fetch_all_generated_id()

            for key, value in property_id_dict.items():
                   property_id_dict[key] = str(value)

            return self.__get_service_response(code=PropertyErrorCode.PR121.name,message=PropertyErrorCode.PR121.value,is_error=False,data=property_id_dict)

        except Exception as e:
            logging.error(f"Error in get_property_id service method: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    async def update_generated_identity(self) -> Dict[str, Any]:
        try:
            property_unique_id = str(uuid.uuid4())

            #update the id's
            update_response = await self.generate_identity_repo.bulk_update_generated_identity(unique_property_id=property_unique_id)
            print("identity update result",update_response)

            return self.__get_service_response(code=PropertyErrorCode.PR122.name,message=PropertyErrorCode.PR122.value,is_error=False,data=update_response)

        except Exception as e:

            logging.error(f"Error in get_property_id service method: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    @staticmethod
    def __get_service_response(
            code: str, message: str, is_error: bool = True, data: Any = None, return_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        return {
            "is_error": is_error,
            "response": {"code": code, "message": message, "data": data},
            "return_data": return_data,
        }