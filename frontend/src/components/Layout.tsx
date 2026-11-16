import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/properties" className="brand">
          Lease Abstraction Tool
        </Link>
        <div className="header-right">
          {user && (
            <span className="muted">
              {user.email} ({user.role})
            </span>
          )}
          <button className="link-button" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="app-content">{children}</main>
    </div>
  );
}
