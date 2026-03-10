import { apiClient, ApiError } from "@/shared/api/client"
import { ApiErrorCodes } from "@/shared/api/types"
import { API_URL } from "@/shared/config/backend"

export type UploadResponse = {
  id?: string
  attachment_id?: string
}

export const fileApi = {
  uploadFile: async (file: File): Promise<string> => {
    const params = new URLSearchParams()
    params.append("file_name", file.name)


    try {
      const response = await apiClient.upload<UploadResponse | string>(
            `/chat/files/upload?${params.toString()}`,
            file
        )
      if (typeof response === "string") return response
      if (response.attachment_id) return response.attachment_id
      if (response.id) return response.id

      throw new Error("Не удалось получить ID файла из ответа сервера")
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === ApiErrorCodes.CHAT_ATTACHMENT_IS_TOO_BIG) {
           const maxSize = error.details?.max_size 
             ? ` (макс. ${(error.details.max_size / 1024 / 1024).toFixed(2)} MB)` 
             : ""
           throw new Error(`Файл слишком большой${maxSize}`)
        }
      }
      throw error
    }
  },

  downloadFile: async (fileId: string, fileName: string) => {
    try {
        const blob = (await apiClient.downloadBlob(`/chat/files?file_id=${fileId}`)) as Blob
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = url
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        // Delay cleanup to ensure download starts
        setTimeout(() => {
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
        }, 100)
    } catch (error) {
        console.warn("Blob download failed, falling back to direct link", error)
        // Fallback: open in new tab
        const fullUrl = `${API_URL}/chat/files?file_id=${fileId}`
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = fullUrl
        // Without download attribute support for cross-origin, this will open in new tab or navigate
        // But we want to download. Try target _blank to avoid leaving page.
        a.target = '_blank'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
    }
  }
}
