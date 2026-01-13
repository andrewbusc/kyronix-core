import type { User } from "../App";

type Props = {
  user: User;
};

export default function Profile({ user }: Props) {
  const statusLabel =
    user.employment_status === "FORMER_EMPLOYEE" ? "Former Employee (read-only)" : "Active";
  const displayValue = (value?: string | null) => value || "Not provided";
  const addressLine = [user.address_line1, user.address_line2].filter(Boolean).join(", ");

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
        <h3 style={{ marginTop: 0 }}>Account help</h3>
        <p>Use Support for access questions, verification letters, or document updates.</p>
      </div>
    </>
  );
}
