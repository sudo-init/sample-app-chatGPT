from logging import getLogger
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from azure.identity.aio import (
    DefaultAzureCredential,
    get_bearer_token_provider
)

from backend.src.settings import app_settings
from backend.src.utils.logger import get_main_logger_name


class CosmosDB:
    
    def __init__(
        self,
        cosmosdb_endpoint: str, 
        credential: any, 
        database_name: str, 
        container_name: str,  
    ):
        # self.logger = getLogger(f"{get_main_logger_name()}.cosmosdb.client")
        
        try:
            self.cosmosdb_client = CosmosClient(cosmosdb_endpoint, credential=credential)
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code == 401:
                raise ValueError("Invalid credentials") from e
            else:
                raise ValueError("Invalid CosmosDB endpoint") from e

        try:
            self.database_client = self.cosmosdb_client.get_database_client(database_name)
        except exceptions.CosmosResourceNotFoundError:
            raise ValueError("Invalid CosmosDB database name") 
        
        try:
            self.container_client = self.database_client.get_container_client(container_name)
        except exceptions.CosmosResourceNotFoundError:
            raise ValueError("Invalid CosmosDB container name") 
        

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