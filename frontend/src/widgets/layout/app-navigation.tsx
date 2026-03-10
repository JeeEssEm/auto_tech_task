import { Link, useLocation } from "react-router-dom"

import { Button } from "@/components/ui/button"

const links = [
  { to: "/", label: "Лендинг" },
  { to: "/chats/new", label: "Новый чат" },
]

export function AppNavigation() {
  const location = useLocation()

  return (
    <nav className="flex items-center gap-2">
      {links.map((link) => {
        const isActive = location.pathname === link.to
        return (
          <Button
            key={link.to}
            asChild
            variant={isActive ? "default" : "ghost"}
            size="sm"
          >
            <Link to={link.to}>{link.label}</Link>
          </Button>
        )
      })}
    </nav>
  )
}
