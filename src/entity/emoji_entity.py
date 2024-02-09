from dataclasses import dataclass

@dataclass
class EmojiEntity:
    emoji_name: str
    emoji_image: str
    local_file_path: str
