import json
from typing import Optional, Dict, Any
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
    is_approved: Optional[bool] = Query(None, description="Filter by approval status boolean"),
    tab: Optional[str] = Query(None, description="Active view tab: unapproved, my_approved, my_disapproved, users_view, all"),
    view: Optional[str] = Query(None, description="View alias: users_view / admin"),
    approved_by: Optional[int] = Query(None, description="Filter by approver user_id"),
    disapproved_by: Optional[int] = Query(None, description="Filter by disapprover user_id"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status: pending, approved, disapproved"),
    created_by: Optional[int] = Query(None, description="Filter by creator user_id"),
    liked: Optional[bool] = Query(None, description="If true, return only user's liked properties"),
    liked_only: Optional[bool] = Query(None, description="If true, return only user's liked properties"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    normalized_role = str(role).upper() if role else None

    # Normal users (or public unauthenticated users) can ONLY see approved properties
    if normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        is_approved = True
        approval_status = "approved"
        approved_by = None
        disapproved_by = None
    elif normalized_role == "ADMIN":
        # Admin logic: can see Users View (same as user has), Unapproved queue, or My Approved/Disapproved
        if view == "users_view" or tab in ("users_view", "approved", "all_approved"):
            # Admin previewing public users view: exact same view the user has (all approved properties)
            is_approved = True
            approval_status = "approved"
            approved_by = None
        elif tab == "my_approved":
            is_approved = True
            approval_status = "approved"
            approved_by = user_id  # strictly filtered by this admin's ID
        elif tab in ("my_disapproved", "disapproved"):
            approval_status = "disapproved"
            disapproved_by = user_id  # strictly filtered by this admin's ID
        elif tab in ("unapproved", "pending"):
            is_approved = False
            approval_status = "pending"
            approved_by = None
    elif normalized_role == "SUPER_ADMIN":
        # Super Admin can see everything, or filter by requested tab
        if tab in ("unapproved", "pending"):
            is_approved = False
            approval_status = "pending"
        elif tab in ("approved", "users_view"):
            is_approved = True
            approval_status = "approved"
        elif tab in ("disapproved",):
            approval_status = "disapproved"

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
        approved_by=approved_by,
        disapproved_by=disapproved_by,
        approval_status=approval_status,
        created_by=created_by,
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


@properties_router.get("/metrics")
@properties_router.get("/stats")
@properties_router.get("/summary")
async def get_property_metrics(request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    admin_user_id = user_id if str(role).upper() in ("ADMIN", "SUPER_ADMIN") else None

    service = _get_property_service(request)
    service_response = await service.get_property_metrics(admin_user_id=admin_user_id)

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


@properties_router.post("/{property_id}/approve")
async def approve_property(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    normalized_role = str(role).upper() if role else None

    if normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"data": {"code": PropertyErrorCode.PR115.name, "message": "Unauthorized: Only Admins can approve properties", "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.approve_property(property_id=property_id, admin_id=user_id)

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response", {}).get("code") == PropertyErrorCode.PR103.name:
            status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(status_code=status_code, content={"data": service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": service_response.get("response")})


@properties_router.post("/{property_id}/disapprove")
async def disapprove_property(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    normalized_role = str(role).upper() if role else None

    if normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"data": {"code": PropertyErrorCode.PR115.name, "message": "Unauthorized: Only Admins can disapprove properties", "data": None}},
        )

    reason = None
    try:
        body = await request.body()
        if body:
            parsed = json.loads(body)
            reason = parsed.get("reason")
    except Exception:
        reason = None

    service = _get_property_service(request)
    service_response = await service.disapprove_property(property_id=property_id, admin_id=user_id, reason=reason)

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response", {}).get("code") == PropertyErrorCode.PR103.name:
            status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(status_code=status_code, content={"data": service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": service_response.get("response")})


@properties_router.put("/{property_id}")
@properties_router.patch("/{property_id}")
async def update_property(property_id: int, request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    normalized_role = str(role).upper() if role else None

    if normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"data": {"code": PropertyErrorCode.PR115.name, "message": "Unauthorized: Only Admins can update properties", "data": None}},
        )

    try:
        body = await request.body()
        update_data = json.loads(body) if body else {}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"data": {"code": "PR116", "message": "Invalid JSON body", "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.update_property(property_id=property_id, update_data=update_data, user_id=user_id)

    if service_response.get("is_error"):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if service_response.get("response", {}).get("code") == PropertyErrorCode.PR103.name:
            status_code = status.HTTP_404_NOT_FOUND
        return JSONResponse(status_code=status_code, content={"data": service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": service_response.get("response")})


@properties_router.post("")
@properties_router.post("/")
async def create_property(request: Request) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)
    normalized_role = str(role).upper() if role else None

    if normalized_role not in ("ADMIN", "SUPER_ADMIN", "EXECUTIVE"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"data": {"code": PropertyErrorCode.PR115.name, "message": "Unauthorized to create property listings", "data": None}},
        )

    try:
        body = await request.body()
        property_data = json.loads(body) if body else {}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"data": {"code": "PR116", "message": "Invalid JSON body", "data": None}},
        )

    service = _get_property_service(request)
    service_response = await service.create_property(property_data=property_data, user_id=user_id)

    if service_response.get("is_error"):
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"data": service_response.get("response")})

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"data": service_response.get("response")})


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
