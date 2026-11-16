import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { PropertiesPage } from "./pages/PropertiesPage";
import { PropertyLeasesPage } from "./pages/PropertyLeasesPage";
import { LeaseDetailPage } from "./pages/LeaseDetailPage";
import { ProtectedRoute } from "./components/ProtectedRoute";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/properties"
        element={
          <ProtectedRoute>
            <PropertiesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/properties/:propertyId"
        element={
          <ProtectedRoute>
            <PropertyLeasesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/leases/:leaseId"
        element={
          <ProtectedRoute>
            <LeaseDetailPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/properties" replace />} />
    </Routes>
  );
}

export default App;
