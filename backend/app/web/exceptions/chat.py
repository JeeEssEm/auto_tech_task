from fastapi import status

from backend.app.web.exceptions.base_exception import BaseWebException


class AttachmentFileIsTooBig(BaseWebException):
    def __init__(self, max_size: float):
        super().__init__(
            code="CHAT_ATTACHMENT_IS_TOO_BIG",
            message=f"Attachment file size exceeds limit: {max_size}",
            detail={
                "max_size": max_size
            },
            http_code=status.HTTP_404_NOT_FOUND
        )


class AttachmentNotFound(BaseWebException):
    def __init__(self, attachment_id: str):
        super().__init__(
            code="CHAT_ATTACHMENT_DOES_NOT_EXIST",
            message=f"Attachment with id=`{attachment_id}` not found",
            http_code=status.HTTP_404_NOT_FOUND
        )


class NotEnoughRightsToCheckAttachment(BaseWebException):
    def __init__(self, attachment_id: str):
        super().__init__(
            code="CHAT_NOT_ENOUGH_RIGHTS_TO_CHECK_THIS_ATTACHMENT",
            message=f"You cannot read attachment with id=`{attachment_id}`",
            http_code=status.HTTP_403_FORBIDDEN
        )


class CannotCreateEmptyChat(BaseWebException):
    def __init__(self):
        super().__init__(
            code="CHAT_CANNOT_BE_EMPTY",
            message=f"Cannot create new chat without any message and attachments",
            http_code=status.HTTP_400_BAD_REQUEST
        )


class MessageNotFound(BaseWebException):
    def __init__(self, msg_id: str):
        super().__init__(
            code="CHAT_MESSAGE_NOT_FOUND",
            message=f"Message with id={msg_id} not found",
            http_code=status.HTTP_404_NOT_FOUND
        )


class ChatNotFound(BaseWebException):
    def __init__(self, chat_id: int):
        super().__init__(
            code="CHAT_NOT_FOUND",
            message=f"Chat with id={chat_id} not found",
            http_code=status.HTTP_404_NOT_FOUND
        )


class AttachmentFieldIsMissing(BaseWebException):
    def __init__(self, field: str):
        super().__init__(
            code="CHAT_ATTACHMENT_FIELD_IS_MISSING",
            message=f"Attachment field {field} is missing",
            http_code=status.HTTP_400_BAD_REQUEST
        )
