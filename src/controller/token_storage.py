class TokenStorage:
    _slack_token = {}
    @classmethod
    def set_slack_token(cls, session_id: str, slack_token: str):
        cls._slack_token[session_id] = slack_token

    @classmethod
    def get_slack_token(cls, session_id: str) -> str:
        slack_token = None
        if cls._slack_token[session_id]:
            slack_token = cls._slack_token[session_id]
        return cls._slack_token[session_id]
