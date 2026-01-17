import { useEffect, useState, type ChangeEvent } from "react";

import { updateMyProfile } from "../api/client";
import type { User } from "../App";

type Props = {
  user: User;
  onProfileUpdate: (user: User) => void;
};

type ProfileForm = {
  preferred_name: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
};

const buildFormState = (user: User): ProfileForm => ({
  preferred_name: user.preferred_name || "",
  phone: user.phone || "",
  address_line1: user.address_line1 || "",
  address_line2: user.address_line2 || "",
  city: user.city || "",
  state: user.state || "",
  postal_code: user.postal_code || "",
  country: user.country || "",
  emergency_contact_name: user.emergency_contact_name || "",
  emergency_contact_phone: user.emergency_contact_phone || "",
  emergency_contact_relationship: user.emergency_contact_relationship || "",
});

export default function Profile({ user, onProfileUpdate }: Props) {
  const statusLabel =
    user.employment_status === "FORMER_EMPLOYEE" ? "Former Employee (read-only)" : "Active";
  const displayValue = (value?: string | null) => value || "Not provided";
  const addressLine = [user.address_line1, user.address_line2].filter(Boolean).join(", ");
  const isReadOnly = user.employment_status === "FORMER_EMPLOYEE";

  const [form, setForm] = useState<ProfileForm>(() => buildFormState(user));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(buildFormState(user));
  }, [user]);

  const updateField =
    (field: keyof ProfileForm) => (event: ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
      setError(null);
      setSuccess(null);
    };

  const handleSave = async () => {
    if (isReadOnly) {
      return;
    }
    if (
      !form.address_line1.trim() ||
      !form.city.trim() ||
      !form.state.trim() ||
      !form.postal_code.trim() ||
      !form.country.trim() ||
      !form.emergency_contact_name.trim() ||
      !form.emergency_contact_phone.trim() ||
      !form.emergency_contact_relationship.trim()
    ) {
      setError("Please complete all required fields.");
      return;
    }
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const payload = {
        preferred_name: form.preferred_name.trim() || null,
        phone: form.phone.trim() || null,
        address_line1: form.address_line1.trim(),
        address_line2: form.address_line2.trim() || null,
        city: form.city.trim(),
        state: form.state.trim(),
        postal_code: form.postal_code.trim(),
        country: form.country.trim(),
        emergency_contact_name: form.emergency_contact_name.trim(),
        emergency_contact_phone: form.emergency_contact_phone.trim(),
        emergency_contact_relationship: form.emergency_contact_relationship.trim(),
      };
      const updated = await updateMyProfile(payload);
      onProfileUpdate(updated);
      setSuccess("Profile updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Profile</h2>
        <div className="grid">
          <div>
            <strong>Email</strong>
            <div>{user.email}</div>
          </div>
          <div>
            <strong>Legal name</strong>
            <div>{`${user.legal_first_name} ${user.legal_last_name}`}</div>
          </div>
          <div>
            <strong>Preferred name</strong>
            <div>{displayValue(user.preferred_name)}</div>
          </div>
          <div>
            <strong>Status</strong>
            <div>{statusLabel}</div>
          </div>
          <div>
            <strong>Job title</strong>
            <div>{user.job_title}</div>
          </div>
          <div>
            <strong>Department</strong>
            <div>{user.department}</div>
          </div>
          <div>
            <strong>Hire date</strong>
            <div>{user.hire_date}</div>
          </div>
          <div>
            <strong>Phone</strong>
            <div>{displayValue(user.phone)}</div>
          </div>
          <div>
            <strong>Address</strong>
            <div>{addressLine || "Not provided"}</div>
          </div>
          <div>
            <strong>City</strong>
            <div>{user.city}</div>
          </div>
          <div>
            <strong>State</strong>
            <div>{user.state}</div>
          </div>
          <div>
            <strong>Postal code</strong>
            <div>{user.postal_code}</div>
          </div>
          <div>
            <strong>Country</strong>
            <div>{user.country}</div>
          </div>
          <div>
            <strong>Emergency contact</strong>
            <div>{user.emergency_contact_name}</div>
          </div>
          <div>
            <strong>Emergency contact phone</strong>
            <div>{user.emergency_contact_phone}</div>
          </div>
          <div>
            <strong>Emergency contact relationship</strong>
            <div>{user.emergency_contact_relationship}</div>
          </div>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Update contact info</h3>
        {isReadOnly && (
          <p style={{ color: "rgba(11, 31, 42, 0.6)" }}>
            This profile is read-only. Use Support for updates.
          </p>
        )}
        {error && <p style={{ color: "#9a4a14" }}>{error}</p>}
        {success && <p style={{ color: "rgba(11, 31, 42, 0.6)" }}>{success}</p>}
        <div className="grid">
          <input
            className="input"
            placeholder="Preferred name (optional)"
            value={form.preferred_name}
            onChange={updateField("preferred_name")}
            disabled={isReadOnly || saving}
          />
          <input
            className="input"
            placeholder="Phone (optional)"
            value={form.phone}
            onChange={updateField("phone")}
            disabled={isReadOnly || saving}
          />
          <input
            className="input"
            placeholder="Address line 1"
            value={form.address_line1}
            onChange={updateField("address_line1")}
            disabled={isReadOnly || saving}
          />
          <input
            className="input"
            placeholder="Address line 2 (optional)"
            value={form.address_line2}
            onChange={updateField("address_line2")}
            disabled={isReadOnly || saving}
          />
          <div className="row">
            <input
              className="input"
              placeholder="City"
              value={form.city}
              onChange={updateField("city")}
              disabled={isReadOnly || saving}
            />
            <input
              className="input"
              placeholder="State"
              value={form.state}
              onChange={updateField("state")}
              disabled={isReadOnly || saving}
            />
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Postal code"
              value={form.postal_code}
              onChange={updateField("postal_code")}
              disabled={isReadOnly || saving}
            />
            <input
              className="input"
              placeholder="Country"
              value={form.country}
              onChange={updateField("country")}
              disabled={isReadOnly || saving}
            />
          </div>
          <div className="row">
            <input
              className="input"
              placeholder="Emergency contact name"
              value={form.emergency_contact_name}
              onChange={updateField("emergency_contact_name")}
              disabled={isReadOnly || saving}
            />
            <input
              className="input"
              placeholder="Emergency contact phone"
              value={form.emergency_contact_phone}
              onChange={updateField("emergency_contact_phone")}
              disabled={isReadOnly || saving}
            />
          </div>
          <input
            className="input"
            placeholder="Emergency contact relationship"
            value={form.emergency_contact_relationship}
            onChange={updateField("emergency_contact_relationship")}
            disabled={isReadOnly || saving}
          />
          <div className="row">
            <button
              className="button"
              onClick={handleSave}
              disabled={isReadOnly || saving}
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Account help</h3>
        <p>Use Support for access questions, verification letters, or document updates.</p>
      </div>
    </>
  );
}
