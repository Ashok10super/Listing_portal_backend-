import asyncpg
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple


import json

def _serialize_value(val: Any) -> Any:
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    return val


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    serialized = {}
    for k, v in row.items():
        if k in ("media_urls", "document_urls") and isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = []
        serialized[k] = _serialize_value(v)
    return serialized


class PropertyRepository:
    def __init__(self, database_connection: asyncpg.Pool):
        self.database_connection = database_connection

    async def get_properties(
        self,
        user_id: Optional[int] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        property_type: Optional[str] = None,
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
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_conditions = []
        where_params = []
        param_idx = 1

        # Calculate where_clause parameters starting at param_idx 1
        if liked_only:
            if user_id is None:
                return [], 0
            where_conditions.append(f"EXISTS (SELECT 1 FROM liked_properties lp WHERE lp.property_id = p.property_id AND lp.user_id = ${param_idx})")
            where_params.append(user_id)
            param_idx += 1

        if state:
            state_vals = [s.strip() for s in state.split(",") if s.strip()]
            if state_vals:
                if len(state_vals) == 1 and state_vals[0].isdigit():
                    where_conditions.append(f"p.state_id = ${param_idx}")
                    where_params.append(int(state_vals[0]))
                    param_idx += 1
                else:
                    state_conds = []
                    for s_val in state_vals:
                        state_conds.append(f"s.state ILIKE ${param_idx}")
                        where_params.append(f"%{s_val}%")
                        param_idx += 1
                    where_conditions.append(f"({' OR '.join(state_conds)})")

        if city:
            city_vals = [c.strip() for c in city.split(",") if c.strip()]
            if city_vals:
                if len(city_vals) == 1 and city_vals[0].isdigit():
                    where_conditions.append(f"p.city_id = ${param_idx}")
                    where_params.append(int(city_vals[0]))
                    param_idx += 1
                else:
                    city_conds = []
                    for c_val in city_vals:
                        city_conds.append(f"c.city ILIKE ${param_idx}")
                        where_params.append(f"%{c_val}%")
                        param_idx += 1
                    where_conditions.append(f"({' OR '.join(city_conds)})")

        if district:
            district_vals = [d.strip() for d in district.split(",") if d.strip()]
            if district_vals:
                if len(district_vals) == 1 and district_vals[0].isdigit():
                    where_conditions.append(f"p.district_id = ${param_idx}")
                    where_params.append(int(district_vals[0]))
                    param_idx += 1
                else:
                    dist_conds = []
                    for d_val in district_vals:
                        dist_conds.append(f"d.district ILIKE ${param_idx}")
                        where_params.append(f"%{d_val}%")
                        param_idx += 1
                    where_conditions.append(f"({' OR '.join(dist_conds)})")

        if property_type:
            types = [t.strip() for t in property_type.split(",") if t.strip()]
            if types:
                type_conds = []
                for t in types:
                    type_conds.append(f"p.property_type ILIKE ${param_idx}")
                    where_params.append(f"%{t}%")
                    param_idx += 1
                where_conditions.append(f"({' OR '.join(type_conds)})")

        if property_sub_type:
            sub_types = [st.strip() for st in property_sub_type.split(",") if st.strip()]
            if sub_types:
                sub_type_conds = []
                for st in sub_types:
                    sub_type_conds.append(f"p.property_sub_type ILIKE ${param_idx}")
                    where_params.append(f"%{st}%")
                    param_idx += 1
                where_conditions.append(f"({' OR '.join(sub_type_conds)})")

        if property_possession_type:
            where_conditions.append(f"p.property_possession_type ILIKE ${param_idx}")
            where_params.append(f"%{property_possession_type.strip()}%")
            param_idx += 1

        if locality:
            where_conditions.append(f"p.locality ILIKE ${param_idx}")
            where_params.append(f"%{locality.strip()}%")
            param_idx += 1

        if min_price is not None:
            where_conditions.append(f"ad.reserve_price >= ${param_idx}")
            where_params.append(min_price)
            param_idx += 1

        if max_price is not None:
            where_conditions.append(f"ad.reserve_price <= ${param_idx}")
            where_params.append(max_price)
            param_idx += 1

        if is_approved is not None:
            where_conditions.append(f"p.is_approved = ${param_idx}")
            where_params.append(is_approved)
            param_idx += 1

        if search:
            search_param = f"%{search.strip()}%"
            where_conditions.append(
                f"(p.property_address ILIKE ${param_idx} OR p.locality ILIKE ${param_idx} "
                f"OR p.property_unique_id ILIKE ${param_idx} OR s.state ILIKE ${param_idx} "
                f"OR c.city ILIKE ${param_idx})"
            )
            where_params.append(search_param)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        count_query = f"""
            SELECT COUNT(DISTINCT p.property_id)
            FROM properties p
            LEFT JOIN auction_details ad ON p.auction_id = ad.auction_id
            LEFT JOIN bank_details bd ON p.property_id = bd.property_id
            LEFT JOIN state s ON p.state_id = s.state_id
            LEFT JOIN district d ON p.district_id = d.district_id
            LEFT JOIN city c ON p.city_id = c.city_id
            {where_clause}
        """

        total_count = await self.database_connection.fetchval(count_query, *where_params)

        # Now build data query with is_liked_sql
        data_params = list(where_params)
        if user_id is not None:
            user_param_idx = param_idx
            param_idx += 1
            data_params.append(user_id)
            is_liked_sql = f"EXISTS (SELECT 1 FROM liked_properties lp WHERE lp.property_id = p.property_id AND lp.user_id = ${user_param_idx})"
        else:
            is_liked_sql = "FALSE"

        offset = (page - 1) * limit
        limit_param_idx = param_idx
        offset_param_idx = param_idx + 1
        data_params.extend([limit, offset])

        data_query = f"""
            SELECT
                p.property_id,
                p.auction_id,
                p.bank_id,
                p.property_unique_id,
                p.property_pincode,
                p.state_id,
                s.state AS state_name,
                p.district_id,
                d.district AS district_name,
                p.city_id,
                c.city AS city_name,
                p.locality,
                p.property_address,
                p.property_possession_type,
                p.property_type,
                p.property_sub_type,
                p.property_carpet_area_sqft,
                p.property_build_up_area_sqft,
                p.is_approved,
                p.approved_by,
                p.listed_date,
                p.property_fetch_date,
                p.property_status,
                p.approval_status,
                p.created_by,
                p.modified_by,
                p.created_at,
                p.updated_at,
                ad.auction_start_date,
                ad.auction_end_date,
                ad.auction_verified_on,
                ad.auction_branch,
                ad.checker_name,
                ad.checker_designation,
                ad.emd_amount,
                ad.emd_start_date,
                ad.emd_end_date,
                ad.reserve_price,
                ad.increment_price,
                ad.inspector_name,
                ad.inspector_mobile_no,
                ad.inspector_branch,
                ad.auction_type,
                bd.bank_name,
                bd.branch_name,
                bd.borrower_name,
                bd.borrower_address,
                bd.is_loan_available,
                bd.percentage_of_loan,
                COALESCE(
                    (SELECT json_agg(pml.media_url) FROM property_media_link pml WHERE pml.property_id = p.property_id),
                    '[]'::json
                ) AS media_urls,
                COALESCE(
                    (SELECT json_agg(adl.document_url) FROM auction_document_link adl WHERE adl.property_id = p.property_id),
                    '[]'::json
                ) AS document_urls,
                {is_liked_sql} AS is_liked
            FROM properties p
            LEFT JOIN auction_details ad ON p.auction_id = ad.auction_id
            LEFT JOIN bank_details bd ON p.property_id = bd.property_id
            LEFT JOIN state s ON p.state_id = s.state_id
            LEFT JOIN district d ON p.district_id = d.district_id
            LEFT JOIN city c ON p.city_id = c.city_id
            {where_clause}
            ORDER BY p.property_id DESC
            LIMIT ${limit_param_idx} OFFSET ${offset_param_idx}
        """

        rows = await self.database_connection.fetch(data_query, *data_params)

        properties = [_serialize_row(dict(row)) for row in rows]
        return properties, total_count or 0

    async def get_property_by_id(self, property_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        params = [property_id]
        if user_id is not None:
            params.append(user_id)
            is_liked_sql = f"EXISTS (SELECT 1 FROM liked_properties lp WHERE lp.property_id = p.property_id AND lp.user_id = $2)"
        else:
            is_liked_sql = "FALSE"

        query = f"""
            SELECT
                p.property_id,
                p.auction_id,
                p.bank_id,
                p.property_unique_id,
                p.property_pincode,
                p.state_id,
                s.state AS state_name,
                p.district_id,
                d.district AS district_name,
                p.city_id,
                c.city AS city_name,
                p.locality,
                p.property_address,
                p.property_possession_type,
                p.property_type,
                p.property_sub_type,
                p.property_carpet_area_sqft,
                p.property_build_up_area_sqft,
                p.is_approved,
                p.approved_by,
                p.listed_date,
                p.property_fetch_date,
                p.property_status,
                p.approval_status,
                p.created_by,
                p.modified_by,
                p.created_at,
                p.updated_at,
                ad.auction_start_date,
                ad.auction_end_date,
                ad.auction_verified_on,
                ad.auction_branch,
                ad.checker_name,
                ad.checker_designation,
                ad.emd_amount,
                ad.emd_start_date,
                ad.emd_end_date,
                ad.reserve_price,
                ad.increment_price,
                ad.inspector_name,
                ad.inspector_mobile_no,
                ad.inspector_branch,
                ad.auction_type,
                bd.bank_name,
                bd.branch_name,
                bd.borrower_name,
                bd.borrower_address,
                bd.is_loan_available,
                bd.percentage_of_loan,
                COALESCE(
                    (SELECT json_agg(pml.media_url) FROM property_media_link pml WHERE pml.property_id = p.property_id),
                    '[]'::json
                ) AS media_urls,
                COALESCE(
                    (SELECT json_agg(adl.document_url) FROM auction_document_link adl WHERE adl.property_id = p.property_id),
                    '[]'::json
                ) AS document_urls,
                {is_liked_sql} AS is_liked
            FROM properties p
            LEFT JOIN auction_details ad ON p.auction_id = ad.auction_id
            LEFT JOIN bank_details bd ON p.property_id = bd.property_id
            LEFT JOIN state s ON p.state_id = s.state_id
            LEFT JOIN district d ON p.district_id = d.district_id
            LEFT JOIN city c ON p.city_id = c.city_id
            WHERE p.property_id = $1
            LIMIT 1
        """

        row = await self.database_connection.fetchrow(query, *params)
        return _serialize_row(dict(row)) if row else None

    async def is_property_liked(self, user_id: int, property_id: int) -> bool:
        query = "SELECT 1 FROM liked_properties WHERE user_id = $1 AND property_id = $2 LIMIT 1"
        res = await self.database_connection.fetchval(query, user_id, property_id)
        return bool(res)

    async def like_property(self, user_id: int, property_id: int) -> bool:
        query = """
            INSERT INTO liked_properties (user_id, property_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, property_id) DO NOTHING
            RETURNING liked_id
        """
        res = await self.database_connection.fetchval(query, user_id, property_id)
        return bool(res)

    async def unlike_property(self, user_id: int, property_id: int) -> bool:
        query = "DELETE FROM liked_properties WHERE user_id = $1 AND property_id = $2 RETURNING liked_id"
        res = await self.database_connection.fetchval(query, user_id, property_id)
        return bool(res)
