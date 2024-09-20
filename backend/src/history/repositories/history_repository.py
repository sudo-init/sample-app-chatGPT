import json
import uuid



from datetime import datetime
from logging import getLogger

from backend.src.history.infrastructure.async_cosmosdb_client_factory import AsyncCosmosDBClientFactory
from backend.src.history.infrastructure.cosmosdb import CosmosDB
from backend.src.utils.logger import get_main_logger_name


  
# class CosmosConversationClient():
class HistoryRepository:
    
    def __init__(
        self, 
        cosmosdb_endpoint: str, 
        # credential: any, 
        database_name: str, 
        container_name: str, 
        cosmosdb_factory: AsyncCosmosDBClientFactory,
        enable_message_feedback: bool = False,
    ):
        self.logger = getLogger(f"{get_main_logger_name()}.history.repository")
        # clients = self.init_cosmosdb_client(
        #                 cosmosdb_endpoint, 
        #                 credential, 
        #                 database_name, 
        #                 container_name, 
        #                 enable_message_feedback
        #             )
        # self.cosmosdb_client = clients[0]
        # self.database_client = clients[1]
        # self.container_client = clients[2]
        
        self.database_name = database_name
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.container_name = container_name
        self.enable_message_feedback = enable_message_feedback
        
        self.cosmosdb_factory = cosmosdb_factory
        
    
    # def init_cosmosdb_client(
    #     self,
    #     cosmosdb_endpoint: str,
    #     credential: any,
    #     database_name: str,
    #     container_name: str,
    # ) -> list:
        
    #     try:
    #         cosmosdb = CosmosDB(
    #                         cosmosdb_endpoint, 
    #                         credential, 
    #                         database_name, 
    #                         container_name, 
    #                     )
    #     except Exception as e:
    #             self.logger.exception("Exception in CosmosDB initialization", e)
    #             raise e

    #     return [cosmosdb.cosmosdb_client, cosmosdb.database_client, cosmosdb.container_client]


    async def ensure(self):
        if not self.cosmosdb_client or not self.database_client or not self.container_client:
            return False, "CosmosDB client not initialized correctly"
        try:
            database_info = await self.database_client.read()
        except:
            return False, f"CosmosDB database {self.database_name} on account {self.cosmosdb_endpoint} not found"
        
        try:
            container_info = await self.container_client.read()
        except:
            return False, f"CosmosDB container {self.container_name} not found"
            
        return True, "CosmosDB client initialized successfully"


    async def add_conversation(self, user_id: str, title: str, request_json: json):
        history_metadata = {}
        async with self.cosmosdb_factory as cosmosdb_client:
                # check for the conversation_id, if the conversation is not set, we will create a new one
                
                conversation_dict = await self.create_conversation(
                    user_id=user_id, title=title, cosmosdb_client
                )
                conversation_id = conversation_dict["id"]
                history_metadata["title"] = title
                history_metadata["date"] = conversation_dict["createdAt"]
                history_metadata["conversation_id"] = conversation_id
                
                ## Format the incoming message object in the "chat/completions" messages format
                ## then write it to the conversation history in cosmos
                messages = request_json["messages"]
                if len(messages) > 0 and messages[-1]["role"] == "user":
                    createdMessageValue = await self.history_repository.create_message(
                        uuid=str(uuid.uuid4()),
                        conversation_id=conversation_id,
                        user_id=user_id,
                        input_message=messages[-1],
                    )
                    if createdMessageValue == "Conversation not found":
                        raise Exception(
                            "Conversation not found for the given conversation ID: "
                            + conversation_id
                            + "."
                        )
                else:
                    raise Exception("No user message found")
        
        return history_metadata



    async def create_conversation(
        self, 
        user_id, 
        title = '', 
        cosmosdb_client:CosmosDB=None
    ):
        conversation = {
            'id': str(uuid.uuid4()),  
            'type': 'conversation',
            'createdAt': datetime.now().isoformat(),  
            'updatedAt': datetime.now().isoformat(),  
            'userId': user_id,
            'title': title
        }
        ## TODO: add some error handling based on the output of the upsert_item call
        resp = await cosmosdb_client.container_client.upsert_item(conversation)  
        if resp:
            return resp
        else:
            return False
    
    
    async def upsert_conversation(self, conversation):
        resp = await self.container_client.upsert_item(conversation)
        if resp:
            return resp
        else:
            return False


    async def delete_conversation(self, user_id, conversation_id):
        conversation = await self.container_client.read_item(item=conversation_id, partition_key=user_id)        
        if conversation:
            resp = await self.container_client.delete_item(item=conversation_id, partition_key=user_id)
            return resp
        else:
            return True

        
    async def delete_messages(self, conversation_id, user_id):
        ## get a list of all the messages in the conversation
        messages = await self.get_messages(user_id, conversation_id)
        response_list = []
        if messages:
            for message in messages:
                resp = await self.container_client.delete_item(item=message['id'], partition_key=user_id)
                response_list.append(resp)
            return response_list


    async def get_conversations(self, user_id, limit, sort_order = 'DESC', offset = 0):
        parameters = [
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.userId = @userId and c.type='conversation' order by c.updatedAt {sort_order}"
        if limit is not None:
            query += f" offset {offset} limit {limit}" 
        
        conversations = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            conversations.append(item)
        
        return conversations


    async def get_conversation(self, user_id, conversation_id):
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.id = @conversationId and c.type='conversation' and c.userId = @userId"
        conversations = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            conversations.append(item)

        ## if no conversations are found, return None
        if len(conversations) == 0:
            return None
        else:
            return conversations[0]
 
 
    async def create_message(self, uuid, conversation_id, user_id, input_message: dict):
        message = {
            'id': uuid,
            'type': 'message',
            'userId' : user_id,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'conversationId' : conversation_id,
            'role': input_message['role'],
            'content': input_message['content']
        }

        if self.enable_message_feedback:
            message['feedback'] = ''
        
        resp = await self.container_client.upsert_item(message)  
        if resp:
            ## update the parent conversations's updatedAt field with the current message's createdAt datetime value
            conversation = await self.get_conversation(user_id, conversation_id)
            if not conversation:
                return "Conversation not found"
            conversation['updatedAt'] = message['createdAt']
            await self.upsert_conversation(conversation)
            return resp
        else:
            return False
    
    
    async def update_message_feedback(self, user_id, message_id, feedback):
        message = await self.container_client.read_item(item=message_id, partition_key=user_id)
        if message:
            message['feedback'] = feedback
            resp = await self.container_client.upsert_item(message)
            return resp
        else:
            return False


    async def get_messages(self, user_id, conversation_id):
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c WHERE c.conversationId = @conversationId AND c.type='message' AND c.userId = @userId ORDER BY c.timestamp ASC"
        messages = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            messages.append(item)

        return messages

