import asyncpg

class SearchFilterRepository:
    def __init__(self, database_connection : asyncpg.Connection):
        self.database_connection = database_connection

    async def get_all_banks_filter(self)-> list | None:

        query = """select id,bank_name from banks"""

        banks = await self.database_connection.fetch(query)

        return self.__serialize__objects_to_dict(banks) if banks else None

    async def get_all_state_filter(self)-> dict | None :
        query = """select state_id,state from "state" """

        state = await self.database_connection.fetch(query)

        return dict(state) if state else None

    async def get_all_district_filter_by_state_id(self,state_id:int)-> list | None:

        query = f"""select * from district where state_id = {state_id}"""

        districts = await self.database_connection.fetch(query)

        print(districts)

        return self.__serialize__objects_to_dict(districts) if districts else None


    async def get_all_cities_filter_by_district(self,district_id:int)-> list | None:

        query = f"""select * from city where district_id = {district_id}"""

        cities = await self.database_connection.fetch(query)

        return self.__serialize__objects_to_dict(cities) if cities else None

    async def get_all_property_type_filter(self)-> list | None:
        query = """SELECT DISTINCT property_type FROM properties"""

        property_types = await self.database_connection.fetch(query)

        return self.__serialize__objects_to_dict(property_types) if property_types else None

    async def get_all_property_sub_type_filters(self)-> list | None:

        query = """select DISTINCT property_sub_type from properties;"""

        property_sub_types = await self.database_connection.fetch(query)

        return self.__serialize__objects_to_dict(property_sub_types) if property_sub_types else None

    async def get_emd_filter_value_range(self)-> dict | None:

        query = """SELECT MAX(emd_amount) AS highest_value, MIN(emd_amount) AS lowest_value FROM auction_details;"""

        emd_values = await self.database_connection.fetchrow(query)

        if emd_values is None:
            return None

        return {
            "highest_value": int(emd_values["highest_value"]),
            "lowest_value": int(emd_values["lowest_value"])
        }

    async def get_reserve_price_filter_value_range(self) -> dict | None:
        query = """SELECT MAX(reserve_price) AS highest_value, MIN(reserve_price) AS lowest_value FROM auction_details;"""

        reserve_price_values = await self.database_connection.fetchrow(query)

        if reserve_price_values is None:
            return None

        return {"highest_value": int(reserve_price_values["highest_value"]),"lowest_value": int(reserve_price_values["lowest_value"])}

    @staticmethod
    def __serialize__objects_to_dict(query_response:list)->list:
        return [dict(item) for item in query_response]
