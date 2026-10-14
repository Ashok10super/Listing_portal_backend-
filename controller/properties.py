import json
from typing import Optional
from fastapi import APIRouter, Request, Query, status
from starlette.responses import JSONResponse
from data_validation.input_data_validator import property_input_validator,validate_identity_generator_input
from repository.property_repository import PropertyRepository
from repository.generated_identity_repository import GeneratedIdentityRepository
from repository.search_filter_repository import SearchFilterRepository
from service.property_service import PropertyService,SearchFiltersService
from service.genearted_identity_service import GeneratedIdentityService
from error_codes.property_error_code import PropertyErrorCode
from error_codes.auth_error_code import AuthErrorCode
from config import IdentityGenerationModules
import logging
logging.basicConfig(level=logging.INFO)

properties_router = APIRouter(tags=["properties"])


def _get_property_service(request: Request) -> PropertyService:
    db_connection = request.app.state.database_connection
    property_repo = PropertyRepository(db_connection)
    return PropertyService(property_repo)

def _get_search_filter_service(request:Request) ->SearchFiltersService:
    db_connection = request.app.state.database_connection
    search_filter_repo = SearchFilterRepository(db_connection)
    return SearchFiltersService(search_filter_repo)

def _get_generated_identity_service(request:Request)->GeneratedIdentityService:
    db_connection = request.app.state.database_connection
    generated_identity_repo = GeneratedIdentityRepository(db_connection)
    return GeneratedIdentityService(generated_identity_repo)

@properties_router.get("/v1/properties")
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

    # Check query param flags (presence in query_params handles both `?flag` and `?flag=true`)
    query_keys = set(request.query_params.keys())
    has_approved_properties = "approved_properties" in query_keys
    has_unapproved_properties = "unapproved_properties" in query_keys
    has_approved_by_me = "approved_by_me" in query_keys
    has_disapproved_by_me = "disapproved_by_me" in query_keys

    if has_approved_properties:
        # /properties?approved_properties -> this is for users view (only approved)
        is_approved = True
        approval_status = "approved"
        approved_by = None
        disapproved_by = None
    elif has_unapproved_properties:
        # /properties?unapproved_properties -> for admin & super_admin view: next 10 unapproved properties
        is_approved = False
        approval_status = "pending"
        approved_by = None
        disapproved_by = None
    elif has_approved_by_me:
        # /properties?approved_by_me -> all approved which is approved by caller's id
        is_approved = True
        approval_status = "approved"
        approved_by = user_id
        disapproved_by = None
    elif has_disapproved_by_me:
        # /properties?disapproved_by_me -> all disapproved which is disapproved by caller's id
        approval_status = "disapproved"
        disapproved_by = user_id
        approved_by = None
    elif normalized_role not in ("ADMIN", "SUPER_ADMIN"):
        # Normal users (or public unauthenticated users) can ONLY see approved properties
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
        elif tab == "all":
            # All properties (both approved and unapproved/disapproved)
            is_approved = None
            approval_status = None
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
        elif not tab or tab == "all":
            # Super Admin: /properties returns all properties (who approved/disapproved is included in each row)
            is_approved = None
            approval_status = None

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


@properties_router.get("/v1/properties/liked")
@properties_router.get("/properties/liked")
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


@properties_router.get("/v1/properties/metrics")
@properties_router.get("/properties/metrics")
@properties_router.get("/v1/properties/stats")
@properties_router.get("/properties/stats")
@properties_router.get("/v1/properties/summary")
@properties_router.get("/properties/summary")
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


