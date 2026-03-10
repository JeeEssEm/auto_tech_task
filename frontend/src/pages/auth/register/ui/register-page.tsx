import { useState, useEffect } from "react"
import { toast } from "sonner"
import { useNavigate } from "react-router-dom"

import { authApi } from "@/shared/api/auth-service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/app/auth-provider"

const FIELD_NAMES: Record<string, string> = {
  login: "Логин",
  firstname: "Имя",
  lastname: "Фамилия",
  middlename: "Отчество",
  email: "Email",
  password: "Пароль",
  password_confirm: "Подтверждение пароля"
}

export function RegisterPage() {
  const [lastName, setLastName] = useState("")
  const [firstName, setFirstName] = useState("")
  const [middleName, setMiddleName] = useState("")
  const [login, setLogin] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/")
    }
  }, [isAuthenticated, navigate])

  const validate = () => {
    if (login.length < 3 || login.length > 64) {
      toast.error("Логин должен быть от 3 до 64 символов")
      return false
    }
    if (firstName.length < 3 || firstName.length > 64) {
      toast.error("Имя должно быть от 3 до 64 символов")
      return false
    }
    if (lastName.length < 3 || lastName.length > 64) {
      toast.error("Фамилия должна быть от 3 до 64 символов")
      return false
    }
    if (middleName && (middleName.length < 3 || middleName.length > 64)) {
      toast.error("Отчество должно быть от 3 до 64 символов")
      return false
    }
    if (password.length < 8 || password.length > 128) {
       toast.error("Пароль должен быть от 8 до 128 символов")
       return false
    }
    if (password !== confirmPassword) {
      toast.error("Пароли не совпадают")
      return false
    }
    // Basic email regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
        toast.error("Введите корректный email")
        return false
    }
    return true
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!validate()) return

    setIsLoading(true)
    try {
      const result = await authApi.register({
        lastname: lastName,
        firstname: firstName,
        middlename: middleName || undefined,
        login,
        email,
        password,
        password_confirm: confirmPassword,

      })
      toast.success(result.message)
      if (!result.need_to_activate) {
        navigate("/chats/new")
      } else {
        // Maybe redirect to a "check email" page or login
        navigate("/auth/login")
      }
    } catch (error: any) {
        let message = error.message || "Ошибка регистрации"

        // Attempt to parse 'Field required' type errors
        if (message.toLowerCase().includes("field required") && error.details?.field) {
            const fieldName = error.details.field
            const translatedField = FIELD_NAMES[fieldName] || fieldName
            message = `Поле "${translatedField}" обязательно для заполнения`
        }

        toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Регистрация</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Фамилия</label>
                <Input
                  placeholder="Ветрова"
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Имя</label>
                <Input
                  placeholder="Анна"
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Отчество</label>
                <Input
                  placeholder="Андреевна"
                  value={middleName}
                  onChange={(event) => setMiddleName(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Логин</label>
              <Input
                placeholder="annav"
                value={login}
                onChange={(event) => setLogin(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Пароль</label>
              <Input
                type="password"
                placeholder="Придумайте пароль"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Подтверждение пароля</label>
              <Input
                type="password"
                placeholder="Повторите пароль"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </div>
            <Button className="w-full" type="submit" disabled={isLoading}>
              {isLoading ? "Создаем..." : "Создать аккаунт"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
