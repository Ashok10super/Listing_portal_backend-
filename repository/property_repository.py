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
        approved_by: Optional[int] = None,
        disapproved_by: Optional[int] = None,
        approval_status: Optional[str] = None,
        created_by: Optional[int] = None,
        liked_only: Optional[bool] = False,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_conditions = []
        where_params = []
        param_idx = 1

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

        if approved_by is not None:
            where_conditions.append(f"p.approved_by = ${param_idx}")
            where_params.append(approved_by)
            param_idx += 1

        if disapproved_by is not None:
            where_conditions.append(f"p.disapproved_by = ${param_idx}")
            where_params.append(disapproved_by)
            param_idx += 1

        if approval_status is not None:
            where_conditions.append(f"p.approval_status = ${param_idx}")
            where_params.append(approval_status)
            param_idx += 1

        if created_by is not None:
            where_conditions.append(f"p.created_by = ${param_idx}")
            where_params.append(created_by)
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
            LEFT JOIN "user" u_creator ON p.created_by = u_creator.user_id
            LEFT JOIN "user" u_approver ON p.approved_by = u_approver.user_id
            LEFT JOIN "user" u_disapprover ON p.disapproved_by = u_disapprover.user_id
            {where_clause}
        """

        total_count = await self.database_connection.fetchval(count_query, *where_params)

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
                p.approved_at,
                p.disapproved_by,
                p.listed_date,
                p.property_fetch_date,
                p.property_status,
                p.approval_status,
                p.created_by,
                p.modified_by,
                p.created_at,
                p.updated_at,
                u_creator.user_name AS creator_name,
                u_creator.email AS creator_email,
                u_approver.user_name AS approver_name,
                u_approver.email AS approver_email,
                u_disapprover.user_name AS disapprover_name,
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
            LEFT JOIN "user" u_creator ON p.created_by = u_creator.user_id
            LEFT JOIN "user" u_approver ON p.approved_by = u_approver.user_id
            LEFT JOIN "user" u_disapprover ON p.disapproved_by = u_disapprover.user_id
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
                p.approved_at,
                p.disapproved_by,
                p.listed_date,
                p.property_fetch_date,
                p.property_status,
                p.approval_status,
                p.created_by,
                p.modified_by,
                p.created_at,
                p.updated_at,
                u_creator.user_name AS creator_name,
                u_creator.email AS creator_email,
                u_approver.user_name AS approver_name,
                u_approver.email AS approver_email,
                u_disapprover.user_name AS disapprover_name,
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
            LEFT JOIN "user" u_creator ON p.created_by = u_creator.user_id
            LEFT JOIN "user" u_approver ON p.approved_by = u_approver.user_id
            LEFT JOIN "user" u_disapprover ON p.disapproved_by = u_disapprover.user_id
            WHERE p.property_id = $1
            LIMIT 1
        """

        row = await self.database_connection.fetchrow(query, *params)
        return _serialize_row(dict(row)) if row else None

    async def approve_property(self, property_id: int, admin_id: int) -> Optional[Dict[str, Any]]:
        query = """
            UPDATE properties
            SET
                is_approved = TRUE,
                approval_status = 'approved',
                approved_by = $1,
                approved_at = CURRENT_TIMESTAMP,
                modified_by = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE property_id = $2
            RETURNING property_id
        """
        res = await self.database_connection.fetchval(query, admin_id, property_id)
        if not res:
            return None
        return await self.get_property_by_id(property_id, user_id=admin_id)

    async def disapprove_property(self, property_id: int, admin_id: int, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = """
            UPDATE properties
            SET
                is_approved = FALSE,
                approval_status = 'disapproved',
                disapproved_by = $1,
                approved_by = $1,
                modified_by = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE property_id = $2
            RETURNING property_id
        """
        res = await self.database_connection.fetchval(query, admin_id, property_id)
        if not res:
            return None
        return await self.get_property_by_id(property_id, user_id=admin_id)

    async def update_property(self, property_id: int, update_data: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
        existing = await self.get_property_by_id(property_id)
        if not existing:
            return None

        prop_fields = []
        prop_params = []
        p_idx = 1

        field_mapping = {
            "locality": "locality",
            "property_address": "property_address",
            "address": "property_address",
            "property_type": "property_type",
            "type": "property_type",
            "property_sub_type": "property_sub_type",
            "property_possession_type": "property_possession_type",
            "possessionStatus": "property_possession_type",
            "property_pincode": "property_pincode",
            "pincode": "property_pincode",
        }

        for key, col in field_mapping.items():
            if key in update_data and update_data[key] is not None:
                prop_fields.append(f"{col} = ${p_idx}")
                prop_params.append(str(update_data[key]))
                p_idx += 1

        if "areaSqFt" in update_data or "property_carpet_area_sqft" in update_data:
            val = float(update_data.get("areaSqFt") or update_data.get("property_carpet_area_sqft") or 1200)
            prop_fields.append(f"property_carpet_area_sqft = ${p_idx}")
            prop_params.append(val)
            p_idx += 1
            prop_fields.append(f"property_build_up_area_sqft = ${p_idx}")
            prop_params.append(val)
            p_idx += 1

        prop_fields.append(f"modified_by = ${p_idx}")
        prop_params.append(user_id)
        p_idx += 1

        prop_fields.append("updated_at = CURRENT_TIMESTAMP")

        prop_params.append(property_id)
        prop_update_query = f"UPDATE properties SET {', '.join(prop_fields)} WHERE property_id = ${p_idx}"
        await self.database_connection.execute(prop_update_query, *prop_params)

        # Update auction_details if auction fields provided
        auction_fields = []
        auction_params = []
        a_idx = 1
        if "reservePrice" in update_data or "reserve_price" in update_data:
            rp = int(update_data.get("reservePrice") or update_data.get("reserve_price"))
            auction_fields.append(f"reserve_price = ${a_idx}")
            auction_params.append(rp)
            a_idx += 1
        if "emdAmount" in update_data or "emd_amount" in update_data:
            emd = float(update_data.get("emdAmount") or update_data.get("emd_amount"))
            auction_fields.append(f"emd_amount = ${a_idx}")
            auction_params.append(emd)
            a_idx += 1

        if auction_fields and existing.get("auction_id"):
            auction_params.append(existing["auction_id"])
            auction_update_query = f"UPDATE auction_details SET {', '.join(auction_fields)} WHERE auction_id = ${a_idx}"
            await self.database_connection.execute(auction_update_query, *auction_params)

        return await self.get_property_by_id(property_id, user_id=user_id)

    async def create_property(self, property_data: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
        # 1. Insert auction_details record
        auction_query = """
            INSERT INTO auction_details (
                auction_start_date, auction_end_date, auction_verified_on,
                auction_branch, checker_name, checker_designation,
                emd_amount, emd_start_date, emd_end_date,
                reserve_price, increment_price, inspector_name,
                inspector_mobile_no, inspector_branch, auction_type
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            ) RETURNING auction_id
        """
        auction_id = await self.database_connection.fetchval(
            auction_query,
            datetime.now(),
            datetime.now(),
            datetime.now(),
            property_data.get("branch") or "Main Branch",
            property_data.get("authorizedOfficer") or "Authorized Officer",
            "Chief Manager",
            float(property_data.get("emdAmount") or 250000),
            datetime.now(),
            datetime.now(),
            int(property_data.get("reservePrice") or 2500000),
            int(property_data.get("increment_price") or 50000),
            property_data.get("authorizedOfficer") or "Authorized Officer",
            property_data.get("contactNumber") or "9876543210",
            property_data.get("branch") or "Main Branch",
            "E-Auction"
        )

        # 2. Insert into properties
        prop_query = """
            INSERT INTO properties (
                auction_id, bank_id, property_unique_id, property_pincode,
                state_id, district_id, city_id, locality, property_address,
                property_possession_type, property_type, property_sub_type,
                property_carpet_area_sqft, property_build_up_area_sqft,
                is_approved, approval_status, created_by, modified_by,
                created_at, updated_at
            ) VALUES (
                $1, NULL, $2, $3, 31, 577, 2458, $4, $5, $6, $7, $8, $9, $10,
                FALSE, 'pending', $11, $11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) RETURNING property_id
        """
        unique_id = property_data.get("lotNumber") or f"LOT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        prop_id = await self.database_connection.fetchval(
            prop_query,
            auction_id,
            unique_id,
            property_data.get("pincode") or "600001",
            property_data.get("locality") or property_data.get("city") or "Prime Area",
            property_data.get("address") or property_data.get("title") or "Property Address",
            property_data.get("possessionStatus") or "Physical Possession",
            property_data.get("type") or "Residential",
            property_data.get("sub_type") or "Flat",
            float(property_data.get("areaSqFt") or 1200),
            float(property_data.get("areaSqFt") or 1200),
            user_id
        )

        # 3. Add bank_details
        if property_data.get("bank"):
            bank_query = """
                INSERT INTO bank_details (
                    property_id, bank_name, branch_name, borrower_name,
                    borrower_address, is_loan_available, percentage_of_loan,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, TRUE, '80%', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """
            await self.database_connection.execute(
                bank_query,
                prop_id,
                property_data.get("bank"),
                property_data.get("branch") or "Main Branch",
                "Borrower Entity",
                property_data.get("address") or ""
            )

        # 4. Add image URL if given
        if property_data.get("imageUrl"):
            media_query = """
                INSERT INTO property_media_link (property_id, media_url)
                VALUES ($1, $2)
            """
            await self.database_connection.execute(media_query, prop_id, property_data.get("imageUrl"))

        return await self.get_property_by_id(prop_id, user_id=user_id)

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

    async def get_property_metrics(self, admin_user_id: Optional[int] = None) -> Dict[str, Any]:
        prop_query = """
            SELECT 
                COUNT(*)::int as total,
                COUNT(*) FILTER (WHERE is_approved = false AND (approval_status = 'pending' OR approval_status IS NULL))::int as pending,
                COUNT(*) FILTER (WHERE is_approved = true OR approval_status = 'approved')::int as approved,
                COUNT(*) FILTER (WHERE approval_status = 'disapproved')::int as disapproved
            FROM properties
        """
        prop_stats = await self.database_connection.fetchrow(prop_query)
        total = prop_stats["total"] or 0
        pending = prop_stats["pending"] or 0
        approved = prop_stats["approved"] or 0
        disapproved = prop_stats["disapproved"] or 0

        user_query = """
            SELECT
                COUNT(*) FILTER (WHERE r.role IN ('ADMIN', 'SUPER_ADMIN'))::int as active_admins,
                COUNT(*) FILTER (WHERE r.role = 'USER')::int as registered_users
            FROM "user" u
            INNER JOIN role r ON u.role_id = r.role_id
        """
        user_stats = await self.database_connection.fetchrow(user_query)
        active_admins = user_stats["active_admins"] or 0
        registered_users = user_stats["registered_users"] or 0

        my_approved = 0
        my_disapproved = 0
        if admin_user_id is not None:
            my_query = """
                SELECT
                    COUNT(*) FILTER (WHERE (is_approved = true OR approval_status = 'approved') AND approved_by = $1)::int as my_approved,
                    COUNT(*) FILTER (WHERE approval_status = 'disapproved' AND disapproved_by = $1)::int as my_disapproved
                FROM properties
            """
            my_stats = await self.database_connection.fetchrow(my_query, admin_user_id)
            if my_stats:
                my_approved = my_stats["my_approved"] or 0
                my_disapproved = my_stats["my_disapproved"] or 0

        summary_list = [
            {
                "key": "pending",
                "label": "Pending Approval",
                "value": pending,
                "subtext": "Requires Audit",
                "badge_color": "amber",
            },
            {
                "key": "approved",
                "label": "Approved",
                "value": approved,
                "subtext": "Public Bidding Live",
                "badge_color": "emerald",
            },
            {
                "key": "disapproved",
                "label": "Disapproved",
                "value": disapproved,
                "subtext": "Flagged / Rejected",
                "badge_color": "red",
            },
            {
                "key": "total",
                "label": "Total Properties",
                "value": total,
                "subtext": "System Inventory",
                "badge_color": "sky",
            },
            {
                "key": "admins",
                "label": "Active Admins",
                "value": active_admins,
                "subtext": "Verification Officers",
                "badge_color": "purple",
            },
            {
                "key": "users",
                "label": "Registered Users",
                "value": registered_users,
                "subtext": "Verified Buyers",
                "badge_color": "indigo",
            },
        ]

        return {
            "total_properties": total,
            "pending_approval": pending,
            "approved": approved,
            "disapproved": disapproved,
            "active_admins": active_admins,
            "registered_users": registered_users,
            "my_approved": my_approved,
            "my_disapproved": my_disapproved,
            "summary_list": summary_list,
        }

