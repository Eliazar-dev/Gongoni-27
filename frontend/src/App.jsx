import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Register from './pages/Register.jsx'
import ThankYou from './pages/ThankYou.jsx'

// The treasurer pages are loaded only when needed, so the registration page stays small and fast.
const Login = lazy(() => import('./admin/Login.jsx'))
const AdminLayout = lazy(() => import('./admin/AdminLayout.jsx'))
const Dashboard = lazy(() => import('./admin/Dashboard.jsx'))
const Members = lazy(() => import('./admin/Members.jsx'))
const Payments = lazy(() => import('./admin/Payments.jsx'))

export default function App() {
  return (
    <Suspense fallback={<div className="loading"><div className="spinner big" /></div>}>
      <Routes>
        <Route path="/" element={<Register />} />
        <Route path="/thank-you" element={<ThankYou />} />
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="members" element={<Members />} />
          <Route path="payments" element={<Payments />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