@properties_router.get("/v1/properties/{property_id}")
@properties_router.get("/properties/{property_id}")
async def get_property_by_id(
    property_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> JSONResponse:
    query_keys = set(request.query_params.keys())
    has_approved_by_me = "approved_by_me" in query_keys
    has_disapproved_by_me = "disapproved_by_me" in query_keys

    # Support /properties/{owner_id}?approved_by_me and /properties/{owner_id}?disapproved_by_me
    # and /properties/owner_id?approved_by_me
    if has_approved_by_me or has_disapproved_by_me:
        auth_user_id = getattr(request.state, "user_id", None)
        if property_id.isdigit():
            target_owner_id = int(property_id)
        else:
            target_owner_id = auth_user_id

        service = _get_property_service(request)
        approval_status = "approved" if has_approved_by_me else "disapproved"
        approved_by = target_owner_id if has_approved_by_me else None
        disapproved_by = target_owner_id if has_disapproved_by_me else None

        service_response = await service.get_properties_list(
            user_id=target_owner_id,
            approval_status=approval_status,
            is_approved=True if has_approved_by_me else None,
            approved_by=approved_by,
            disapproved_by=disapproved_by,
            page=page,
            limit=limit,
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"data": service_response.get("response")})

    if not property_id.isdigit():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"data": {"code": PropertyErrorCode.PR103.name, "message": PropertyErrorCode.PR103.value, "data": None}},
        )

    numeric_property_id = int(property_id)
    user_id = getattr(request.state, "user_id", None)
    service = _get_property_service(request)
    service_response = await service.get_property_detail(property_id=numeric_property_id, user_id=user_id)

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


@properties_router.post("/v1/properties/{property_id}/approve")
@properties_router.post("/properties/{property_id}/approve")
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


@properties_router.post("/v1/properties/{property_id}/disapprove")
@properties_router.post("/properties/{property_id}/disapprove")
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


@properties_router.put("/v1/properties/{property_id}")
@properties_router.put("/properties/{property_id}")
@properties_router.patch("/v1/properties/{property_id}")
@properties_router.patch("/properties/{property_id}")
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


@properties_router.post("/v1/properties")
async def create_property(request: Request) -> JSONResponse :
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

        input_validation_response = property_input_validator(body,required_fields=["auction_id","auction_start_date","auction_end_date","emd_amount","reserve_price","auction_type","property_unique_id","property_id","state_id","district_id",
        "city_id","property_possession_type","property_type","property_sub_type","bank_id"])

        if input_validation_response.get("is_error"):
            return JSONResponse(status_code=input_validation_response.get("status_code"),content=input_validation_response.get("response"))

        property_service = _get_property_service(request)

        service_response = await property_service.create_property(property_data=input_validation_response.get("response").get("data"), user_id=user_id)

        if service_response.get("is_error"):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return JSONResponse(status_code=status_code,content=service_response.get("response"))

        #if the proprty is successfully created update the identities
        identity_service  = _get_generated_identity_service(request)
        update_response = await identity_service.update_generated_identity()

        if update_response.get("is_error"):
            logging.info("Unable to update the Identity")

        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"data": service_response.get("response")})

    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"data": {"code": "PR116", "message": "Invalid JSON body", "data": None}},
        )


@properties_router.post("/v1/properties/{property_id}/like")
@properties_router.post("/properties/{property_id}/like")
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


@properties_router.delete("/v1/properties/{property_id}/like")
@properties_router.delete("/properties/{property_id}/like")
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


@properties_router.get('/v1/properties/filter-lookup/{search_parameter}')
async def get_search_filter_lookup(request:Request, search_parameter:str,sub_search_parameter:int=None) -> JSONResponse:

    print("Im executing")

    filter_service = _get_search_filter_service(request)

    service_response =  await filter_service.get_search_filters(request=request,search_header=search_parameter,query_parameter=sub_search_parameter)

    if service_response.get("is_error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"data": service_response.get("response")},
        )
    print(service_response)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )

@properties_router.post('/v1/properties/generate-identity')
async def generate_identity(request: Request) -> JSONResponse:

    body = await request.body()

    input_validation = validate_identity_generator_input(body=body,required_fields=[IdentityGenerationModules.property_id.value, IdentityGenerationModules.property_unique_id.value,IdentityGenerationModules.auction_id.value])

    if input_validation.get("is_error"):
        return JSONResponse(status_code=input_validation.get("status_code"),content=input_validation.get("response"))

    service_object = _get_generated_identity_service(request)

    service_response = await service_object.get_available_id_by_name(input_body=input_validation.get("response").get("data"))


    if service_response.get("is_error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"data": service_response.get("response")},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": service_response.get("response")},
    )













