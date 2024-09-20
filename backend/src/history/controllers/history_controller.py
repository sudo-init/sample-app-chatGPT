import uuid

from logging import getLogger
from quart import Blueprint, request, jsonify

from backend.src.auth.auth_utils import get_authenticated_user_details
from backend.src.conversation.conversation_service import ConversationService
from backend.src.history.history_service import HistoryService
from backend.src.history.repositories.history_repository import HistoryRepository
from backend.src.settings import app_settings
from backend.src.utils.logger import get_main_logger_name

class HistoryControllers:
    
    def __init__(
        self, 
        conversation_service: ConversationService,
        history_service: HistoryService,
        history_repository: HistoryRepository
    ):
        self.conversation_service = conversation_service
        self.history_service = history_service
        self.history_repository = history_repository
        self.blueprint = Blueprint("history", __name__, url_prefix="/history")
        self.logger = getLogger(f"{get_main_logger_name()}.history.controllers")
        self._register_routes()


    def _register_routes(self):
        self.blueprint.add_url_rule(
            '/generate', 'add_conversation', self.add_conversation, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/update', 'update_conversation', self.update_conversation, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/message_feedback', 'update_message', self.update_message, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/delete', 'delete_conversation', self.delete_conversation, methods=['DELETE']
        )
        self.blueprint.add_url_rule(
            '/list', 'list_conversations', self.list_conversations, methods=['GET']
        )
        self.blueprint.add_url_rule(
            '/read', 'get_conversation', self.get_conversation, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/rename', 'rename_conversation', self.rename_conversation, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/delete_all', 'delete_all_conversations', self.delete_all_conversations, methods=['DELETE']
        )
        self.blueprint.add_url_rule(
            '/clear', 'clear_messages', self.clear_messages, methods=['POST']
        )
        self.blueprint.add_url_rule(
            '/ensure', 'ensure_cosmos', self.ensure_cosmos, methods=['GET']
        )
    
    
    ## Conversation History API ##
    # @bp.route("/history/generate", methods=["POST"])
    async def add_conversation(self):
        


    # @bp.route("/history/update", methods=["POST"])
    async def update_conversation(self):
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        try:
            # make sure cosmos is configured
            cosmos_conversation_client = init_cosmosdb_client()
            if not cosmos_conversation_client:
                raise Exception("CosmosDB is not configured or not working")

            # check for the conversation_id, if the conversation is not set, we will create a new one
            if not conversation_id:
                raise Exception("No conversation_id found")

            ## Format the incoming message object in the "chat/completions" messages format
            ## then write it to the conversation history in cosmos
            messages = request_json["messages"]
            if len(messages) > 0 and messages[-1]["role"] == "assistant":
                if len(messages) > 1 and messages[-2].get("role", None) == "tool":
                    # write the tool message first
                    await cosmos_conversation_client.create_message(
                        uuid=str(uuid.uuid4()),
                        conversation_id=conversation_id,
                        user_id=user_id,
                        input_message=messages[-2],
                    )
                # write the assistant message
                await cosmos_conversation_client.create_message(
                    uuid=messages[-1]["id"],
                    conversation_id=conversation_id,
                    user_id=user_id,
                    input_message=messages[-1],
                )
            else:
                raise Exception("No bot messages found")

            # Submit request to Chat Completions for response
            await cosmos_conversation_client.cosmosdb_client.close()
            response = {"success": True}
            return jsonify(response), 200

        except Exception as e:
            self.logger.exception("Exception in /history/update")
            return jsonify({"error": str(e)}), 500


    # @bp.route("/history/message_feedback", methods=["POST"])
    async def update_message(self):
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]
        cosmos_conversation_client = init_cosmosdb_client()

        ## check request for message_id
        request_json = await request.get_json()
        message_id = request_json.get("message_id", None)
        message_feedback = request_json.get("message_feedback", None)
        try:
            if not message_id:
                return jsonify({"error": "message_id is required"}), 400

            if not message_feedback:
                return jsonify({"error": "message_feedback is required"}), 400

            ## update the message in cosmos
            updated_message = await cosmos_conversation_client.update_message_feedback(
                user_id, message_id, message_feedback
            )
            if updated_message:
                return (
                    jsonify(
                        {
                            "message": f"Successfully updated message with feedback {message_feedback}",
                            "message_id": message_id,
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "error": f"Unable to update message {message_id}. It either does not exist or the user does not have access to it."
                        }
                    ),
                    404,
                )

        except Exception as e:
            self.logger.exception("Exception in /history/message_feedback")
            return jsonify({"error": str(e)}), 500


    # @bp.route("/history/delete", methods=["DELETE"])
    async def delete_conversation(self):
        ## get the user id from the request headers
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        try:
            if not conversation_id:
                return jsonify({"error": "conversation_id is required"}), 400

            ## make sure cosmos is configured
            cosmos_conversation_client = init_cosmosdb_client()
            if not cosmos_conversation_client:
                raise Exception("CosmosDB is not configured or not working")

            ## delete the conversation messages from cosmos first
            deleted_messages = await cosmos_conversation_client.delete_messages(
                conversation_id, user_id
            )

            ## Now delete the conversation
            deleted_conversation = await cosmos_conversation_client.delete_conversation(
                user_id, conversation_id
            )

            await cosmos_conversation_client.cosmosdb_client.close()

            return (
                jsonify(
                    {
                        "message": "Successfully deleted conversation and messages",
                        "conversation_id": conversation_id,
                    }
                ),
                200,
            )
        except Exception as e:
            self.logger.exception("Exception in /history/delete")
            return jsonify({"error": str(e)}), 500


    # @bp.route("/history/list", methods=["GET"])
    async def list_conversations(self):
        offset = request.args.get("offset", 0)
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## make sure cosmos is configured
        cosmos_conversation_client = init_cosmosdb_client()
        if not cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        ## get the conversations from cosmos
        conversations = await cosmos_conversation_client.get_conversations(
            user_id, offset=offset, limit=25
        )
        await cosmos_conversation_client.cosmosdb_client.close()
        if not isinstance(conversations, list):
            return jsonify({"error": f"No conversations for {user_id} were found"}), 404

        ## return the conversation ids

        return jsonify(conversations), 200


    # @bp.route("/history/read", methods=["POST"])
    async def get_conversation(self):
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400

        ## make sure cosmos is configured
        cosmos_conversation_client = init_cosmosdb_client()
        if not cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        ## get the conversation object and the related messages from cosmos
        conversation = await cosmos_conversation_client.get_conversation(
            user_id, conversation_id
        )
        ## return the conversation id and the messages in the bot frontend format
        if not conversation:
            return (
                jsonify(
                    {
                        "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
                    }
                ),
                404,
            )

        # get the messages for the conversation from cosmos
        conversation_messages = await cosmos_conversation_client.get_messages(
            user_id, conversation_id
        )

        ## format the messages in the bot frontend format
        messages = [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "createdAt": msg["createdAt"],
                "feedback": msg.get("feedback"),
            }
            for msg in conversation_messages
        ]

        await cosmos_conversation_client.cosmosdb_client.close()
        return jsonify({"conversation_id": conversation_id, "messages": messages}), 200


    # @bp.route("/history/rename", methods=["POST"])
    async def rename_conversation(self):
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400

        ## make sure cosmos is configured
        cosmos_conversation_client = init_cosmosdb_client()
        if not cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        ## get the conversation from cosmos
        conversation = await cosmos_conversation_client.get_conversation(
            user_id, conversation_id
        )
        if not conversation:
            return (
                jsonify(
                    {
                        "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
                    }
                ),
                404,
            )

        ## update the title
        title = request_json.get("title", None)
        if not title:
            return jsonify({"error": "title is required"}), 400
        conversation["title"] = title
        updated_conversation = await cosmos_conversation_client.upsert_conversation(
            conversation
        )

        await cosmos_conversation_client.cosmosdb_client.close()
        return jsonify(updated_conversation), 200


    # @bp.route("/history/delete_all", methods=["DELETE"])
    async def delete_all_conversations(self):
        ## get the user id from the request headers
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        # get conversations for user
        try:
            ## make sure cosmos is configured
            cosmos_conversation_client = init_cosmosdb_client()
            if not cosmos_conversation_client:
                raise Exception("CosmosDB is not configured or not working")

            conversations = await cosmos_conversation_client.get_conversations(
                user_id, offset=0, limit=None
            )
            if not conversations:
                return jsonify({"error": f"No conversations for {user_id} were found"}), 404

            # delete each conversation
            for conversation in conversations:
                ## delete the conversation messages from cosmos first
                deleted_messages = await cosmos_conversation_client.delete_messages(
                    conversation["id"], user_id
                )

                ## Now delete the conversation
                deleted_conversation = await cosmos_conversation_client.delete_conversation(
                    user_id, conversation["id"]
                )
            await cosmos_conversation_client.cosmosdb_client.close()
            return (
                jsonify(
                    {
                        "message": f"Successfully deleted conversation and messages for user {user_id}"
                    }
                ),
                200,
            )

        except Exception as e:
            self.logger.exception("Exception in /history/delete_all")
            return jsonify({"error": str(e)}), 500


    # @bp.route("/history/clear", methods=["POST"])
    async def clear_messages(self):
        ## get the user id from the request headers
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user["user_principal_id"]

        ## check request for conversation_id
        request_json = await request.get_json()
        conversation_id = request_json.get("conversation_id", None)

        try:
            if not conversation_id:
                return jsonify({"error": "conversation_id is required"}), 400

            ## make sure cosmos is configured
            cosmos_conversation_client = init_cosmosdb_client()
            if not cosmos_conversation_client:
                raise Exception("CosmosDB is not configured or not working")

            ## delete the conversation messages from cosmos
            deleted_messages = await cosmos_conversation_client.delete_messages(
                conversation_id, user_id
            )

            return (
                jsonify(
                    {
                        "message": "Successfully deleted messages in conversation",
                        "conversation_id": conversation_id,
                    }
                ),
                200,
            )
        except Exception as e:
            logging.exception("Exception in /history/clear_messages")
            return jsonify({"error": str(e)}), 500


    @bp.route("/history/ensure", methods=["GET"])
    async def ensure_cosmos():
        if not app_settings.chat_history:
            return jsonify({"error": "CosmosDB is not configured"}), 404

        try:
            cosmos_conversation_client = init_cosmosdb_client()
            success, err = await cosmos_conversation_client.ensure()
            if not cosmos_conversation_client or not success:
                if err:
                    return jsonify({"error": err}), 422
                return jsonify({"error": "CosmosDB is not configured or not working"}), 500

            await cosmos_conversation_client.cosmosdb_client.close()
            return jsonify({"message": "CosmosDB is configured and working"}), 200
        except Exception as e:
            logging.exception("Exception in /history/ensure")
            cosmos_exception = str(e)
            if "Invalid credentials" in cosmos_exception:
                return jsonify({"error": cosmos_exception}), 401
            elif "Invalid CosmosDB database name" in cosmos_exception:
                return (
                    jsonify(
                        {
                            "error": f"{cosmos_exception} {app_settings.chat_history.database} for account {app_settings.chat_history.account}"
                        }
                    ),
                    422,
                )
            elif "Invalid CosmosDB container name" in cosmos_exception:
                return (
                    jsonify(
                        {
                            "error": f"{cosmos_exception}: {app_settings.chat_history.conversations_container}"
                        }
                    ),
                    422,
                )
            else:
                return jsonify({"error": "CosmosDB is not working"}), 500


    