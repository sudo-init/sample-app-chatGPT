


class OpenAiClient:
    
    
    def __init__(self, config: Config):
        self.app_settings = config  
        
    
    # Initialize Azure OpenAI Client
    def init_openai_client(self):   
        azure_openai_client = None
        try:
            # API version check
            if (
                app_settings.azure_openai.preview_api_version
                < MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
            ):
                raise ValueError(
                    f"The minimum supported Azure OpenAI preview API version is '{MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION}'"
                )

            # Endpoint
            if (
                not app_settings.azure_openai.endpoint and
                not app_settings.azure_openai.resource
            ):
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_RESOURCE is required"
                )

            endpoint = (
                app_settings.azure_openai.endpoint
                if app_settings.azure_openai.endpoint
                else f"https://{app_settings.azure_openai.resource}.openai.azure.com/"
            )

            # Authentication
            aoai_api_key = app_settings.azure_openai.key
            ad_token_provider = None
            if not aoai_api_key:
                logging.debug("No AZURE_OPENAI_KEY found, using Azure Entra ID auth")
                ad_token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )

            # Deployment
            deployment = app_settings.azure_openai.model
            if not deployment:
                raise ValueError("AZURE_OPENAI_MODEL is required")

            # Default Headers
            default_headers = {"x-ms-useragent": USER_AGENT}

            azure_openai_client = AsyncAzureOpenAI(
                api_version=app_settings.azure_openai.preview_api_version,
                api_key=aoai_api_key,
                azure_ad_token_provider=ad_token_provider,
                default_headers=default_headers,
                azure_endpoint=endpoint,
            )

            return azure_openai_client
        except Exception as e:
            logging.exception("Exception in Azure OpenAI initialization", e)
            azure_openai_client = None
            raise e