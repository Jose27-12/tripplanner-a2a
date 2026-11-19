import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { ForgotPasswordPage, LoginPage, RegisterPage } from "./pages/AuthPages";
import DashboardPage from "./pages/DashboardPage";
import AssistantPage from "./pages/AssistantPage";
import FlightsPage from "./pages/FlightsPage";
import WeatherPage from "./pages/WeatherPage";
import TripsPage from "./pages/TripsPage";
import TripDetailPage from "./pages/TripDetailPage";
import ReservationsPage from "./pages/ReservationsPage";
import PreferencesPage from "./pages/PreferencesPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/registro" element={<RegisterPage />} />
      <Route path="/recuperar" element={<ForgotPasswordPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="asistente" element={<AssistantPage />} />
        <Route path="vuelos" element={<FlightsPage />} />
        <Route path="clima" element={<WeatherPage />} />
        <Route path="viajes" element={<TripsPage />} />
        <Route path="viajes/:tripId" element={<TripDetailPage />} />
        <Route path="reservas" element={<ReservationsPage />} />
        <Route path="preferencias" element={<PreferencesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
