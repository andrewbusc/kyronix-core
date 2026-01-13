import { Link } from "react-router-dom";

export default function AdminDashboard() {
  return (
    <>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Admin Overview</h2>
        <p>Manage employees, paystubs, documents, and requests from one place.</p>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Quick actions</h3>
        <div className="row">
          <Link className="button secondary" to="/admin/employees">
            Employees
          </Link>
          <Link className="button secondary" to="/admin/paystubs">
            Paystubs
          </Link>
          <Link className="button secondary" to="/admin/documents">
            Documents
          </Link>
          <Link className="button secondary" to="/admin/requests">
            Requests
          </Link>
          <Link className="button secondary" to="/admin/settings">
            Settings
          </Link>
        </div>
      </div>
    </>
  );
}
