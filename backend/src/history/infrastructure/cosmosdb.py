

class CosmosdbHistoryRepository(HistoryRepository):
    def __init__(self, client: CosmosClient, database_id: str, container_id: str):
        self.client = client
        self.database_id = database_id
        self.container_id = container_id

    def get(self, user_id: str) -> List[History]:
        query = f"SELECT * FROM c WHERE c.userId = '{user_id}'"
        container = self.client.get_database_client(self.database_id).get_container_client(self.container_id)
        items = container.query_items(query, enable_cross_partition_query=True)
        return [History(**item) for item in items]

    def add(self, history: History):
        container = self.client.get_database_client(self.database_id).get_container_client(self.container_id)
        container.create_item(history.dict())