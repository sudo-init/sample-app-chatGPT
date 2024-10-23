# history/service/chat_service.py

from history.domain.chat_domain import Message, Conversation

class ChatService:
    def __init__(self, cosmos_db_service):
        self.repository = cosmos_db_service.get_repository()

    async def create_conversation(self, user_id, title=''):
        return await self.repository.create_conversation(user_id, title)

    async def upsert_conversation(self, conversation: Conversation):
        return await self.repository.upsert_conversation(conversation)

    async def delete_conversation(self, user_id, conversation_id):
        return await self.repository.delete_conversation(user_id, conversation_id)

    async def delete_messages(self, conversation_id, user_id):
        return await self.repository.delete_messages(conversation_id, user_id)

    async def get_conversations(self, user_id, limit, sort_order='DESC', offset=0):
        return await self.repository.get_conversations(user_id, limit, sort_order, offset)

    async def get_conversation(self, user_id, conversation_id):
        return await self.repository.get_conversation(user_id, conversation_id)

    async def create_message(self, user_id, conversation_id, input_message: dict):
        message = Message(
            id=str(uuid.uuid4()),
            role=input_message['role'],
            content=input_message['content'],
            user_id=user_id,
            conversation_id=conversation_id,
            feedback='' if self.repository.client.enable_message_feedback else None
        )
        return await self.repository.create_message(message)

    async def update_message_feedback(self, user_id, message_id, feedback):
        return await self.repository.update_message_feedback(user_id, message_id, feedback)

    async def get_messages(self, user_id, conversation_id):
        return await self.repository.get_messages(user_id, conversation_id)
