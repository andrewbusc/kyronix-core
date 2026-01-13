import { Link } from "react-router-dom";

import type { User } from "../App";

type Props = {
  user: User;
};

export default function Home({ user }: Props) {
  const statusMessage =
    user.employment_status === "FORMER_EMPLOYEE"
      ? "Your access is read-only. Documents remain available for download."
      : "Your access is active. Documents and pay history are ready when you need them.";

  return (
    <>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Home</h2>
        <p>{`Signed in as ${user.email}.`}</p>
        <p>{statusMessage}</p>
        <div className="row">
          <Link className="button secondary" to="/paystubs">
            Paystubs
          </Link>
          <Link className="button secondary" to="/documents">
            Documents
          </Link>
          <Link className="button secondary" to="/profile">
            Profile
          </Link>
          <Link className="button secondary" to="/support">
            Support
          </Link>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Documents</h3>
        <p>Review and download your documents in PDF format.</p>
        <Link className="button" to="/documents">
          Go to Documents
        </Link>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Pay history</h3>
        <p>Paystubs are stored in Kyronix Core for quick access.</p>
        <Link className="button secondary" to="/paystubs">
          View paystubs
        </Link>
      </div>
    </>
  );
}
