import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing.jsx'
import PaymentDone from './pages/PaymentDone.jsx'

// The treasurer pages are loaded only when needed, so the public page stays small and fast.
const Login = lazy(() => import('./admin/Login.jsx'))
const AdminLayout = lazy(() => import('./admin/AdminLayout.jsx'))
const Dashboard = lazy(() => import('./admin/Dashboard.jsx'))
const Members = lazy(() => import('./admin/Members.jsx'))
const Payments = lazy(() => import('./admin/Payments.jsx'))
const MemberDetail = lazy(() => import('./admin/MemberDetail.jsx'))
const PaymentDetail = lazy(() => import('./admin/PaymentDetail.jsx'))
const RecordPayment = lazy(() => import('./admin/RecordPayment.jsx'))
const RequestPayment = lazy(() => import('./admin/RequestPayment.jsx'))

export default function App() {
  return (
    <Suspense fallback={<div className="loading"><div className="spinner big" /></div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/payment/done" element={<PaymentDone />} />
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="members" element={<Members />} />
          <Route path="members/:id" element={<MemberDetail />} />
          <Route path="payments" element={<Payments />} />
          <Route path="payments/new" element={<RecordPayment />} />
          <Route path="request" element={<RequestPayment />} />
          <Route path="payments/:id" element={<PaymentDetail />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
