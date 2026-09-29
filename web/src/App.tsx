import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { PlanPage } from './pages/PlanPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<PlanPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<PlanPage />} />
      </Route>
    </Routes>
  );
}
