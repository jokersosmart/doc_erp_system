import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";

import LoginPage from "@/pages/LoginPage";
import { ProjectDashboardPage } from "@/pages/ProjectDashboardPage";
import { WizardContainer } from "@/components/wizard/WizardContainer";

export default function App(): JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/projects/new" element={<WizardContainer />} />
        <Route path="/projects/:projectId/wizard" element={<WizardContainer />} />
        <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
