import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { getMe, login } from "./api/client";
import AppLayout from "./components/AppLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminDocuments from "./pages/admin/AdminDocuments";
import AdminEmployees from "./pages/admin/AdminEmployees";
import AdminPaystubs from "./pages/admin/AdminPaystubs";
import AdminRequests from "./pages/admin/AdminRequests";
import AdminSettings from "./pages/admin/AdminSettings";
import Documents from "./pages/Documents";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Paystubs from "./pages/Paystubs";
import Profile from "./pages/Profile";
import ResetPassword from "./pages/ResetPassword";
import Support from "./pages/Support";

export type User = {
  id: number;
  email: string;
  legal_first_name: string;
  legal_last_name: string;
  preferred_name?: string | null;
  job_title: string;
  department: string;
  hire_date: string;
  phone?: string | null;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
  role: "EMPLOYEE" | "ADMIN";
  employment_status: "ACTIVE" | "FORMER_EMPLOYEE";
  is_active: boolean;
};

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("kc_token"));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    getMe()
      .then((data) => setUser(data))
      .catch(() => {
        localStorage.removeItem("kc_token");
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const handleLogin = async (email: string, password: string) => {
    const data = await login(email, password);
    localStorage.setItem("kc_token", data.access_token);
    setToken(data.access_token);
  };

  const handleLogout = () => {
    localStorage.removeItem("kc_token");
    setToken(null);
    setUser(null);
  };

  if (loading) {
    return <div className="content">Loading Kyronix Core...</div>;
  }

  const canAccessAdmin = !!user && user.role === "ADMIN" && user.employment_status === "ACTIVE";

  return (
    <Routes>
      <Route
        path="/login"
        element={
          user ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
        }
      />
      <Route
        path="/reset"
        element={user ? <Navigate to="/" replace /> : <ResetPassword />}
      />
      <Route
        element={
          user ? (
            <AppLayout user={user} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      >
        <Route path="/" element={<Home user={user as User} />} />
        <Route path="/paystubs" element={<Paystubs />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/profile" element={<Profile user={user as User} />} />
        <Route path="/support" element={<Support />} />
        <Route
          path="/admin"
          element={canAccessAdmin ? <AdminDashboard /> : <Navigate to="/" replace />}
        />
        <Route
          path="/admin/employees"
          element={canAccessAdmin ? <AdminEmployees /> : <Navigate to="/" replace />}
        />
        <Route
          path="/admin/paystubs"
          element={canAccessAdmin ? <AdminPaystubs /> : <Navigate to="/" replace />}
        />
        <Route
          path="/admin/documents"
          element={canAccessAdmin ? <AdminDocuments /> : <Navigate to="/" replace />}
        />
        <Route
          path="/admin/requests"
          element={canAccessAdmin ? <AdminRequests /> : <Navigate to="/" replace />}
        />
        <Route
          path="/admin/settings"
          element={canAccessAdmin ? <AdminSettings /> : <Navigate to="/" replace />}
        />
      </Route>
      <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
    </Routes>
  );
}
