import json
from .base import BaseExtractor

class JsonExtractor(BaseExtractor):
    def extract(self, file_path: str, original_filename: str = None):
        metadata = self._get_basic_metadata(original_filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Невалидный JSON: {str(e)}")

        if self._is_telegram_chat(json_data):
            text = self._format_telegram_chat(json_data)
        else:
            text = json.dumps(json_data, ensure_ascii=False, indent=2)

        return text, metadata

    def _is_telegram_chat(self, data):
        if not isinstance(data, dict):
            return False
        has_name = "name" in data
        has_type = "type" in data and data["type"] in ["private_group", "private_chat", "public_group"]
        has_messages = "messages" in data and isinstance(data["messages"], list)
        return has_name and has_type and has_messages

    def _format_telegram_chat(self, data):
        lines = []
        chat_name = data.get("name", "Без названия")
        chat_type = data.get("type", "unknown")
        lines.append(f"ЧАТ: {chat_name} ({chat_type})\n")

        for msg in data.get("messages", []):
            if msg.get("type") != "message":
                continue

            from_name = msg.get("from", "Unknown")
            date = msg.get("date", "")
            lines.append(f"[{date}] {from_name}:")

            text_entities = msg.get("text_entities", [])
            if text_entities:
                message_text = "".join(entity.get("text", "") for entity in text_entities)
                if message_text:
                    lines.append(message_text)
            else:
                plain_text = msg.get("text", "")
                if isinstance(plain_text, str) and plain_text:
                    lines.append(plain_text)

            lines.append("")
        return "\n".join(lines)
