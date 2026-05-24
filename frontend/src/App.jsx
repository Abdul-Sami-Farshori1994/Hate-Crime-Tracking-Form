import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import {
  adminLoginPath,
  adminPrefix,
  formLoginPath,
  formPagePath,
  formPrefix,
  thankYouPath,
} from './paths'
import LoginPage from './pages/LoginPage'
import FormPage from './pages/FormPage'
import ThankYouPage from './pages/ThankYouPage'
import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import NotFoundPage from './pages/NotFoundPage'

const FormPreview = lazy(() => import('./pages/admin/FormPreview'))
const FormEditor = lazy(() => import('./pages/admin/FormEditor'))
const Responses = lazy(() => import('./pages/admin/Responses'))
const ResponseDetail = lazy(() => import('./pages/admin/ResponseDetail'))
const Analytics = lazy(() => import('./pages/admin/Analytics'))
const CredentialManager = lazy(() => import('./pages/admin/CredentialManager'))
const DataActions = lazy(() => import('./pages/admin/DataActions'))
const AuditLog = lazy(() => import('./pages/admin/AuditLog'))

function AdminFallback() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
      Loading…
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path={formLoginPath()} element={<LoginPage />} />
      <Route path={formPagePath()} element={<FormPage />} />
      <Route path={thankYouPath()} element={<ThankYouPage />} />

      <Route path={adminLoginPath()} element={<AdminLogin />} />
      <Route path={`${adminPrefix}/dashboard`} element={<AdminDashboard />}>
        <Route index element={<Navigate to="preview" replace />} />
        <Route
          path="preview"
          element={
            <Suspense fallback={<AdminFallback />}>
              <FormPreview />
            </Suspense>
          }
        />
        <Route
          path="editor"
          element={
            <Suspense fallback={<AdminFallback />}>
              <FormEditor />
            </Suspense>
          }
        />
        <Route
          path="responses"
          element={
            <Suspense fallback={<AdminFallback />}>
              <Responses />
            </Suspense>
          }
        />
        <Route
          path="responses/:sessionId"
          element={
            <Suspense fallback={<AdminFallback />}>
              <ResponseDetail />
            </Suspense>
          }
        />
        <Route
          path="analytics"
          element={
            <Suspense fallback={<AdminFallback />}>
              <Analytics />
            </Suspense>
          }
        />
        <Route
          path="data-actions"
          element={
            <Suspense fallback={<AdminFallback />}>
              <DataActions />
            </Suspense>
          }
        />
        <Route
          path="credentials"
          element={
            <Suspense fallback={<AdminFallback />}>
              <CredentialManager />
            </Suspense>
          }
        />
        <Route
          path="audit"
          element={
            <Suspense fallback={<AdminFallback />}>
              <AuditLog />
            </Suspense>
          }
        />
      </Route>

      <Route path="/" element={<NotFoundPage />} />
      <Route path="/form" element={<NotFoundPage />} />
      <Route path="/thank-you" element={<NotFoundPage />} />
      <Route path="/admin" element={<NotFoundPage />} />
      <Route path="/admin/*" element={<NotFoundPage />} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
