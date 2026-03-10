import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppLayout } from "@/widgets/layout/app-layout"
import { AuthLayout } from "@/widgets/layout/auth-layout"
import { LoginPage } from "@/pages/auth/login/ui/login-page"
import { RecoverPage } from "@/pages/auth/recover/ui/recover-page"
import { RegisterPage } from "@/pages/auth/register/ui/register-page"
import { ChatCreatePage } from "@/pages/chat-create/ui/chat-create-page"
import { ChatPage } from "@/pages/chat/ui/chat-page"
import { LandingPage } from "@/pages/landing/ui/landing-page"
import { ProfilePage } from "@/pages/profile/ui/profile-page"
import { WorkspacePage } from "@/pages/workspace/ui/workspace-page"
import { Toaster } from "@/components/ui/sonner"
import { AuthProvider } from "./auth-provider"

export default function App() {
  return (
    <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route index element={<LandingPage />} />
            <Route element={<AuthLayout />}>
              <Route path="auth/login" element={<LoginPage />} />
              <Route path="auth/register" element={<RegisterPage />} />
              <Route path="auth/recover" element={<RecoverPage />} />
            </Route>
            <Route element={<AppLayout />}>
              <Route path="profile" element={<ProfilePage />} />
              <Route path="chats/new" element={<ChatCreatePage />} />
              <Route path="chats/:id" element={<ChatPage />} />
              <Route path="workspace/:id" element={<WorkspacePage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster />
        </BrowserRouter>
    </AuthProvider>
  )
}
