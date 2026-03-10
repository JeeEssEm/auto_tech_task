import { useCallback, useRef, useState } from "react"

import type { GenerationStatusType, WsEventMap } from "@/shared/ws/types"
import type { GenerationStep } from "../lib/types"

const COMPLETE_DISMISS_DELAY = 1500

const STEP_LABELS: Record<string, string> = {
  ANALYZING_DATA: "Анализ данных",
  BUILDING_GRAPH: "Построение графа знаний",
  MERGING_DATA_SOURCES: "Объединение источников",
  VERIFYING_DATA: "Проверка данных",
  INGESTING: "Обработка источников",
  COMPILING: "Сборка документа",
  extracting: "Извлечение данных",
  analyzing: "Анализ структуры",
  conflict_check: "Проверка противоречий",
  ingest_done: "Источники обработаны",
  compiling: "Сборка ТЗ",
  filling_sections: "Заполнение разделов",
  validating: "Валидация",
  compile_done: "Сборка завершена",
  regenerating: "Перегенерация",
  applying_comment: "Применение комментария",
  generating_block: "Генерация блока",
}

export function useGenerationStatus() {
  const [steps, setSteps] = useState<GenerationStep[]>([])
  const [isThinking, setIsThinking] = useState(false)
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleGenerationStatus = useCallback((data: WsEventMap["GENERATION_STATUS"]) => {
    setIsThinking(true)

    // Clear any pending dismiss timer (in case answer hasn't arrived yet)
    if (dismissTimer.current) {
      clearTimeout(dismissTimer.current)
      dismissTimer.current = null
    }

    setSteps(prev => {
      // If this status already exists, skip
      if (prev.some(s => s.status === data.status)) return prev

      // Mark all previous steps as done, add new as active
      const updated = prev.map(s => ({ ...s, state: "done" as const }))
      const label = data.step || STEP_LABELS[data.status] || data.status
      return [...updated, { status: data.status, label, state: "active" as const }]
    })
  }, [])

  // Called when LLM_ANSWER arrives — mark all done, then dismiss after delay
  const completeGeneration = useCallback(() => {
    setSteps(prev => prev.map(s => ({ ...s, state: "done" as const })))

    dismissTimer.current = setTimeout(() => {
      setSteps([])
      setIsThinking(false)
      dismissTimer.current = null
    }, COMPLETE_DISMISS_DELAY)
  }, [])

  // Reset on chat change
  const resetGeneration = useCallback(() => {
    if (dismissTimer.current) {
      clearTimeout(dismissTimer.current)
      dismissTimer.current = null
    }
    setSteps([])
    setIsThinking(false)
  }, [])

  return { steps, isThinking, handleGenerationStatus, completeGeneration, resetGeneration }
}
