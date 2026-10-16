import { createBrowserRouter, Navigate } from 'react-router'

import { AppLayout } from '@/components/layout/AppLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'
import { DeltaMatroidPage } from '@/pages/DeltaMatroidPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PlaceholderPage } from '@/pages/PlaceholderPage'
import { WorkspaceHome } from '@/pages/WorkspaceHome'

/*
 * Every screen has its own URL, so the back button and shared links work.
 * The workspace (tree on the left) is a nested layout: /workspace and
 * /workspace/:deltaMatroidId share it; /new and /isomorphism do not.
 */
export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/workspace" replace /> },
      {
        path: 'workspace',
        element: <WorkspaceLayout />,
        children: [
          { index: true, element: <WorkspaceHome /> },
          { path: ':deltaMatroidId', element: <DeltaMatroidPage /> },
        ],
      },
      { path: 'new', element: <PlaceholderPage titleKey="nav.new" block="3c" /> },
      {
        path: 'isomorphism',
        element: <PlaceholderPage titleKey="nav.isomorphism" block="v1+" />,
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      { path: 'login', element: <PlaceholderPage titleKey="auth.login" block="3b" /> },
      { path: 'register', element: <PlaceholderPage titleKey="auth.register" block="3b" /> },
      { path: 'forgot-password', element: <PlaceholderPage titleKey="auth.forgot" block="3b" /> },
      { path: 'reset-password', element: <PlaceholderPage titleKey="auth.reset" block="3b" /> },
      { path: 'verify-email', element: <PlaceholderPage titleKey="auth.verify" block="3b" /> },
    ],
  },
])
