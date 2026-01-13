import { NavLink, Outlet } from "react-router-dom";

import type { User } from "../App";
import Footer from "./Footer";

type Props = {
  user: User;
  onLogout: () => void;
};

const employeeNav = [
  { to: "/", label: "Home" },
  { to: "/paystubs", label: "Paystubs" },
  { to: "/documents", label: "Documents" },
  { to: "/profile", label: "Profile" },
  { to: "/support", label: "Support" },
];

const adminNav = [
  { to: "/admin", label: "Admin Overview" },
  { to: "/admin/employees", label: "Employees" },
  { to: "/admin/paystubs", label: "Paystubs" },
  { to: "/admin/documents", label: "Documents" },
  { to: "/admin/requests", label: "Requests" },
  { to: "/admin/settings", label: "Settings" },
];

export default function AppLayout({ user, onLogout }: Props) {
  const isAdmin = user.role === "ADMIN" && user.employment_status === "ACTIVE";

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand">
          <h1>Kyronix Core</h1>
          <span>Employee access to pay, documents, and records</span>
        </div>
        <div className="row" style={{ alignItems: "center" }}>
          <span className="pill">{user.role}</span>
          {user.employment_status === "FORMER_EMPLOYEE" && (
            <span className="pill">{"Former Employee \u2022 Read-only"}</span>
          )}
          <button className="button secondary" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <nav className="nav-bar">
        <div className="nav-group">
          {employeeNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
        {isAdmin && (
          <div className="nav-group">
            {adminNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/admin"}
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        )}
      </nav>

      <main className="content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
