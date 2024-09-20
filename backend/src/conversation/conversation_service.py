import copy
import json

from logging import getLogger
import httpx
from quart import (jsonify, request, make_response)

from backend.src.auth.auth_utils import get_authenticated_user_details
from backend.src.openai.openai_client import OpenAiClient
from backend.src.security.ms_defender_utils import get_msdefender_user_json
from backend.src.settings import app_settings, MS_DEFENDER_ENABLED
from backend.src.utils.general import (
    convert_to_pf_format,
    format_stream_response,
    format_as_ndjson,
    format_pf_non_streaming_response,
    format_non_streaming_response,
)
from backend.src.utils.logger import get_main_logger_name


class ConversationService:
    
    def __init__(self, open_ai_client: OpenAiClient):
        self.logger = getLogger(f"{get_main_logger_name()}.conversation.service")
        self.open_ai_client = open_ai_client
    
    
    async def conversation(self, ):
        if not request.is_json:
            return jsonify({"error": "request must be json"}), 415
        request_json = await request.get_json()

        return await self.conversation_internal(request_json, request.headers)
    
    
    async def conversation_internal(self, request_body, request_headers):
        try:
            if app_settings.azure_openai.stream and not app_settings.base_settings.use_promptflow:
                result = await self.stream_chat_request(request_body, request_headers)
                response = await make_response(format_as_ndjson(result))
                response.timeout = None
                response.mimetype = "application/json-lines"
                return response
            else:
                result = await self.complete_chat_request(request_body, request_headers)
                return jsonify(result)

        except Exception as ex:
            self.logger.exception(ex)
            if hasattr(ex, "status_code"):
                return jsonify({"error": str(ex)}), ex.status_code
            else:
                return jsonify({"error": str(ex)}), 500
            
    
    async def stream_chat_request(self, request_body, request_headers):
        response, apim_request_id = await self.send_chat_request(request_body, request_headers)
        history_metadata = request_body.get("history_metadata", {})
        
        async def generate():
            async for completionChunk in response:
                yield format_stream_response(completionChunk, history_metadata, apim_request_id)

        return generate()
    
    
    async def send_chat_request(self, request_body, request_headers):
        filtered_messages = []
        messages = request_body.get("messages", [])
        for message in messages:
            if message.get("role") != 'tool':
                filtered_messages.append(message)
                
        request_body['messages'] = filtered_messages
        model_args = self.prepare_model_args(request_body, request_headers)

        try:
            azure_openai_client = self.open_ai_client.init_openai_client()
            raw_response = await azure_openai_client.chat.completions.with_raw_response.create(**model_args)
            response = raw_response.parse()
            apim_request_id = raw_response.headers.get("apim-request-id") 
        except Exception as e:
            self.logger.exception("Exception in send_chat_request")
            raise e

        return response, apim_request_id
    
    
    async def complete_chat_request(self, request_body, request_headers):
        if app_settings.base_settings.use_promptflow:
            response = await self.promptflow_request(request_body)
            history_metadata = request_body.get("history_metadata", {})
            return format_pf_non_streaming_response(
                response,
                history_metadata,
                app_settings.promptflow.response_field_name,
                app_settings.promptflow.citations_field_name
            )
        else:
            response, apim_request_id = await self.send_chat_request(request_body, request_headers)
            history_metadata = request_body.get("history_metadata", {})
            return format_non_streaming_response(response, history_metadata, apim_request_id)
        

    async def promptflow_request(self, request):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {app_settings.promptflow.api_key}",
            }
            # Adding timeout for scenarios where response takes longer to come back
            self.logger.debug(f"Setting timeout to {app_settings.promptflow.response_timeout}")
            async with httpx.AsyncClient(
                timeout=float(app_settings.promptflow.response_timeout)
            ) as client:
                pf_formatted_obj = convert_to_pf_format(
                    request,
                    app_settings.promptflow.request_field_name,
                    app_settings.promptflow.response_field_name
                )
                # NOTE: This only support question and chat_history parameters
                # If you need to add more parameters, you need to modify the request body
                response = await client.post(
                    app_settings.promptflow.endpoint,
                    json={
                        app_settings.promptflow.request_field_name: pf_formatted_obj[-1]["inputs"][app_settings.promptflow.request_field_name],
                        "chat_history": pf_formatted_obj[:-1],
                    },
                    headers=headers,
                )
            resp = response.json()
            resp["id"] = request["messages"][-1]["id"]
            return resp
        except Exception as e:
            self.logger.error(f"An error occurred while making promptflow_request: {e}")
    
    
    def prepare_model_args(self, request_body, request_headers):
        request_messages = request_body.get("messages", [])
        messages = []
        if not app_settings.datasource:
            messages = [
                {
                    "role": "system",
                    "content": app_settings.azure_openai.system_message
                }
            ]

        for message in request_messages:
            if message:
                messages.append(
                    {
                        "role": message["role"],
                        "content": message["content"]
                    }
                )

        user_json = None
        
        if (MS_DEFENDER_ENABLED):
            authenticated_user_details = get_authenticated_user_details(request_headers)
            conversation_id = request_body.get("conversation_id", None)        
            user_json = get_msdefender_user_json(authenticated_user_details, request_headers, conversation_id)

        model_args = {
            "messages": messages,
            "temperature": app_settings.azure_openai.temperature,
            "max_tokens": app_settings.azure_openai.max_tokens,
            "top_p": app_settings.azure_openai.top_p,
            "stop": app_settings.azure_openai.stop_sequence,
            "stream": app_settings.azure_openai.stream,
            "model": app_settings.azure_openai.model,
            "user": user_json
        }

        if app_settings.datasource:
            model_args["extra_body"] = {
                "data_sources": [
                    app_settings.datasource.construct_payload_configuration(
                        request=request
                    )
                ]
            }

        model_args_clean = copy.deepcopy(model_args)
        if model_args_clean.get("extra_body"):
            secret_params = [
                "key",
                "connection_string",
                "embedding_key",
                "encoded_api_key",
                "api_key",
            ]
            for secret_param in secret_params:
                if model_args_clean["extra_body"]["data_sources"][0]["parameters"].get(
                    secret_param
                ):
                    model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                        secret_param
                    ] = "*****"
            authentication = model_args_clean["extra_body"]["data_sources"][0][
                "parameters"
            ].get("authentication", {})
            for field in authentication:
                if field in secret_params:
                    model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                        "authentication"
                    ][field] = "*****"
            embeddingDependency = model_args_clean["extra_body"]["data_sources"][0][
                "parameters"
            ].get("embedding_dependency", {})
            if "authentication" in embeddingDependency:
                for field in embeddingDependency["authentication"]:
                    if field in secret_params:
                        model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                            "embedding_dependency"
                        ]["authentication"][field] = "*****"

        self.logger.debug(f"REQUEST BODY: {json.dumps(model_args_clean, indent=4)}")

        return model_args