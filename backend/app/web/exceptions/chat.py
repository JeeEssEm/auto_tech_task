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
