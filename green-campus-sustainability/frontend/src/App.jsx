import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import {
  Leaf, LayoutDashboard, Zap, Droplets, Trash2, Wind,
  Search, ClipboardList, ChevronRight, CheckSquare,
  Database, FileText, Settings,
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import AuditPage from './pages/AuditPage';
import ElectricityPage from './pages/ElectricityPage';
import WaterPage from './pages/WaterPage';
import WastePage from './pages/WastePage';
import CarbonPage from './pages/CarbonPage';
import FindingsPage from './pages/FindingsPage';
import ActionsPage from './pages/ActionsPage';
import VerificationPage from './pages/VerificationPage';
import DatasetsPage from './pages/DatasetsPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

const NAV = [
  { path: '/',            icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/audit',       icon: Search,          label: 'Run Audit' },
  { path: '/electricity', icon: Zap,             label: 'Electricity' },
  { path: '/water',       icon: Droplets,        label: 'Water' },
  { path: '/waste',       icon: Trash2,          label: 'Waste' },
  { path: '/carbon',      icon: Wind,            label: 'Carbon' },
  { path: '/findings',    icon: ClipboardList,   label: 'Findings' },
  { path: '/actions',     icon: ChevronRight,    label: 'Actions' },
  { path: '/verification',icon: CheckSquare,     label: 'Verification' },
  { path: '/datasets',    icon: Database,        label: 'Datasets' },
  { path: '/reports',     icon: FileText,        label: 'Reports' },
  { path: '/settings',    icon: Settings,        label: 'Settings' },
];

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', backgroundColor: '#f9fafb' }}>
        {/* Sidebar */}
        <aside style={{
          width: '220px', flexShrink: 0,
          background: 'white', borderRight: '1px solid #e5e7eb',
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid #f3f4f6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{
                width: 32, height: 32, borderRadius: '0.5rem',
                background: '#16a34a', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Leaf size={18} color="white" />
              </div>
              <div>
                <p style={{ fontSize: '0.8rem', fontWeight: 700, lineHeight: 1.2, margin: 0 }}>Green Campus</p>
                <p style={{ fontSize: '0.7rem', color: '#6b7280', margin: 0 }}>Sustainability Auditor</p>
              </div>
            </div>
          </div>

          <nav style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
            {NAV.map(({ path, icon: Icon, label }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center', gap: '0.6rem',
                  padding: '0.45rem 0.75rem', borderRadius: '0.5rem',
                  fontSize: '0.82rem', fontWeight: 500, textDecoration: 'none',
                  marginBottom: '0.1rem',
                  color: isActive ? '#16a34a' : '#6b7280',
                  background: isActive ? '#f0fdf4' : 'transparent',
                })}
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div style={{ padding: '0.75rem', borderTop: '1px solid #f3f4f6', textAlign: 'center' }}>
            <p style={{ fontSize: '0.65rem', color: '#9ca3af', margin: 0 }}>v1.0.0 · Zero-cost · Local</p>
          </div>
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, overflowY: 'auto' }}>
          <Routes>
            <Route path="/"             element={<Dashboard />} />
            <Route path="/audit"        element={<AuditPage />} />
            <Route path="/electricity"  element={<ElectricityPage />} />
            <Route path="/water"        element={<WaterPage />} />
            <Route path="/waste"        element={<WastePage />} />
            <Route path="/carbon"       element={<CarbonPage />} />
            <Route path="/findings"     element={<FindingsPage />} />
            <Route path="/actions"      element={<ActionsPage />} />
            <Route path="/verification" element={<VerificationPage />} />
            <Route path="/datasets"     element={<DatasetsPage />} />
            <Route path="/reports"      element={<ReportsPage />} />
            <Route path="/settings"     element={<SettingsPage />} />
            <Route path="*"             element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
