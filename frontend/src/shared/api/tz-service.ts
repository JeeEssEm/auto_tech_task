import { apiClient } from "@/shared/api/client"

export type PendingConflictView = {
  id: string
  scope: string
  property: string
  rationale: string
  options: string[]
}

export type PendingActionView = {
  id: string
  question: string
  options: string[]
  status: string
  created_at: string
}

export type PendingItemsResponse = {
  conflicts: PendingConflictView[]
  actions: PendingActionView[]
}

export type KnowledgeGraphFactDto = {
  id: string
  scope: string
  property: string
  value: string
  status: string
  rationale: string
  source_ids: string[]
  created_at: string
  updated_at: string
}

export type KnowledgeGraphFactsResponse = {
  facts: KnowledgeGraphFactDto[]
}

export const tzApi = {
  /** Получение статуса последней генерации */
  getGenerationStatus: async (chatId: string): Promise<{ status: string | null }> => {
    return apiClient.get(`/tz/${chatId}/generation-status`)
  },

  getPendingItems: async (chatId: string): Promise<PendingItemsResponse> => {
    return apiClient.get(`/tz/${chatId}/actions`)
  },

  getKnowledgeGraphFacts: async (chatId: string): Promise<KnowledgeGraphFactsResponse> => {
    return apiClient.get(`/tz/${chatId}/facts`)
  },

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
    blockId: string,
    instruction?: string | null,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/regenerate-block`, {
      block_id: blockId,
      instruction: instruction ?? null,
    })
  },

  /** Разрешение conflict/pending action */
  resolveConflict: async (
    chatId: string,
    actionId: string,
    resolution: string,
  ): Promise<{ status: string }> => {
    return apiClient.post(`/tz/${chatId}/resolve-conflict`, {
      action_id: actionId,
      resolution,
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
  downloadExport: async (chatId: string, exportKey: string) => {
    const endpoint = `/tz/${chatId}/export-download?${new URLSearchParams({ key: exportKey })}`
    const blob = await apiClient.downloadBlob(endpoint)
    const filename = exportKey.split("/").pop() ?? "export"

    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.style.display = "none"
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    setTimeout(() => {
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }, 100)
  },
}
