import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import RequireAuth from "./components/auth/RequireAuth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import LibraryPage from "./pages/LibraryPage";
import FamilyPage from "./pages/FamilyPage";
import TimelinePage from "./pages/TimelinePage";
import StoriesPage from "./pages/StoriesPage";
import StoryReaderPage from "./pages/StoryReaderPage";
import VideosPage from "./pages/VideosPage";
import GeneratePage from "./pages/GeneratePage";
import TasksPage from "./pages/TasksPage";
import SettingsPage from "./pages/SettingsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        <Route path="/"            element={<DashboardPage />} />
        <Route path="/library"     element={<LibraryPage />} />
        <Route path="/family"      element={<FamilyPage />} />
        <Route path="/timeline"    element={<TimelinePage />} />
        <Route path="/stories"     element={<StoriesPage />} />
        <Route path="/stories/:id" element={<StoryReaderPage />} />
        <Route path="/videos"      element={<VideosPage />} />
        <Route path="/generate"    element={<GeneratePage />} />
        <Route path="/tasks"       element={<TasksPage />} />
        <Route path="/settings"    element={<SettingsPage />} />
      </Route>

      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*"    element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
