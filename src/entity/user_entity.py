from dataclasses import dataclass


@dataclass
class UserEntity:
    id: str
    name: str
    title: str
    display_name: str
    first_name: str
    last_name: str
    email: str
    is_bot: bool
    is_deleted: bool
    is_app_user: bool
    image_original: str






