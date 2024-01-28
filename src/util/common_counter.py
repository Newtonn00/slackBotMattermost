class CommonCounter:
    _error_count = {}
    _error_custom_count = {}
    _user_count = {}
    _user_custom_count = {}
    _channel_count = {}
    _channel_custom_count = {}
    _pin_count = {}
    _pin_custom_count = {}
    _message_count = {}
    _message_custom_count = {}
    _file_count = {}
    _file_custom_count = {}

    @classmethod
    def increment_error(cls, session_id: str):
        cls._error_count.setdefault(session_id, 0)
        cls._error_count[session_id] += 1

        cls._error_custom_count.setdefault(session_id, 0)
        cls._error_custom_count[session_id] += 1

    @classmethod
    def get_error_count(cls, session_id: str):
        return cls._error_count.get(session_id, 0)

    @classmethod
    def get_error_custom_count(cls, session_id: str):
        return cls._error_custom_count.get(session_id, 0)

    @classmethod
    def init_counter(cls, session_id: str):
        cls._error_count[session_id] = 0
        cls._pin_count[session_id] = 0
        cls._channel_count[session_id] = 0
        cls._user_count[session_id] = 0
        cls._message_count[session_id] = 0
        cls._file_count[session_id] = 0
        cls._file_custom_count[session_id] = 0
        cls._error_custom_count[session_id] = 0
        cls._pin_custom_count[session_id] = 0
        cls._channel_custom_count[session_id] = 0
        cls._user_custom_count[session_id] = 0
        cls._message_custom_count[session_id] = 0

    @classmethod
    def init_custom_counter(cls, session_id: str):
        cls._error_custom_count[session_id] = 0
        cls._pin_custom_count[session_id] = 0
        cls._channel_custom_count[session_id] = 0
        cls._user_custom_count[session_id] = 0
        cls._message_custom_count[session_id] = 0
        cls._file_custom_count[session_id] = 0

    @classmethod
    def increment_user(cls, session_id: str):
        cls._user_count.setdefault(session_id, 0)
        cls._user_count[session_id] += 1

        cls._user_custom_count.setdefault(session_id, 0)
        cls._user_custom_count[session_id] += 1

    @classmethod
    def get_user_count(cls, session_id: str):
        return cls._user_count.get(session_id, 0)

    @classmethod
    def get_user_custom_count(cls, session_id: str):
        return cls._user_custom_count.get(session_id, 0)

    @classmethod
    def init_user_custom_counter(cls, session_id: str):
        cls._user_custom_count[session_id] = 0

    @classmethod
    def increment_channel(cls, session_id: str):
        cls._channel_count.setdefault(session_id, 0)
        cls._channel_count[session_id] += 1

        cls._channel_custom_count.setdefault(session_id, 0)
        cls._channel_custom_count[session_id] += 1

    @classmethod
    def get_channel_count(cls, session_id: str):
        return cls._channel_count.get(session_id, 0)

    @classmethod
    def get_channel_custom_count(cls, session_id: str):
        return cls._channel_custom_count.get(session_id, 0)

    @classmethod
    def init_channel_custom_counter(cls, session_id: str):
        cls._channel_custom_count[session_id] = 0

    @classmethod
    def increment_pin(cls, session_id: str):
        cls._pin_count.setdefault(session_id, 0)
        cls._pin_count[session_id] += 1

        cls._pin_custom_count.setdefault(session_id, 0)
        cls._pin_custom_count[session_id] += 1

    @classmethod
    def get_pin_count(cls, session_id: str):
        return cls._pin_count.get(session_id, 0)

    @classmethod
    def get_pin_custom_count(cls, session_id: str):
        return cls._pin_custom_count.get(session_id, 0)

    @classmethod
    def init_pin_custom_counter(cls, session_id: str):
        cls._pin_custom_count[session_id] = 0

    @classmethod
    def increment_message(cls, session_id: str):
        cls._message_count.setdefault(session_id, 0)
        cls._message_count[session_id] += 1

        cls._message_custom_count.setdefault(session_id, 0)
        cls._message_custom_count[session_id] += 1

    @classmethod
    def get_message_count(cls, session_id: str):
        return cls._message_count.get(session_id, 0)

    @classmethod
    def get_message_custom_count(cls, session_id: str):
        return cls._message_custom_count.get(session_id, 0)

    @classmethod
    def init_message_custom_counter(cls, session_id: str):
        cls._message_custom_count[session_id] = 0

    @classmethod
    def increment_file(cls, session_id: str):
        cls._file_count.setdefault(session_id, 0)
        cls._file_count[session_id] += 1

        cls._file_custom_count.setdefault(session_id, 0)
        cls._file_custom_count[session_id] += 1

    @classmethod
    def get_file_count(cls, session_id: str):
        return cls._file_count.get(session_id, 0)

    @classmethod
    def get_file_custom_count(cls, session_id: str):
        return cls._file_custom_count.get(session_id, 0)

    @classmethod
    def init_file_custom_counter(cls, session_id: str):
        cls._file_custom_count[session_id] = 0

    @classmethod
    def get_str_statistic(cls, session_id: str) -> str:
        stat_str = (f'Common statistic | Session: {session_id}\n'   
                    f'messages - {cls._message_count.get(session_id, 0)}\n'
                    f'files - {cls._file_count.get(session_id, 0)}\n'
                    f'users - {cls._user_count.get(session_id, 0)}\n'
                    f'channels - {cls._channel_count.get(session_id, 0)}\n'
                    f'pins - {cls._pin_count.get(session_id, 0)}\n'
                    f'errors - {cls._error_count.get(session_id, 0)}')
        return stat_str

    @classmethod
    def get_str_custom_statistic(cls, session_id: str) -> str:
        stat_str = (f'Common statistic | Session: {session_id}\n'
                    f'messages - {cls._message_custom_count.get(session_id, 0)}\n'
                    f'files - {cls._file_custom_count.get(session_id, 0)}\n'
                    f'users - {cls._user_custom_count.get(session_id, 0)}\n'
                    f'channels - {cls._channel_custom_count.get(session_id, 0)}\n'
                    f'pins - {cls._pin_custom_count.get(session_id, 0)}\n'
                    f'errors - {cls._error_custom_count.get(session_id, 0)}')
        return stat_str
