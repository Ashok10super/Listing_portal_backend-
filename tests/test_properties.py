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
    await connection.execute("""
        CREATE TABLE IF NOT EXISTS liked_properties (
            liked_id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
            property_id INTEGER NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, property_id)
        );
    """)
    yield


@pytest.mark.asyncio
async def test_get_properties_list():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/properties")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["code"] == "PR101"
        assert "properties" in data["data"]
        assert "pagination" in data["data"]
        assert isinstance(data["data"]["properties"], list)


@pytest.mark.asyncio
async def test_get_properties_filtered():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Test state filter
        res_state = await client.get("/v1/properties?state=tamilnadu")
        assert res_state.status_code == 200
        data_state = res_state.json()["data"]["data"]
        assert "properties" in data_state

        # Test city filter
        res_city = await client.get("/v1/properties?city=Chennai")
        assert res_city.status_code == 200
        data_city = res_city.json()["data"]["data"]
        assert "properties" in data_city

        # Test property_type filter
        res_type = await client.get("/v1/properties?property_type=Residential")
        assert res_type.status_code == 200
        data_type = res_type.json()["data"]["data"]
        assert "properties" in data_type

        # Test property_typre typo alias filter
        res_typo = await client.get("/v1/properties?property_typre=Residential")
        assert res_typo.status_code == 200
        data_typo = res_typo.json()["data"]["data"]
        assert "properties" in data_typo


@pytest.mark.asyncio
async def test_get_property_detail():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        list_res = await client.get("/v1/properties?limit=1")
        assert list_res.status_code == 200
        props = list_res.json()["data"]["data"]["properties"]
        assert len(props) > 0
        prop_id = props[0]["property_id"]

        detail_res = await client.get(f"/v1/properties/{prop_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()["data"]["data"]
        assert detail_data["property_id"] == prop_id
        assert "media_urls" in detail_data
        assert "document_urls" in detail_data
        assert "is_liked" in detail_data


@pytest.mark.asyncio
async def test_like_and_unlike_property_flow():
    token = AuthService._AuthService__generate_jwt_token(AuthService(None, None, None), {"user_id": 1, "role": "USER"})
    cookies = {"access_token": token}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        # 1. Get a property ID
        list_res = await client.get("/v1/properties?limit=1")
        props = list_res.json()["data"]["data"]["properties"]
        prop_id = props[0]["property_id"]

        # 2. Like property
        like_res = await client.post(f"/v1/properties/{prop_id}/like")
        assert like_res.status_code == 200
        assert like_res.json()["data"]["code"] == "PR104"

        # 3. Check property detail reflects is_liked = True
        detail_res = await client.get(f"/v1/properties/{prop_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["data"]["data"]["is_liked"] is True

        # 4. Get liked properties list
        liked_res = await client.get("/v1/properties/liked")
        assert liked_res.status_code == 200
        liked_props = liked_res.json()["data"]["data"]["properties"]
        liked_ids = [p["property_id"] for p in liked_props]
        assert prop_id in liked_ids

        # 5. Unlike property
        unlike_res = await client.delete(f"/v1/properties/{prop_id}/like")
        assert unlike_res.status_code == 200
        assert unlike_res.json()["data"]["code"] == "PR105"

        # 6. Check property detail reflects is_liked = False
        detail_after = await client.get(f"/v1/properties/{prop_id}")
        assert detail_after.status_code == 200
        assert detail_after.json()["data"]["data"]["is_liked"] is False
