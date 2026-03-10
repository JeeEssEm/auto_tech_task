import { AlertTriangle, User } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { Stakeholder } from "../../lib/types"

type StakeholdersTabProps = {
  stakeholders: Stakeholder[]
}

export function StakeholdersTab({ stakeholders }: StakeholdersTabProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-sm font-medium">{stakeholders.length} заинтересованных лиц</span>
      </div>

      <div className="flex-1 overflow-y-auto chat-scrollbar p-4">
        <div className="space-y-3">
          {stakeholders.map(sh => (
            <Card key={sh.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                    <User className="size-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">{sh.name}</h3>
                    <p className="text-xs text-muted-foreground">{sh.role}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <AlertTriangle className="size-3 text-amber-500" />
                      <span className="text-xs font-medium text-muted-foreground">Интересы и риски</span>
                    </div>
                    <div className="space-y-1">
                      {sh.concerns.map((concern, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                          <span className="text-muted-foreground mt-0.5">•</span>
                          <span>{concern}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 pt-2 border-t border-border/50">
                    <span className="text-[11px] text-muted-foreground">Связанные требования:</span>
                    {sh.relatedRequirements.map(id => (
                      <Badge key={id} variant="outline" className="text-[10px]">{id}</Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
