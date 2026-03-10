import { createContext, useContext, useEffect, useState } from "react"
import { authEvents } from "@/shared/api/client"

interface AuthContextType {
  isAuthenticated: boolean
  login: () => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem("isAuth") === "true"
  })

  useEffect(() => {
    // Listen for 401 events from API client
    const handleUnauthorized = () => {
      logout()
    }

    authEvents.addEventListener("unauthorized", handleUnauthorized)
    return () => {
        authEvents.removeEventListener("unauthorized", handleUnauthorized)
    }
  }, [])

  const login = () => {
    setIsAuthenticated(true)
    localStorage.setItem("isAuth", "true")
  }

  const logout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem("isAuth")
    // Optionally call api logout if this was triggered by user action, 
    // but this function might be called by 401 too.
    // If called by user, they usually call authApi.logout() first then this.
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
