import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      toastOptions={{
        classNames: {
            success: "group-[.toaster]:!bg-green-500/10 group-[.toaster]:!text-green-700 dark:group-[.toaster]:!text-green-400 group-[.toaster]:!border-green-500/20",
            error: "group-[.toaster]:!bg-red-500/10 group-[.toaster]:!text-red-700 dark:group-[.toaster]:!text-red-400 group-[.toaster]:!border-red-500/20",
            info: "group-[.toaster]:!bg-blue-500/10 group-[.toaster]:!text-blue-700 dark:group-[.toaster]:!text-blue-400 group-[.toaster]:!border-blue-500/20",
            warning: "group-[.toaster]:!bg-orange-500/10 group-[.toaster]:!text-orange-700 dark:group-[.toaster]:!text-orange-400 group-[.toaster]:!border-orange-500/20",
        }
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
