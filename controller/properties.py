from typing import Optional
from fastapi import APIRouter, Request, Query, status
from starlette.responses import JSONResponse
from repository.property_repository import PropertyRepository
from service.property_service import PropertyService
from error_codes.property_error_code import PropertyErrorCode
from error_codes.auth_error_code import AuthErrorCode

properties_router = APIRouter(prefix="/v1/properties", tags=["properties"])


def _get_property_service(request: Request) -> PropertyService:
    db_connection = request.app.state.database_connection
    property_repo = PropertyRepository(db_connection)
    return PropertyService(property_repo)


@properties_router.get("")
@properties_router.get("/")
async def get_properties(
    request: Request,
    state: Optional[str] = Query(None, description="State name or state_id (comma-separated for multiple)"),
    city: Optional[str] = Query(None, description="City name or city_id (comma-separated for multiple)"),
    district: Optional[str] = Query(None, description="District name or district_id"),
    property_type: Optional[str] = Query(None, description="Property type e.g. Residential, Commercial"),
    property_typre: Optional[str] = Query(None, description="Alias for property_type typo"),
    property_sub_type: Optional[str] = Query(None, description="Property sub-type e.g. Apartment, Land"),
    property_possession_type: Optional[str] = Query(None, description="Possession type e.g. Physical, Symbolic"),
    locality: Optional[str] = Query(None, description="Locality text filter"),
    min_price: Optional[float] = Query(None, description="Minimum reserve price"),
    max_price: Optional[float] = Query(None, description="Maximum reserve price"),
    search: Optional[str] = Query(None, description="Global text search across address, locality, etc."),
    is_approved: Optional[bool] = Query(None, description="Filter by approval status"),
    liked: Optional[bool] = Query(None, description="If true, return only user's liked properties"),
    liked_only: Optional[bool] = Query(None, description="If true, return only user's liked properties"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)

    normalized_role = role.upper() if isinstance(role, str) else None
    if normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        is_approved = True

    service = _get_property_service(request)

    is_liked_filter = liked or liked_only

    if is_liked_filter and not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": "Authentication required to filter liked properties", "data": None}},
        )

    service_response = await service.get_properties_list(
        user_id=user_id,
        state=state,
        city=city,
        district=district,
        property_type=property_type,
        property_typre=property_typre,
        property_sub_type=property_sub_type,
        property_possession_type=property_possession_type,
        locality=locality,
        min_price=min_price,
        max_price=max_price,
        search=search,
        is_approved=is_approved,
        liked_only=is_liked_filter,
        page=page,
        limit=limit,
    )

    if service_response.get("is_error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"data": service_response.get("response")},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )


@properties_router.get("/liked")
async def get_liked_properties(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": AuthErrorCode.AU121.value, "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.get_liked_properties(user_id=user_id, page=page, limit=limit)

    if service_response.get("is_error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"data": service_response.get("response")},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )


@properties_router.get("/{property_id}")
async def get_property_by_id(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    service = _get_property_service(request)
    service_response = await service.get_property_detail(property_id=property_id, user_id=user_id)

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response", {}).get("code") == PropertyErrorCode.PR103.name:
            status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(
            status_code=status_code,
            content={"data": service_response.get("response")},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )


@properties_router.post("/{property_id}/like")
async def like_property(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": AuthErrorCode.AU121.value, "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.like_property(user_id=user_id, property_id=property_id)

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response", {}).get("code") == PropertyErrorCode.PR103.name:
            status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(
            status_code=status_code,
            content={"data": service_response.get("response")},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )


@properties_router.delete("/{property_id}/like")
async def unlike_property(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"data": {"code": AuthErrorCode.AU121.name, "message": AuthErrorCode.AU121.value, "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.unlike_property(user_id=user_id, property_id=property_id)

    if service_response.get("is_error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"data": service_response.get("response")},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )
