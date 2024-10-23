from backend.src.history.infrastructure.cosmosdb import CosmosDB


class AsyncCosmosDBClientFactory:
    """비동기 Context Manager 패턴을 사용하여 CosmosDB 클라이언트를 생성하는 팩토리 클래스"""
    
    def __init__(self, cosmosdb_endpoint: str, credential: any, database_name: str, container_name: str, enable_message_feedback: bool = False):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.enable_message_feedback = enable_message_feedback
    
    async def __aenter__(self):
        self.cosmosdb_client = CosmosDB(
            self.cosmosdb_endpoint,
            self.credential,
            self.database_name,
            self.container_name,
        )
        return self.cosmosdb_client

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.cosmosdb_client.close()