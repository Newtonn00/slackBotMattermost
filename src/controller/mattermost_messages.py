import logging

from requests import HTTPError


class MattermostMessages:
    def __init__(self, mattermost_web_client):
        self._logger_bot = logging.getLogger("")
        self._mm_web_client = mattermost_web_client
        self._messages_per_page = 100

    def load_messages(self, channel_id: str) -> dict:
        messages_dict = {}
        response = ''
        params = {
            "page": 0,
            "per_page": self._messages_per_page
        }

        try:
            while True:
                messages = {}
                response = self._mm_web_client.mattermost_session.get(
                    f'{self._mm_web_client.mattermost_url}/channels/{channel_id}/posts',
                    params=params)
                response.raise_for_status()
                messages = response.json()["posts"]

                if not messages:
                    break

                messages_dict.update(messages)
                params["page"] += 1

            self._logger_bot.info("Mattermost messages loaded (%d)", len(messages_dict))

        except HTTPError as err:
            self._logger_bot.error(
                f'Mattermost API Error (channels/posts). Status code: {response.status_code} '
                f'Response:{response.text} Error:{err}')
        return messages_dict
