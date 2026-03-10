export type ApiErrorDetail = {
  field?: string
  type?: string
}

export type ApiErrorData = {
  code: string
  message: string
  details?: ApiErrorDetail
}

export type ApiResponse<T> = T | { error: ApiErrorData }

export const ApiErrorCodes = {
  AUTH_USER_ALREADY_EXISTS: "AUTH_USER_ALREADY_EXISTS",
  AUTH_USER_NOT_FOUND: "AUTH_USER_NOT_FOUND",
  AUTH_USER_WRONG_PASSWORD_OR_LOGIN: "AUTH_USER_WRONG_PASSWORD_OR_LOGIN",
  AUTH_USER_SESSION_NOT_FOUND: "AUTH_USER_SESSION_NOT_FOUND",
  AUTH_USER_SESSION_EXPIRED: "AUTH_USER_SESSION_EXPIRED",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  CHAT_ATTACHMENT_IS_TOO_BIG: "CHAT_ATTACHMENT_IS_TOO_BIG",
} as const
