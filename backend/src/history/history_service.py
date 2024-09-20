import uuid

from logging import getLogger
from quart import request, jsonify

from backend.src.auth.auth_utils import get_authenticated_user_details
from backend.src.conversation.conversation_service import ConversationService
from backend.src.history.repositories.history_repository import HistoryRepository
from backend.src.utils.logger import get_main_logger_name


class HistoryService:
    def __init__(
        self, 
        history_repository: HistoryRepository, 
        conversation_service: ConversationService
    ):
        self.logger = getLogger(f"{get_main_logger_name()}.history.service")
        self.history_repository = history_repository
        self.conversation_service = conversation_service
        

    async def add_conversation(self):
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        try:
            history_metadata = {}
            if not conversation_id:
                title = await self.generate_title(request_json["messages"])
                history_metadata = self.history_repository.add_conversation(user_id, title, request_json)
            
            # Submit request to Chat Completions for response
            request_body = await request.get_json()
            request_body["history_metadata"] = history_metadata
            return await self.conversation_service.conversation_internal(
                request_body, request.headers
                )

        except Exception as e:
            self.logger.exception("Exception in /history/generate")
            return jsonify({"error": str(e)}), 500
        
        
    async def generate_title(conversation_messages) -> str:
        ## make sure the messages are sorted by _ts descending
        title_prompt = "Summarize the conversation so far into a 4-word or less title. Do not use any quotation marks or punctuation. Do not include any other commentary or description."

        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation_messages
        ]
        messages.append({"role": "user", "content": title_prompt})

        try:
            azure_openai_client = init_openai_client()
            response = await azure_openai_client.chat.completions.create(
                model=app_settings.azure_openai.model, messages=messages, temperature=1, max_tokens=64
            )

            title = response.choices[0].message.content
            return title
        except Exception as e:
            logging.exception("Exception while generating title", e)
            return messages[-2]["content"]
        
        
        
        
        
        
        
        
        
        
    def get_all(self):
        return self.history_repository.get_all()

    def get_by_id(self, id):
        return self.history_repository.get_by_id(id)

    def create(self, history):
        return self.history_repository.create(history)

    def update(self, id, history):
        return self.history_repository.update(id, history)

    def delete(self, id):
        return self.history_repository.delete(id)