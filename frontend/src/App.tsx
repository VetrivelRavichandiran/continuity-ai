import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Dashboard from './pages/Dashboard'
import ProjectOverview from './pages/ProjectOverview'
import DocumentsPage from './pages/DocumentsPage'
import KnowledgePage from './pages/KnowledgePage'
import TimelinePage from './pages/TimelinePage'
import ConflictsPage from './pages/ConflictsPage'
import AssistantPage from './pages/AssistantPage'
import HandoverPage from './pages/HandoverPage'
import AuditPage from './pages/AuditPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path=":projectId" element={<ProjectOverview />} />
          <Route path=":projectId/documents" element={<DocumentsPage />} />
          <Route path=":projectId/knowledge" element={<KnowledgePage />} />
          <Route path=":projectId/timeline" element={<TimelinePage />} />
          <Route path=":projectId/conflicts" element={<ConflictsPage />} />
          <Route path=":projectId/assistant" element={<AssistantPage />} />
          <Route path=":projectId/handover" element={<HandoverPage />} />
          <Route path=":projectId/audit" element={<AuditPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}