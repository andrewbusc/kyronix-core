import { useEffect, useState } from "react";

import { createUser, deleteUser, listUsers } from "../../api/client";
import type { User } from "../../App";

type CreateUserPayload = {
  email: string;
  password: string;
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
};

const emptyForm: CreateUserPayload = {
  email: "",
  password: "",
  legal_first_name: "",
  legal_last_name: "",
  preferred_name: "",
  job_title: "",
  department: "",
  hire_date: "",
  phone: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  emergency_contact_relationship: "",
  role: "EMPLOYEE",
  employment_status: "ACTIVE",
};

export default function AdminEmployees() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<CreateUserPayload>({ ...emptyForm });

  const formatStatus = (status: User["employment_status"]) =>
    status === "FORMER_EMPLOYEE" ? "Former Employee" : "Active";

  const fetchUsers = async () => {
    setError(null);
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async () => {
    if (
      !form.email ||
      !form.password ||
      !form.legal_first_name ||
      !form.legal_last_name ||
      !form.job_title ||
      !form.department ||
      !form.hire_date ||
      !form.address_line1 ||
      !form.city ||
      !form.state ||
      !form.postal_code ||
      !form.country ||
      !form.emergency_contact_name ||
      !form.emergency_contact_phone ||
      !form.emergency_contact_relationship
    ) {
      setError("Please complete all required fields.");
      return;
    }
    setError(null);
    try {
      const payload: CreateUserPayload = {
        ...form,
        preferred_name: form.preferred_name || null,
        phone: form.phone || null,
        address_line2: form.address_line2 || null,
      };
      await createUser(payload);
      setForm({ ...emptyForm });
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user");
    }
  };

  const handleDeleteUser = async (entry: User) => {
    const displayName = `${entry.legal_first_name} ${entry.legal_last_name}`.trim();
    const confirmed = window.confirm(
      `Delete ${displayName}? This will remove the employee and their data.`
    );
    if (!confirmed) {
      return;
    }
    setError(null);
    try {
      await deleteUser(entry.id);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete user");
    }
  };

  return (
    <>
      {error && <div className="card">{error}</div>}

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ margin: 0 }}>Employees</h2>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Manage Kyronix Core access.
            </p>
          </div>
          <button className="button secondary" onClick={fetchUsers}>
            Refresh
          </button>
        </div>
        <div className="grid">
          {users.map((entry) => (
            <div key={entry.id} className="card" style={{ padding: 16 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <strong>{`${entry.legal_first_name} ${entry.legal_last_name}`}</strong>
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`${entry.job_title} \u2022 ${entry.department}`}
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`${entry.email} \u2022 ${entry.role} \u2022 ${formatStatus(
                      entry.employment_status
                    )}`}
                  </div>
                </div>
                <div className="row" style={{ alignItems: "center", justifyContent: "flex-end" }}>
                  <span className="pill">{entry.is_active ? "Enabled" : "Disabled"}</span>
                  <button
                    className="button secondary"
                    style={{ borderColor: "rgba(154, 74, 20, 0.4)", color: "#9a4a14" }}
                    onClick={() => handleDeleteUser(entry)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {users.length === 0 && <p>No users found.</p>}
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Add employee</h2>
        <div className="grid">
          <div className="row">
            <input
              className="input"
              placeholder="Legal first name"
              value={form.legal_first_name}
              onChange={(event) => setForm({ ...form, legal_first_name: event.target.value })}
            />
            <input
              className="input"
              placeholder="Legal last name"
              value={form.legal_last_name}
              onChange={(event) => setForm({ ...form, legal_last_name: event.target.value })}
            />
          </div>
          <input
            className="input"
            placeholder="Preferred name (optional)"
            value={form.preferred_name || ""}
            onChange={(event) => setForm({ ...form, preferred_name: event.target.value })}
          />
          <input
            className="input"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
          />
          <input
            className="input"
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
          />
          <div className="row">
            <input
              className="input"
              placeholder="Job title"
              value={form.job_title}
              onChange={(event) => setForm({ ...form, job_title: event.target.value })}
            />
            <input
              className="input"
              placeholder="Department"
              value={form.department}
              onChange={(event) => setForm({ ...form, department: event.target.value })}
            />
          </div>
          <div className="row">
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Hire date
              <input
                className="input"
                type="date"
                value={form.hire_date}
                onChange={(event) => setForm({ ...form, hire_date: event.target.value })}
              />
            </label>
            <input
              className="input"
              placeholder="Phone (optional)"
              value={form.phone || ""}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
            />
          </div>
          <input
            className="input"
            placeholder="Address line 1"
            value={form.address_line1}
            onChange={(event) => setForm({ ...form, address_line1: event.target.value })}
          />
          <input
            className="input"
            placeholder="Address line 2 (optional)"
            value={form.address_line2 || ""}
            onChange={(event) => setForm({ ...form, address_line2: event.target.value })}
          />
          <div className="row">
            <input
              className="input"
              placeholder="City"
              value={form.city}
              onChange={(event) => setForm({ ...form, city: event.target.value })}
            />
            <input
              className="input"
              placeholder="State"
              value={form.state}
              onChange={(event) => setForm({ ...form, state: event.target.value })}
            />
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Postal code"
              value={form.postal_code}
              onChange={(event) => setForm({ ...form, postal_code: event.target.value })}
            />
            <input
              className="input"
              placeholder="Country"
              value={form.country}
              onChange={(event) => setForm({ ...form, country: event.target.value })}
            />
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Emergency contact name"
              value={form.emergency_contact_name}
              onChange={(event) =>
                setForm({ ...form, emergency_contact_name: event.target.value })
              }
            />
            <input
              className="input"
              placeholder="Emergency contact phone"
              value={form.emergency_contact_phone}
              onChange={(event) =>
                setForm({ ...form, emergency_contact_phone: event.target.value })
              }
            />
          </div>
          <input
            className="input"
            placeholder="Emergency contact relationship"
            value={form.emergency_contact_relationship}
            onChange={(event) =>
              setForm({ ...form, emergency_contact_relationship: event.target.value })
            }
          />
          <div className="row">
            <select
              className="input"
              value={form.role}
              onChange={(event) =>
                setForm({ ...form, role: event.target.value as CreateUserPayload["role"] })
              }
            >
              <option value="EMPLOYEE">Employee</option>
              <option value="ADMIN">Admin</option>
            </select>
            <select
              className="input"
              value={form.employment_status}
              onChange={(event) =>
                setForm({
                  ...form,
                  employment_status: event.target.value as CreateUserPayload["employment_status"],
                })
              }
            >
              <option value="ACTIVE">Active</option>
              <option value="FORMER_EMPLOYEE">Former Employee</option>
            </select>
          </div>
          <button className="button" onClick={handleCreateUser}>
            Add employee
          </button>
        </div>
      </div>
    </>
  );
}
