import math
import logging
import asyncpg
from typing import Optional, Dict, Any
from error_codes.property_error_code import PropertyErrorCode
from repository.property_repository import PropertyRepository


class PropertyService:
    def __init__(self, property_repository: PropertyRepository):
        self.property_repository = property_repository

    async def get_properties_list(
        self,
        user_id: Optional[int] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        property_type: Optional[str] = None,
        property_typre: Optional[str] = None,  # Handle query typo parameter alias
        property_sub_type: Optional[str] = None,
        property_possession_type: Optional[str] = None,
        locality: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        is_approved: Optional[bool] = None,
        liked_only: Optional[bool] = False,
        page: int = 1,
        limit: int = 10,
    ) -> Dict[str, Any]:
        try:
            effective_property_type = property_type or property_typre

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 10

            properties, total_count = await self.property_repository.get_properties(
                user_id=user_id,
                state=state,
                city=city,
                district=district,
                property_type=effective_property_type,
                property_sub_type=property_sub_type,
                property_possession_type=property_possession_type,
                locality=locality,
                min_price=min_price,
                max_price=max_price,
                search=search,
                is_approved=is_approved,
                liked_only=liked_only,
                page=page,
                limit=limit,
            )

            total_pages = math.ceil(total_count / limit) if limit > 0 else 1

            result_data = {
                "properties": properties,
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            }

            return self.__get_service_response(
                code=PropertyErrorCode.PR101.name,
                message=PropertyErrorCode.PR101.value,
                is_error=False,
                data=result_data,
            )
        except asyncpg.exceptions.PostgresError as e:
            logging.error(f"Postgres error in get_properties_list: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )
        except Exception as e:
            logging.error(f"Unexpected error in get_properties_list: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    async def get_property_detail(self, property_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            property_data = await self.property_repository.get_property_by_id(
                property_id=property_id, user_id=user_id
            )
            if not property_data:
                return self.__get_service_response(
                    code=PropertyErrorCode.PR103.name,
                    message=PropertyErrorCode.PR103.value,
                )

            return self.__get_service_response(
                code=PropertyErrorCode.PR102.name,
                message=PropertyErrorCode.PR102.value,
                is_error=False,
                data=property_data,
            )
        except asyncpg.exceptions.PostgresError as e:
            logging.error(f"Postgres error in get_property_detail: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    async def like_property(self, user_id: int, property_id: int) -> Dict[str, Any]:
        try:
            property_data = await self.property_repository.get_property_by_id(property_id=property_id)
            if not property_data:
                return self.__get_service_response(
                    code=PropertyErrorCode.PR103.name,
                    message=PropertyErrorCode.PR103.value,
                )

            success = await self.property_repository.like_property(user_id=user_id, property_id=property_id)
            return self.__get_service_response(
                code=PropertyErrorCode.PR104.name,
                message=PropertyErrorCode.PR104.value,
                is_error=False,
                data={"property_id": property_id, "is_liked": True},
            )
        except asyncpg.exceptions.PostgresError as e:
            logging.error(f"Postgres error in like_property: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    async def unlike_property(self, user_id: int, property_id: int) -> Dict[str, Any]:
        try:
            await self.property_repository.unlike_property(user_id=user_id, property_id=property_id)
            return self.__get_service_response(
                code=PropertyErrorCode.PR105.name,
                message=PropertyErrorCode.PR105.value,
                is_error=False,
                data={"property_id": property_id, "is_liked": False},
            )
        except asyncpg.exceptions.PostgresError as e:
            logging.error(f"Postgres error in unlike_property: {e}")
            return self.__get_service_response(
                code=PropertyErrorCode.PR109.name,
                message=PropertyErrorCode.PR109.value,
            )

    async def get_liked_properties(self, user_id: int, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        try:
            res = await self.get_properties_list(
                user_id=user_id, liked_only=True, page=page, limit=limit
            )
            if res.get("is_error"):
                return res
            
            # Override response code and message for liked properties endpoint
            res["response"]["code"] = PropertyErrorCode.PR110.name
            res["response"]["message"] = PropertyErrorCode.PR110.value
            return res
        except Exception as e:
            logging.error(f"Unexpected error in get_liked_properties: {e}")
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
