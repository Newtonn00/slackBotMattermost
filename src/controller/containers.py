from dependency_injector import containers, providers
from src.business.config_service import ConfigService
from src.business.messages_service import MessagesService
from src.controller.mattermost_upload_messages import MattermostUploadMessages
from src.controller.mattermost_web_client import MattermostWebClient
from src.controller.slack_load_messages import SlackLoadMessages
from src.controller.slack_app_manager import SlackAppManager
from src.controller.slack_web_client import SlackWebClient
from src.repository.config_repository import ConfigRepository


class Containers(containers.DeclarativeContainer):
    slack_web_client = providers.Singleton(SlackWebClient)
    mattermost_web_client = providers.Singleton(MattermostWebClient)
    mattermost_upload_messages = providers.Singleton(MattermostUploadMessages,
                                                     mattermost_web_client=mattermost_web_client)

    config_repo = providers.Factory(ConfigRepository)
    config_service = providers.Factory(ConfigService, config_repo=config_repo)
    messages_service = providers.Factory(MessagesService, config_service=config_service,
                                         mattermost_upload_messages=mattermost_upload_messages)
    slack_load_messages = providers.Factory(SlackLoadMessages, web_client=slack_web_client,
                                            config_service=config_service,
                                            messages_service=messages_service,
                                            mattermost_upload_messages=mattermost_upload_messages)
    slack_app_manager = providers.Factory(SlackAppManager,
                                          config_service=config_service,
                                          slack_load_messages=slack_load_messages,
                                          mattermost_upload_messages=mattermost_upload_messages)



