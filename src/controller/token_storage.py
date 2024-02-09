class TokenStorage:
    _slack_token = {}
    _mm_token = {}
    @classmethod
    def set_slack_token(cls, session_id: str, slack_token: str):
        cls._slack_token[session_id] = slack_token

    @classmethod
    def get_slack_token(cls, session_id: str) -> str:
        slack_token = None
        if cls._slack_token[session_id]:
            slack_token = cls._slack_token[session_id]
        return cls._slack_token[session_id]

    @classmethod
    def set_mm_token(cls, session_id: str, mm_token: str):
        cls._mm_token[session_id] = mm_token

    @classmethod
    def get_mm_token(cls, session_id: str) -> str:
        mm_token = None
        if cls._mm_token[session_id]:
            slack_token = cls._mm_token[session_id]
        return cls._mm_token[session_id]

    @classmethod
    def delete_session(cls, session_id: str):
        if session_id in cls._slack_token and cls._slack_token[session_id]:
            del(cls._slack_token[session_id])
        if session_id in cls._mm_token and cls._mm_token[session_id]:
            del(cls._mm_token[session_id])