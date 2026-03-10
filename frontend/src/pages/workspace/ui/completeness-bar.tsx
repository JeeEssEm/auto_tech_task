import { cn } from "@/lib/utils"
import type { WorkspaceProject } from "../lib/types"

type CompletenessBarProps = {
  project: WorkspaceProject
}

export function CompletenessBar({ project }: CompletenessBarProps) {
  return (
    <div className="flex items-center gap-4 px-1 text-xs text-muted-foreground">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden max-w-[200px]">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              project.completeness >= 80 ? "bg-emerald-500" :
              project.completeness >= 40 ? "bg-primary" : "bg-amber-500",
            )}
            style={{ width: `${project.completeness}%` }}
          />
        </div>
        <span className="whitespace-nowrap font-medium">
          {project.completeness}%
        </span>
      </div>
      <span className="hidden sm:inline">
        Разделов: {project.sectionsFilled}/{project.sectionsTotal}
      </span>
      <span className="hidden md:inline">
        Требований: {project.requirementsCount}
      </span>
      <span className="hidden lg:inline">
        Сущностей: {project.entitiesCount}
      </span>
      {project.openQuestions > 0 && (
        <span className="text-amber-500 hidden sm:inline">
          ⚠ {project.openQuestions} открыт. вопросов
        </span>
      )}
    </div>
  )
}
