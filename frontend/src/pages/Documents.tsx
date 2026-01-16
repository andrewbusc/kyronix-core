import { useEffect, useState } from "react";

import {
  createVerificationRequest,
  downloadDocumentPdf,
  downloadVerificationPdf,
  getDocument,
  listDocuments,
  listVerificationRequests,
} from "../api/client";

type Document = {
  id: number;
  title: string;
  body: string;
  owner_id: number;
};

type VerificationRequest = {
  id: number;
  verifier_name: string;
  verifier_company?: string | null;
  verifier_email?: string | null;
  purpose: string;
  include_salary: boolean;
  consent: boolean;
  status: "PENDING" | "GENERATED" | "SENT" | "DECLINED";
  delivery_method?: "VERIFIER" | "EMPLOYEE";
  document_id?: number | null;
  created_at?: string | null;
  generated_at?: string | null;
  sent_at?: string | null;
  file_name?: string | null;
  decline_reason?: string | null;
};

type VerificationForm = {
  verifier_name: string;
  verifier_company: string;
  verifier_email: string;
  purpose: string;
  include_salary: boolean;
  consent: boolean;
  delivery_method: "VERIFIER" | "EMPLOYEE";
};

function getSafeFileName(title: string) {
  const normalized = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return normalized ? `${normalized}.pdf` : "document.pdf";
}

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Document | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [verificationRequests, setVerificationRequests] = useState<VerificationRequest[]>([]);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [verificationLoading, setVerificationLoading] = useState(true);
  const [verificationForm, setVerificationForm] = useState<VerificationForm>({
    verifier_name: "",
    verifier_company: "",
    verifier_email: "",
    purpose: "",
    include_salary: false,
    consent: false,
    delivery_method: "VERIFIER",
  });

  const formatVerificationStatus = (status: VerificationRequest["status"]) => {
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

  const refreshDocuments = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await listDocuments();
      setDocuments(data);
      setSelected(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  const refreshVerificationRequests = async () => {
    setVerificationError(null);
    setVerificationLoading(true);
    try {
      const data = await listVerificationRequests();
      setVerificationRequests(data);
    } catch (err) {
      setVerificationError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setVerificationLoading(false);
    }
  };

  useEffect(() => {
    refreshDocuments();
    refreshVerificationRequests();
  }, []);

  const handleSelect = async (docId: number) => {
    try {
      const doc = await getDocument(docId);
      setSelected(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open document");
    }
  };

  const handleDownload = async (doc: Document) => {
    const { blob, filename } = await downloadDocumentPdf(doc.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename || getSafeFileName(doc.title);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleVerificationSubmit = async () => {
    const needsEmail = verificationForm.delivery_method === "VERIFIER";
    if (
      !verificationForm.verifier_name ||
      !verificationForm.purpose ||
      (needsEmail && !verificationForm.verifier_email)
    ) {
      setVerificationError("Please complete all required fields.");
      return;
    }
    if (!verificationForm.consent) {
      setVerificationError("Consent is required to submit a verification request.");
      return;
    }
    setVerificationError(null);
    try {
      await createVerificationRequest({
        verifier_name: verificationForm.verifier_name,
        verifier_company: verificationForm.verifier_company || null,
        verifier_email: verificationForm.verifier_email.trim() || null,
        purpose: verificationForm.purpose,
        include_salary: verificationForm.include_salary,
        consent: verificationForm.consent,
        delivery_method: verificationForm.delivery_method,
      });
      setVerificationForm({
        verifier_name: "",
        verifier_company: "",
        verifier_email: "",
        purpose: "",
        include_salary: false,
        consent: false,
        delivery_method: "VERIFIER",
      });
      await refreshVerificationRequests();
    } catch (err) {
      setVerificationError(
        err instanceof Error ? err.message : "Unable to submit verification request"
      );
    }
  };

  const handleVerificationDownload = async (requestId: number) => {
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

  return (
    <>
      {error && <div className="card">{error}</div>}
      {verificationError && <div className="card">{verificationError}</div>}

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ margin: 0 }}>Employment verification</h2>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Submit a request for a verification letter. HR can send it directly to the
              verifier or make it available in your documents.
            </p>
          </div>
        </div>
        <div className="grid">
          <div className="row">
            <input
              className="input"
              placeholder="Verifier name"
              value={verificationForm.verifier_name}
              onChange={(event) =>
                setVerificationForm({ ...verificationForm, verifier_name: event.target.value })
              }
            />
            <input
              className="input"
              placeholder="Verifier company (optional)"
              value={verificationForm.verifier_company}
              onChange={(event) =>
                setVerificationForm({ ...verificationForm, verifier_company: event.target.value })
              }
            />
          </div>
          <input
            className="input"
            placeholder="Verifier email (optional)"
            type="email"
            value={verificationForm.verifier_email}
            onChange={(event) =>
              setVerificationForm({ ...verificationForm, verifier_email: event.target.value })
            }
          />
          <textarea
            className="input"
            placeholder="Purpose of verification"
            rows={3}
            value={verificationForm.purpose}
            onChange={(event) =>
              setVerificationForm({ ...verificationForm, purpose: event.target.value })
            }
          />
          <label className="row" style={{ gap: 10 }}>
            <input
              type="checkbox"
              checked={verificationForm.include_salary}
              onChange={(event) =>
                setVerificationForm({ ...verificationForm, include_salary: event.target.checked })
              }
            />
            Include salary details (optional)
          </label>
          <label className="row" style={{ gap: 10 }}>
            <input
              type="checkbox"
              checked={verificationForm.consent}
              onChange={(event) =>
                setVerificationForm({ ...verificationForm, consent: event.target.checked })
              }
            />
            I authorize Kyronix LLC to share my employment details with the verifier above.
          </label>
          <label className="row" style={{ gap: 10 }}>
            Preferred delivery
            <select
              className="input"
              value={verificationForm.delivery_method}
              onChange={(event) =>
                setVerificationForm({
                  ...verificationForm,
                  delivery_method: event.target.value as "VERIFIER" | "EMPLOYEE",
                })
              }
            >
              <option value="VERIFIER">Send directly to verifier</option>
              <option value="EMPLOYEE">Make available in my documents</option>
            </select>
          </label>
          <button className="button" onClick={handleVerificationSubmit}>
            Submit request
          </button>
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h3 style={{ marginTop: 0 }}>Verification requests</h3>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Track requests and download completed letters.
            </p>
          </div>
          <button className="button secondary" onClick={refreshVerificationRequests}>
            Refresh
          </button>
        </div>
        {verificationLoading ? (
          <p>Loading requests...</p>
        ) : verificationRequests.length === 0 ? (
          <p>No verification requests yet.</p>
        ) : (
          <div className="grid">
            {verificationRequests.map((request) => (
              <div key={request.id} className="card" style={{ padding: 16 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div>
                    <strong>{request.verifier_name}</strong>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {request.verifier_company || "Company not provided"}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {request.verifier_email || "No verifier email provided"}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Requested: ${formatDate(request.created_at)} \u2022 Status: ${formatVerificationStatus(
                        request.status
                      )}`}
                    </div>
                  </div>
                  {request.status !== "PENDING" && request.status !== "DECLINED" && (
                    <button
                      className="button secondary"
                      onClick={() => handleVerificationDownload(request.id)}
                    >
                      Download PDF
                    </button>
                  )}
                </div>
                <p style={{ marginTop: 12 }}>{request.purpose}</p>
                <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                  {request.include_salary
                    ? "Salary disclosure requested."
                    : "Salary disclosure not requested."}
                </div>
                {request.delivery_method && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {request.delivery_method === "EMPLOYEE"
                      ? "Preferred delivery: employee documents."
                      : "Preferred delivery: verifier."}
                  </div>
                )}
                {request.document_id && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    Saved to your Documents.
                  </div>
                )}
                {request.status === "DECLINED" && request.decline_reason && (
                  <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                    {`Reason: ${request.decline_reason}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ margin: 0 }}>Documents</h2>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              All documents are provided as PDF files.
            </p>
          </div>
          <button className="button secondary" onClick={refreshDocuments}>
            Refresh
          </button>
        </div>
        {loading ? (
          <p>Loading documents...</p>
        ) : documents.length === 0 ? (
          <p>No documents available.</p>
        ) : (
          <div className="grid">
            {documents.map((doc) => (
              <div key={doc.id} className="card" style={{ padding: 16 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div>
                    <strong>{doc.title}</strong>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      PDF ready for download
                    </div>
                  </div>
                  <div className="row">
                    <button className="button secondary" onClick={() => handleSelect(doc.id)}>
                      Open
                    </button>
                    <button className="button" onClick={() => handleDownload(doc)}>
                      Download PDF
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{selected.title}</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{selected.body}</p>
        </div>
      )}
    </>
  );
}
