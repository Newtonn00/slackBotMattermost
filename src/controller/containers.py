from dependency_injector import containers, providers

from src.business.bookmark_service import BookmarkService
from src.business.config_service import ConfigService
from src.business.messages_service import MessagesService
from src.business.pin_service import PinService
from src.business.thread_service import ThreadService
from src.business.user_service import UserService
from src.controller.mattermost_bookmarks import MattermostBookmarks
from src.controller.mattermost_messages import MattermostMessages
from src.controller.mattermost_upload_messages import MattermostUploadMessages
from src.controller.mattermost_pins import MattermostPins
from src.controller.mattermost_users_handler import MattermostUsersHandler
from src.controller.mattermost_web_client import MattermostWebClient
from src.controller.slack_load_bookmarks import SlackLoadBookmarks
from src.controller.slack_load_messages import SlackLoadMessages
from src.controller.slack_app_manager import SlackAppManager
from src.controller.slack_load_pins import SlackLoadPins
from src.controller.slack_messages_handler import SlackMessagesHandler
from src.controller.slack_users_handler import SlackUsersHandler
from src.controller.slack_web_client import SlackWebClient
from src.repository.config_repository import ConfigRepository


class Containers(containers.DeclarativeContainer):
    slack_web_client = providers.Singleton(SlackWebClient)
    mattermost_web_client = providers.Singleton(MattermostWebClient)
    mattermost_upload_messages = providers.Singleton(MattermostUploadMessages,
                                                     mattermost_web_client=mattermost_web_client)
    mattermost_messages = providers.Singleton(MattermostMessages, mattermost_web_client)

    config_repo = providers.Factory(ConfigRepository)
    config_service = providers.Factory(ConfigService, config_repo=config_repo)
    slack_load_pins = providers.Factory(SlackLoadPins)
    slack_load_bookmarks = providers.Factory(SlackLoadBookmarks)
    slack_messages_handler = providers.Singleton(SlackMessagesHandler, slack_web_client)
    slack_users_handler = providers.Singleton(SlackUsersHandler, slack_web_client)
    mattermost_users_handler = providers.Singleton(MattermostUsersHandler, mattermost_web_client)

    mattermost_pins = providers.Factory(MattermostPins, mattermost_web_client)
    mattermost_bookmarks = providers.Factory(MattermostBookmarks, mattermost_web_client)
    pin_service = providers.Singleton(PinService, slack_load_pins, mattermost_pins, mattermost_upload_messages,
                                      mattermost_messages)
    bookmark_service = providers.Singleton(BookmarkService, slack_load_bookmarks, mattermost_bookmarks,
                                           mattermost_upload_messages)

    user_service = providers.Singleton(UserService,
                                       slack_users_handler=slack_users_handler,
                                       mattermost_users_handler=mattermost_users_handler)
    messages_service = providers.Singleton(MessagesService,
                                           config_service=config_service,
                                           mattermost_upload_messages=mattermost_upload_messages)
    thread_service = providers.Singleton(ThreadService,
                                         config_service=config_service,
                                         messages_service=messages_service,
                                         mattermost_upload_messages=mattermost_upload_messages,
                                         mattermost_messages=mattermost_messages,
                                         slack_messages_handler=slack_messages_handler)

    slack_load_messages = providers.Factory(SlackLoadMessages,
                                            web_client=slack_web_client,
                                            config_service=config_service,
                                            messages_service=messages_service,
                                            pin_service=pin_service,
                                            bookmark_service=bookmark_service,
                                            thread_service=thread_service)
    slack_app_manager = providers.Factory(SlackAppManager,
                                          config_service=config_service,
                                          slack_load_messages=slack_load_messages,
                                          mattermost_upload_messages=mattermost_upload_messages,
                                          pin_service=pin_service,
                                          bookmark_service=bookmark_service,
                                          thread_service=thread_service,
                                          user_service=user_service)
