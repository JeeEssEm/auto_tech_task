import { apiClient } from "@/shared/api/client"
import { API_URL } from "@/shared/config/backend"

export const tzApi = {
  /** Запуск полного пайплайна первичной генерации */
  runFullPipeline: async (
    chatId: string,
    attachmentIds: string[],
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/generate`, {
      attachment_ids: attachmentIds,
    })
  },

  /** Обновление ТЗ: новые файлы и/или комментарий */
  updateTZ: async (
    chatId: string,
    newAttachmentIds: string[],
    comment: string | null,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/update`, {
      new_attachment_ids: newAttachmentIds,
      comment,
    })
  },

  /** Перегенерация конкретного блока */
  regenerateBlock: async (
    chatId: string,
    fieldPath: string,
    instruction?: string | null,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/regenerate-block`, {
      field_path: fieldPath,
      instruction: instruction ?? null,
    })
  },

  /** Генерация кастомного/пустого блока */
  generateCustomBlock: async (
    chatId: string,
    fieldPath: string,
    customTopic: string,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/generate-block`, {
      field_path: fieldPath,
      custom_topic: customTopic,
    })
  },

  /** Ручное редактирование блока */
  manualEditBlock: async (
    chatId: string,
    fieldPath: string,
    value: unknown,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/manual-edit`, {
      field_path: fieldPath,
      value,
    })
  },

  /** Обновление пользовательских подпунктов секции */
  updateCustomSections: async (
    chatId: string,
    sectionKey: string,
    sections: { id: string; title: string; content: string; children: unknown[] }[],
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/update-custom-sections`, {
      section_key: sectionKey,
      sections,
    })
  },

  /** Запуск экспорта ТЗ */
  exportTZ: async (
    chatId: string,
    resultKey: string,
    format: "markdown" | "word" | "pdf",
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/export`, {
      result_key: resultKey,
      format,
    })
  },

  /** Скачивание экспортированного файла */
  downloadExport: (chatId: string, exportKey: string) => {
    const url = `${API_URL}/tz/${chatId}/export-download?${new URLSearchParams({ key: exportKey })}`
    const a = document.createElement("a")
    a.style.display = "none"
    a.href = url
    a.download = exportKey.split("/").pop() ?? "export"
    document.body.appendChild(a)
    a.click()
    setTimeout(() => document.body.removeChild(a), 100)
  },
}
