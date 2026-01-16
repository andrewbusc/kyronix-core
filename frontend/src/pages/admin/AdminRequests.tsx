import { useEffect, useMemo, useState } from "react";

import {
  declineVerificationRequest,
  downloadVerificationPdf,
  generateVerificationRequest,
  listVerificationRequests,
  markVerificationSent,
} from "../../api/client";

type VerificationRequest = {
  id: number;
  verifier_name: string;
  verifier_company?: string | null;
  verifier_email: string;
  purpose: string;
  include_salary: boolean;
  status: "PENDING" | "GENERATED" | "SENT" | "DECLINED";
  delivery_method?: "VERIFIER" | "EMPLOYEE";
  document_id?: number | null;
  created_at?: string | null;
  generated_at?: string | null;
  sent_at?: string | null;
  salary_amount?: number | null;
  sent_note?: string | null;
  decline_reason?: string | null;
  employee: {
    id: number;
    legal_first_name: string;
    legal_last_name: string;
    job_title: string;
    department: string;
    hire_date: string;
    employment_status: "ACTIVE" | "FORMER_EMPLOYEE";
  } | null;
};

export default function AdminRequests() {
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [salaryInputs, setSalaryInputs] = useState<Record<number, string>>({});
  const [sentNotes, setSentNotes] = useState<Record<number, string>>({});
  const [declineReasons, setDeclineReasons] = useState<Record<number, string>>({});
  const [deliveryMethods, setDeliveryMethods] = useState<
    Record<number, "VERIFIER" | "EMPLOYEE">
  >({});

  const sortedRequests = useMemo(() => {
    return [...requests].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  }, [requests]);

  const formatStatus = (status: VerificationRequest["status"]) => {
    if (status === "GENERATED") return "Generated";
    if (status === "SENT") return "Sent";
    if (status === "DECLINED") return "Declined";
    return "Pending";
  };

  const formatDate = (value?: string | null) => {
    if (!value) return "Not available";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
  };

  const refresh = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await listVerificationRequests();
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleGenerate = async (request: VerificationRequest) => {
    setError(null);
    try {
      const salaryValue = salaryInputs[request.id];
      const salaryAmount =
        request.include_salary && salaryValue ? Number.parseFloat(salaryValue) : undefined;
      const deliveryMethod = deliveryMethods[request.id] || "VERIFIER";
      const { blob, filename } = await generateVerificationRequest(
        request.id,
        salaryAmount,
        deliveryMethod
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || "employment_verification.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate letter");
    }
  };

  const handleDownload = async (requestId: number) => {
    const { blob, filename } = await downloadVerificationPdf(requestId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename || "employment_verification.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleMarkSent = async (requestId: number) => {
    setError(null);
    try {
      await markVerificationSent(requestId, sentNotes[requestId]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to mark as sent");
    }
  };

  const handleDecline = async (requestId: number) => {
    setError(null);
    try {
      await declineVerificationRequest(requestId, declineReasons[requestId]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to decline request");
    }
  };

  return (
    <>
      {error && <div className="card">{error}</div>}
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ marginTop: 0 }}>Requests</h2>
            <p>Track employee requests for documents, paystubs, and verification letters.</p>
          </div>
          <button className="button secondary" onClick={refresh}>
            Refresh
          </button>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Verification queue</h3>
        {loading ? (
          <p>Loading requests...</p>
        ) : sortedRequests.length === 0 ? (
          <p>No requests yet.</p>
        ) : (
          <div className="grid">
            {sortedRequests.map((request) => (
              <div key={request.id} className="card" style={{ padding: 16 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div>
                    <strong>{request.verifier_name}</strong>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {request.verifier_company || "Company not provided"}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {request.verifier_email}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Requested: ${formatDate(request.created_at)} \u2022 Status: ${formatStatus(
                        request.status
                      )}`}
                    </div>
                    {request.employee && (
                      <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                        {`${request.employee.legal_first_name} ${request.employee.legal_last_name} \u2022 ${request.employee.job_title}`}
                      </div>
                    )}
                  </div>
                  <span className="pill">{formatStatus(request.status)}</span>
                </div>
                <p style={{ marginTop: 12 }}>{request.purpose}</p>
                <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                  {request.include_salary ? "Salary disclosure requested." : "Salary disclosure not requested."}
                </div>
                {request.document_id && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    Saved to employee documents.
                  </div>
                )}
                {request.include_salary && request.status === "PENDING" && (
                  <div style={{ marginTop: 12 }}>
                    <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      Annual base salary
                      <input
                        className="input"
                        placeholder="0.00"
                        value={salaryInputs[request.id] || ""}
                        onChange={(event) =>
                          setSalaryInputs({
                            ...salaryInputs,
                            [request.id]: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                )}
                {request.include_salary &&
                  request.status !== "PENDING" &&
                  request.salary_amount !== null &&
                  request.salary_amount !== undefined && (
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Salary on record: $${request.salary_amount.toLocaleString()}`}
                    </div>
                  )}
                {request.status === "PENDING" && (
                  <div style={{ marginTop: 12 }}>
                    <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      Delivery method
                      <select
                        className="input"
                        value={deliveryMethods[request.id] || "VERIFIER"}
                        onChange={(event) =>
                          setDeliveryMethods({
                            ...deliveryMethods,
                            [request.id]: event.target.value as "VERIFIER" | "EMPLOYEE",
                          })
                        }
                      >
                        <option value="VERIFIER">Send directly to verifier</option>
                        <option value="EMPLOYEE">Make available in employee documents</option>
                      </select>
                    </label>
                  </div>
                )}
                {request.status === "PENDING" && (
                  <div style={{ marginTop: 12 }}>
                    <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      Decline reason (optional)
                      <input
                        className="input"
                        placeholder="Reason for decline"
                        value={declineReasons[request.id] || ""}
                        onChange={(event) =>
                          setDeclineReasons({
                            ...declineReasons,
                            [request.id]: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                )}
                {request.status === "DECLINED" && request.decline_reason && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`Declined: ${request.decline_reason}`}
                  </div>
                )}
                {request.status !== "PENDING" && request.sent_note && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`Sent note: ${request.sent_note}`}
                  </div>
                )}
                <div className="row" style={{ marginTop: 12 }}>
                  {request.status === "PENDING" && (
                    <button className="button" onClick={() => handleGenerate(request)}>
                      Generate PDF
                    </button>
                  )}
                  {request.status !== "PENDING" && request.status !== "DECLINED" && (
                    <button
                      className="button secondary"
                      onClick={() => handleDownload(request.id)}
                    >
                      Download PDF
                    </button>
                  )}
                  {request.status === "GENERATED" && (
                    <>
                      {request.delivery_method !== "EMPLOYEE" && (
                        <>
                          <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                            Send note (optional)
                            <input
                              className="input"
                              placeholder="Notes about delivery"
                              value={sentNotes[request.id] || ""}
                              onChange={(event) =>
                                setSentNotes({
                                  ...sentNotes,
                                  [request.id]: event.target.value,
                                })
                              }
                            />
                          </label>
                          <button
                            className="button secondary"
                            onClick={() => handleMarkSent(request.id)}
                          >
                            Mark sent
                          </button>
                        </>
                      )}
                    </>
                  )}
                  {request.status === "PENDING" && (
                    <button
                      className="button secondary"
                      onClick={() => handleDecline(request.id)}
                    >
                      Decline
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
