import { apiClient, ApiError } from "@/shared/api/client"
import { ApiErrorCodes } from "@/shared/api/types"

type AuthResult = {
  success: boolean
  message: string
  need_to_activate?: boolean
}

type LoginPayload = {
  email_or_login: string
  password: string
}

type RegisterPayload = {
  email: string
  login: string
  firstname: string
  lastname: string
  middlename?: string
  password: string
  password_confirm: string
}

type RecoverPayload = {
  email: string
}

type UserProfile = {
  id: number
  email: string
  login: string
  firstname: string
  middlename: string
  lastname: string
  role: string
  is_active: boolean
  subscription_tier: string
}

type UsagePeriod = {
  generate_tz: number
  parsed_files: number
}

type UsageLimits = {
  generate_tz: number
  parse_files: number
  create_chat: number
}

type UsageInfo = {
  tier: string
  today: UsagePeriod
  total_chats: number
  limits: UsageLimits
}

export const authApi = {
  login: async (payload: LoginPayload): Promise<AuthResult> => {
    try {
      await apiClient.post("/auth/login", payload)
      return { success: true, message: "Вход выполнен успешно" }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === ApiErrorCodes.AUTH_USER_WRONG_PASSWORD_OR_LOGIN) {
            throw new Error("Неверный логин или пароль")
        }
        if (error.code === ApiErrorCodes.AUTH_USER_NOT_FOUND) {
            throw new Error("Пользователь не найден")
        }
      }
      throw error
    }
  },

  register: async (payload: RegisterPayload): Promise<AuthResult> => {
    try {
      const response = await apiClient.post<{ need_to_activate?: boolean }>("/auth/signup", payload)
      return { 
        success: true, 
        message: response.need_to_activate 
          ? "Аккаунт создан. Проверьте почту для подтверждения." 
          : "Регистрация успешна",
        need_to_activate: response.need_to_activate
      }
    } catch (error) {
       if (error instanceof ApiError) {
         if (error.code === ApiErrorCodes.AUTH_USER_ALREADY_EXISTS) {
           throw new Error("Пользователь с таким email или логином уже существует")
         }
         if (error.code === ApiErrorCodes.VALIDATION_ERROR) {
            throw new Error(error.message || "Ошибка валидации данных")
         }
       }
       throw error
    }
  },

  recover: async (payload: RecoverPayload): Promise<AuthResult> => {
      // Mock for now
      await new Promise(r => setTimeout(r, 500))
      return { success: true, message: `Инструкция отправлена на ${payload.email}` }
  },

  logout: async () => {
      await apiClient.post("/auth/logout", {})
  },

  getMe: async (): Promise<UserProfile> => {
      return await apiClient.get<UserProfile>("/auth/me")
  },

  getUsage: async (): Promise<UsageInfo> => {
      return await apiClient.get<UsageInfo>("/auth/me/usage")
  },
}

export { ApiError }
export type { AuthResult, LoginPayload, RegisterPayload, RecoverPayload, UserProfile, UsageInfo, UsagePeriod, UsageLimits }
