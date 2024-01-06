class CommonCounter:
    _error_count = 0
    _error_custom_count = 0
    _user_count = 0
    _user_custom_count = 0
    _channel_count = 0
    _channel_custom_count = 0
    _pin_count = 0
    _pin_custom_count = 0
    _message_count = 0
    _message_custom_count = 0
    _file_count = 0
    _file_custom_count = 0

    @classmethod
    def increment_error(cls):
        cls._error_count += 1
        cls._error_custom_count += 1

    @classmethod
    def get_error_count(cls):
        return cls._error_count

    @classmethod
    def get_error_custom_count(cls):
        return cls._error_custom_count

    @classmethod
    def init_counter(cls):
        cls._error_count = 0
        cls._pin_count = 0
        cls._channel_count = 0
        cls._user_count = 0
        cls._message_count = 0
        cls._file_count = 0
        cls._file_custom_count = 0
        cls._error_custom_count = 0
        cls._pin_custom_count = 0
        cls._channel_custom_count = 0
        cls._user_custom_count = 0
        cls._message_custom_count = 0

    @classmethod
    def init_custom_counter(cls):
        cls._error_custom_count = 0
        cls._pin_custom_count = 0
        cls._channel_custom_count = 0
        cls._user_custom_count = 0
        cls._message_custom_count = 0
        cls._file_custom_count = 0

    @classmethod
    def increment_user(cls):
        cls._user_count += 1
        cls._user_custom_count += 1
    @classmethod
    def get_user_count(cls):
        return cls._user_count

    @classmethod
    def get_user_custom_count(cls):
        return cls._user_custom_count

    @classmethod
    def init_user_custom_counter(cls):
        cls._user_custom_count = 0

    @classmethod
    def increment_channel(cls):
        cls._channel_count += 1
        cls._channel_custom_count += 1
    @classmethod
    def get_channel_count(cls):
        return cls._channel_count

    @classmethod
    def get_channel_custom_count(cls):
        return cls._channel_custom_count

    @classmethod
    def init_channel_custom_counter(cls):
        cls._channel_custom_count = 0

    @classmethod
    def increment_pin(cls):
        cls._pin_count += 1
        cls._pin_custom_count += 1
    @classmethod
    def get_pin_count(cls):
        return cls._pin_count

    @classmethod
    def get_pin_custom_count(cls):
        return cls._pin_custom_count

    @classmethod
    def init_pin_custom_counter(cls):
        cls._pin_custom_count = 0

    @classmethod
    def increment_message(cls):
        cls._message_count += 1
        cls._message_custom_count += 1
    @classmethod
    def get_message_count(cls):
        return cls._message_count

    @classmethod
    def get_message_custom_count(cls):
        return cls._message_custom_count

    @classmethod
    def init_message_custom_counter(cls):
        cls._message_custom_count = 0

    @classmethod
    def increment_file(cls):
        cls._file_count += 1
        cls._file_custom_count += 1
    @classmethod
    def get_file_count(cls):
        return cls._file_count

    @classmethod
    def get_file_custom_count(cls):
        return cls._file_custom_count

    @classmethod
    def init_file_custom_counter(cls):
        cls._file_custom_count = 0

    @classmethod
    def get_str_statistic(cls) -> str:
        stat_str = (f'messages - {cls._message_count}\n'
                    f'files - {cls._file_count}\n'
                    f'users - {cls._user_count}\n'
                    f'channels - {cls._channel_count}\n'
                    f'pins - {cls._pin_count}\n'
                    f'errors - {cls._error_count}')
        return stat_str

    @classmethod
    def get_str_custom_statistic(cls) -> str:
        stat_str = (f'messages - {cls._message_custom_count}\n'
                    f'files - {cls._file_custom_count}\n'
                    f'users - {cls._user_custom_count}\n'
                    f'channels - {cls._channel_custom_count}\n'
                    f'pins - {cls._pin_custom_count}\n'
                    f'errors - {cls._error_custom_count}')
        return stat_str
