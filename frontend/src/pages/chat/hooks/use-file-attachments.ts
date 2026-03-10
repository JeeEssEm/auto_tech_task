import React, { useRef, useState } from "react"
import { toast } from "sonner"

import { fileApi } from "@/shared/api/file-service"
import type { FileItem } from "../lib/types"

type UseFileAttachmentsOptions = {
  onFileUploaded?: (attachmentId: string, fileName: string) => void
}

export function useFileAttachments(options?: UseFileAttachmentsOptions) {
  const [files, setFiles] = useState<FileItem[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadFile = async (file: File) => {
    const newItem: FileItem = { file, status: "uploading" }
    setFiles(prev => [...prev, newItem])

    try {
      const uploadedId = await fileApi.uploadFile(file)
      options?.onFileUploaded?.(uploadedId, file.name)
      setFiles(prev =>
        prev.map(item =>
          item.file === file ? { ...item, status: "success", id: uploadedId } : item,
        ),
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      setFiles(prev =>
        prev.map(item =>
          item.file === file ? { ...item, status: "error", error: message } : item,
        ),
      )
      toast.error(`Ошибка загрузки ${file.name}: ${message}`)
    }
  }

  const handleAttachClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      Array.from(event.target.files).forEach(file => uploadFile(file))
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const removeFile = (fileItem: FileItem) => {
    setFiles(prev => prev.filter(f => f !== fileItem))
  }

  const clearFiles = () => setFiles([])

  return { files, fileInputRef, handleAttachClick, handleFileChange, removeFile, clearFiles }
}
