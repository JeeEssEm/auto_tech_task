import { API_URL } from "@/shared/config/backend"
import type { ApiErrorData } from "./types"

export class ApiError extends Error {
  code: string
  details?: any

  constructor(data: ApiErrorData) {
    super(data.message)
    this.name = "ApiError"
    this.code = data.code
    this.details = data.details
  }
}

// Event to notify app about 401/403
export const authEvents = new EventTarget()

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401 || response.status === 403) {
    authEvents.dispatchEvent(new Event("unauthorized"))
    throw new Error("Сессия истекла")
  }

  const contentType = response.headers.get("content-type")
  const isJson = contentType?.includes("application/json")

  if (isJson) {
      const data = await response.json()

      if (data && typeof data === "object" && "error" in data) {
        throw new ApiError(data.error)
      }
      return data as T
  }

  // Handle text/plain or other types if successful
  if (response.ok) {
     const text = await response.text()
     // Prepare for mixed returns (quoted string or raw)
     try {
         return JSON.parse(text)
     } catch {
         return text as unknown as T
     }
  }

  if (!response.ok) {
     throw new Error(`HTTP error! status: ${response.status}`)
  }

  return {} as T
}

const fetchWithNetworkCheck = async (input: RequestInfo | URL, init?: RequestInit) => {
    try {
        return await fetch(input, init)
    } catch (error) {
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            throw new Error('Сервер временно недоступен. Попробуйте позже.')
        }
        throw error
    }
}

export const apiClient = {
  get: async <T>(endpoint: string, init?: RequestInit) => {
    const response = await fetchWithNetworkCheck(`${API_URL}${endpoint}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Important for HttpOnly cookies
      ...init
    })
    return handleResponse<T>(response)
  },

  post: async <T>(endpoint: string, body: unknown) => {
    const response = await fetchWithNetworkCheck(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      credentials: "include",
    })
    return handleResponse<T>(response)
  },

    upload: async <T>(endpoint: string, data: FormData | File) => {
        const headers: HeadersInit = {}
        let body: BodyInit

        if (data instanceof File) {
            headers["Content-Type"] = data.type || "application/octet-stream"
            body = data
        } else {
            body = data
        }

            const response = await fetchWithNetworkCheck(`${API_URL}${endpoint}`, {
              method: "POST",
              headers,
              body,
              credentials: "include",
            })
            return handleResponse<T>(response)
          },

          downloadBlob: async (endpoint: string) => {
            const response = await fetchWithNetworkCheck(`${API_URL}${endpoint}`, {
              method: "GET",
              credentials: "include",
            })

            if (response.status === 401 || response.status === 403) {
                authEvents.dispatchEvent(new Event("unauthorized"))
                throw new Error("Сессия истекла")
            }

            if (!response.ok) {
                throw new Error(`Ошибка скачивания файла: ${response.status}`)
            }

            return response.blob()
          }
        }