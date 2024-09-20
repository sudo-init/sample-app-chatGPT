import copy
import json
import os
import logging
import uuid
import httpx
from quart import (
    Blueprint,
    Quart,
    jsonify,
    make_response,
    request,
    send_from_directory,
    render_template,
)

from backend.src.auth.auth_utils import get_authenticated_user_details
from backend.src.settings import (
    app_settings,
    MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
)
from backend.src.conversation.conversation_controller import ConversationController
from backend.src.conversation.conversation_service import ConversationService
from backend.src.utils.logger import get_main_logger_name, setup_logger


# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
if DEBUG.lower() == "true":
    logging.basicConfig(level=logging.DEBUG)

USER_AGENT = "GitHubSampleWebApp/AsyncAzureOpenAI/1.0.0"


class App:
    
    def __init__(self):
        self.app = Quart(__name__)
        
        self.blueprint = Blueprint("routes", __name__, static_folder="static", template_folder="static")
        conversation_controller = ConversationController(ConversationService())
        
        self.app.register_blueprint(self.blueprint)
        self.app.register_blueprint(conversation_controller.blueprint)
        
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        
        # logger
        self.logger = setup_logger(f"{get_main_logger_name()}.main")

        # Frontend Settings via Environment Variables
        self.frontend_settings = self.get_frontend_settings()
    

        ## service 및 controller 및 repository 등을 생성 및 초기화
        
        # if not cosmos_conversation_client:
        #         raise Exception("CosmosDB is not configured or not working")
    
    
    def get_frontend_settings(self):
        return {
            "auth_enabled": app_settings.base_settings.auth_enabled,
            "feedback_enabled": (
                app_settings.chat_history and
                app_settings.chat_history.enable_feedback
            ),
            "ui": {
                "title": app_settings.ui.title,
                "logo": app_settings.ui.logo,
                "chat_logo": app_settings.ui.chat_logo or app_settings.ui.logo,
                "chat_title": app_settings.ui.chat_title,
                "chat_description": app_settings.ui.chat_description,
                "show_share_button": app_settings.ui.show_share_button,
                "show_chat_history_button": app_settings.ui.show_chat_history_button,
            },
            "sanitize_answer": app_settings.base_settings.sanitize_answer,
        }
    

    def _register_routes(self):
        self.blueprint.add_url_rule("/", "index", self.index)
        self.blueprint.add_url_rule("/favicon.ico", "favicon", self.favicon)
        self.blueprint.add_url_rule("/assets/<path:path>", "assets", self.assets)
        self.blueprint.add_url_rule("/frontend_settings", "get_frontend_settings", self.get_frontend_settings, methods=["GET"])


    # @bp.route("/")
    async def index(self):
        return await render_template(
            "index.html",
            title=app_settings.ui.title,
            favicon=app_settings.ui.favicon
        )


    # @bp.route("/favicon.ico")
    async def favicon(self):
        return await self.blueprint.send_static_file("favicon.ico")


    # @bp.route("/assets/<path:path>")
    async def assets(self, path):
        return await send_from_directory("static/assets", path)


    # @bp.route("/frontend_settings", methods=["GET"])
    def get_frontend_settings(self):
        try:
            return jsonify(self.frontend_settings), 200
        except Exception as e:
            logging.exception("Exception in /frontend_settings")
            return jsonify({"error": str(e)}), 500
    
    
    def run(self):
        self.app.run()
    
    
if __name__ == "__main__":
    app = App()
    app.run()









