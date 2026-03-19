import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
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

        # Проверяем различные форматы чатов
        if self._is_telegram_chat(json_data):
            text = self._format_telegram_chat(json_data)
        elif self._is_simple_messages_list(json_data):
            text = self._format_simple_messages(json_data)
        else:
            text = json.dumps(json_data, ensure_ascii=False, indent=2)

        return text, metadata

    def _is_telegram_chat(self, data: Any) -> bool:
        """Проверяет, является ли это Telegram чатом в стиле экспорта из TDLib"""
        if not isinstance(data, dict):
            return False
        has_name = "name" in data
        has_type = "type" in data and data["type"] in ["private_group", "private_chat", "public_group"]
        has_messages = "messages" in data and isinstance(data["messages"], list)
        return has_name and has_type and has_messages

    def _is_simple_messages_list(self, data: Any) -> bool:
        """Проверяет, является ли это просто списком объектов с сообщениями"""
        if not isinstance(data, list):
            return False
        if len(data) == 0:
            return False
        
        # Проверяем первый элемент
        first_item = data[0]
        if not isinstance(first_item, dict):
            return False
        
        # Ищем признаки сообщения: author/sender + text/message/content + время
        has_author = any(key in first_item for key in ["author", "sender", "from", "user", "name"])
        has_text = any(key in first_item for key in ["text", "message", "content", "body"])
        has_time = any(key in first_item for key in ["date", "timestamp", "time", "created_at"])
        
        return has_author and has_text and has_time

    def _format_telegram_chat(self, data: Dict) -> str:
        """Форматирует Telegram чат в компактный текстовый формат"""
        normalized_messages: List[Dict[str, Any]] = []

        for msg in data.get("messages", []):
            if msg.get("type") != "message":
                continue

            normalized_messages.append(
                {
                    "author": msg.get("from", "Unknown"),
                    "timestamp": msg.get("date"),
                    "text": self._extract_message_text(msg),
                }
            )

        return self._format_compact_messages(normalized_messages)

    def _format_simple_messages(self, messages: List[Dict]) -> str:
        """Форматирует простой список сообщений в компактный формат"""
        normalized_messages: List[Dict[str, Any]] = []

        for msg in messages:
            # Извлекаем автора
            author = None
            for key in ["author", "sender", "from", "user", "name"]:
                if key in msg:
                    author = msg[key]
                    if isinstance(author, dict):
                        author = author.get("name", author.get("username", str(author)))
                    break

            # Извлекаем текст
            text = None
            for key in ["text", "message", "content", "body"]:
                if key in msg:
                    text = msg[key]
                    break

            # Извлекаем время
            timestamp = None
            for key in ["date", "timestamp", "time", "created_at"]:
                if key in msg:
                    timestamp = msg[key]
                    break

            if not author:
                author = "Unknown"

            normalized_messages.append(
                {
                    "author": author,
                    "timestamp": timestamp,
                    "text": text if text is not None else "",
                }
            )

        return self._format_compact_messages(normalized_messages)

    def _format_compact_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Форматирует переписку: заголовок даты + склейка подряд идущих сообщений автора"""
        if not messages:
            return ""

        lines: List[str] = []
        last_date_key: Optional[str] = None
        current_block: Optional[Dict[str, str]] = None

        for msg in messages:
            author = str(msg.get("author") or "Unknown")
            text = str(msg.get("text") or "").strip()
            dt = self._parse_datetime(msg.get("timestamp"))

            date_key = dt.strftime("%Y-%m-%d") if dt else "unknown"
            if date_key != last_date_key:
                if current_block:
                    lines.append(self._render_compact_block(current_block))
                    current_block = None

                lines.append(self._format_date_heading(dt))
                last_date_key = date_key

            time_str = dt.strftime("%H:%M") if dt else "unknown"

            if current_block and current_block["author"] == author:
                current_block["text"] = self._merge_message_text(current_block["text"], text)
            else:
                if current_block:
                    lines.append(self._render_compact_block(current_block))

                current_block = {
                    "time": time_str,
                    "author": author,
                    "text": text,
                }

        if current_block:
            lines.append(self._render_compact_block(current_block))

        return "\n".join(lines)

    def _render_compact_block(self, block: Dict[str, str]) -> str:
        return f"[{block['time']}] {block['author']}: {block['text']}".rstrip()

    def _merge_message_text(self, current_text: str, new_text: str) -> str:
        if not new_text:
            return current_text
        if not current_text:
            return new_text
        if current_text[-1] in ".!?…":
            return f"{current_text} {new_text}"
        return f"{current_text}. {new_text}"

    def _format_date_heading(self, dt: Optional[datetime]) -> str:
        if not dt:
            return "##  unknown"

        ru_months = [
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        ]
        month_name = ru_months[dt.month - 1]
        return f"##  {dt.day} {month_name} {dt.year}"

    def _parse_datetime(self, date_value: Any) -> Optional[datetime]:
        if not date_value:
            return None

        if isinstance(date_value, (int, float)):
            try:
                return datetime.fromtimestamp(date_value)
            except (ValueError, OSError):
                return None

        if isinstance(date_value, str):
            # Формат YYYY-MM-DD HH:MM(:SS)
            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(:\d{2})?", date_value)
            if date_match:
                value = f"{date_match.group(1)} {date_match.group(2)}"
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M")
                except ValueError:
                    pass

            # ISO формат
            try:
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        return None

    def _format_date(self, date_value: Any) -> str:
        """Форматирует дату в формат [YYYY-MM-DD HH:MM]"""
        if not date_value:
            return "unknown"

        # Если это число (timestamp)
        if isinstance(date_value, (int, float)):
            try:
                dt = datetime.fromtimestamp(date_value)
                return dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError):
                return str(date_value)

        # Если это строка, пытаемся распарсить
        if isinstance(date_value, str):
            # Если уже в нужном формате
            if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", date_value):
                return date_value[:16]
            
            # Пытаемся распарсить ISO формат
            try:
                dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                pass

            # Возвращаем как есть, если не смогли распарсить
            return date_value[:16] if len(date_value) >= 16 else date_value

        return str(date_value)[:16]

    def _extract_message_text(self, msg: Dict) -> str:
        """Извлекает текст из сообщения (поддерживает text_entities и text)"""
        # Попробуем text_entities (Telegram формат)
        text_entities = msg.get("text_entities", [])
        if text_entities:
            parts = []
            for entity in text_entities:
                if "text" in entity:
                    parts.append(entity["text"])
            if parts:
                return "".join(parts)

        # Переходим к обычному text
        plain_text = msg.get("text", "")
        if isinstance(plain_text, str):
            return plain_text

        return ""
