from quart import Blueprint

from backend.src.conversation.conversation_service import ConversationService


class ConversationController:
    
    def __init__(self, conversation_service: ConversationService):
        self.blueprint = Blueprint("conversation", __name__)
        self.conversation_service = conversation_service
        self._register_routes()
    
    
    def _register_routes(self):
        # Register the external methods as routes
        self.blueprint.add_url_rule(
            '/conversation', 'conversation', self.conversation, methods=['POST']
        )


    async def conversation(self, request, headers):
        return await self.conversation_service.conversation(request, headers)
    