import pytest
import pytest_asyncio
import httpx
from main import app
from database import PostgresDatabase
from service.auth_service import AuthService


@pytest_asyncio.fixture(autouse=True)
async def setup_test_app():
    db = PostgresDatabase()
    connection = await db.get_database_connection()
    app.state.database_connection = connection
    yield


@pytest.mark.asyncio
async def test_public_user_sees_only_approved_properties():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Public visitor without token
        response = await client.get("/v1/properties")
        assert response.status_code == 200
        data = response.json()["data"]["data"]
        for prop in data["properties"]:
            assert prop["is_approved"] is True
            assert prop["approval_status"] in ("approved", None)


@pytest.mark.asyncio
async def test_admin_unapproved_queue_and_my_approved_flow():
    # Admin kyisa (user_id = 9, role = ADMIN)
    admin_token = AuthService._AuthService__generate_jwt_token(
        AuthService(None, None, None), {"user_id": 9, "role": "ADMIN"}
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers) as client:
        # 1. Admin can view unapproved properties queue
        unapproved_res = await client.get("/v1/properties?tab=unapproved")
        assert unapproved_res.status_code == 200
        unapproved_data = unapproved_res.json()["data"]["data"]
        assert "properties" in unapproved_data
        for p in unapproved_data["properties"]:
            assert p["is_approved"] is False

        # 2. If there's an unapproved property, admin can approve it
        if len(unapproved_data["properties"]) > 0:
            target_prop = unapproved_data["properties"][0]
            prop_id = target_prop["property_id"]

            approve_res = await client.post(f"/v1/properties/{prop_id}/approve")
            assert approve_res.status_code == 200
            assert approve_res.json()["data"]["code"] == "PR111"
            approved_prop = approve_res.json()["data"]["data"]
            assert approved_prop["is_approved"] is True
            assert approved_prop["approved_by"] == 9

            # 3. Admin checks "My Approved" tab -> must contain this property
            my_approved_res = await client.get("/v1/properties?tab=my_approved")
            assert my_approved_res.status_code == 200
            my_approved_props = my_approved_res.json()["data"]["data"]["properties"]
            my_ids = [p["property_id"] for p in my_approved_props]
            assert prop_id in my_ids
            for p in my_approved_props:
                assert p["approved_by"] == 9

            # 4. Admin checks "Users View" tab -> must see this property and all approved
            users_view_res = await client.get("/v1/properties?tab=users_view")
            assert users_view_res.status_code == 200
            users_view_props = users_view_res.json()["data"]["data"]["properties"]
            users_view_ids = [p["property_id"] for p in users_view_props]
            assert prop_id in users_view_ids


@pytest.mark.asyncio
async def test_superadmin_global_access_and_users_directory():
    # Superadmin ashok (user_id = 1, role = SUPER_ADMIN)
    super_token = AuthService._AuthService__generate_jwt_token(
        AuthService(None, None, None), {"user_id": 1, "role": "SUPER_ADMIN"}
    )
    headers = {"Authorization": f"Bearer {super_token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers) as client:
        # 1. Superadmin can view users directory
        users_res = await client.get("/v1/auth/users")
        assert users_res.status_code == 200
        users_data = users_res.json()["data"]["data"]
        assert isinstance(users_data, list)
        assert len(users_data) > 0
        roles_found = [u["role"] for u in users_data]
        assert "SUPER_ADMIN" in roles_found

        # 2. Superadmin views all properties
        props_res = await client.get("/v1/properties?limit=5")
        assert props_res.status_code == 200
        props = props_res.json()["data"]["data"]["properties"]
        assert len(props) > 0
        # Check audit fields exist
        assert "creator_name" in props[0]
        assert "approver_name" in props[0]


@pytest.mark.asyncio
async def test_register_role_restriction():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Public attempt to create an ADMIN must fail with 403
        payload = {
            "username": "unauthorized_admin",
            "email": "hacker@domain.com",
            "phone": "9999999999",
            "password": "%ncK7M98",
            "role": "ADMIN"
        }
        res = await client.post("/v1/auth/register", json=payload)
        assert res.status_code == 403
        assert res.json()["data"]["code"] == "AU121"


@pytest.mark.asyncio
async def test_property_metrics_api():
    # Admin kyisa (user_id = 9, role = ADMIN)
    admin_token = AuthService._AuthService__generate_jwt_token(
        AuthService(None, None, None), {"user_id": 9, "role": "ADMIN"}
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers) as client:
        res = await client.get("/v1/properties/metrics")
        assert res.status_code == 200
        data = res.json()["data"]["data"]
        assert "pending_approval" in data
        assert "approved" in data
        assert "disapproved" in data
        assert "total_properties" in data
        assert "active_admins" in data
        assert "registered_users" in data
        assert "summary_list" in data
        assert len(data["summary_list"]) >= 3

        # Check summary list items
        labels = [item["label"] for item in data["summary_list"]]
        assert "Pending Approval" in labels
        assert "Approved" in labels
        assert "Disapproved" in labels

        subtexts = [item["subtext"] for item in data["summary_list"]]
        assert "Requires Audit" in subtexts
        assert "Public Bidding Live" in subtexts
        assert "Flagged / Rejected" in subtexts

