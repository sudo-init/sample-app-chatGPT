# history/controller/chat_controller.py

from quart import Blueprint, render_template, request, redirect, url_for
from history.service.chat_service import ChatService
from history.infrastructure.chat_repository import InMemoryChatRepository

class ChatController:
    def __init__(self):
        self.repository = InMemoryChatRepository()
        self.chat_service = ChatService(self.repository)
        self.blueprint = Blueprint('chat', __name__)
        self._register_routes()

    def _register_routes(self):
        self.blueprint.route('/')(self.index)
        self.blueprint.route('/send_message', methods=['POST'])(self.send_message)

    async def index(self):
        history = self.chat_service.get_history()
        return await render_template('index.html', history=history)

    async def send_message(self):
        user_message = (await request.form)['message']
        
        # 여기에 AI 응답 생성 로직을 추가할 수 있습니다
        ai_response = f"AI 응답: {user_message}"  # 예시로 단순히 사용자 메시지를 에코합니다

        # 대화 기록에 추가
        self.chat_service.add_message('User', user_message)
        self.chat_service.add_message('AI', ai_response)

        return redirect(url_for('chat.index'))
