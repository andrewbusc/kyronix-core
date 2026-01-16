import { useEffect, useState } from "react";

import {
  API_URL,
  createDocument,
  createDocumentShare,
  getDocument,
  listDocuments,
  listDocumentShares,
  revokeDocumentShare,
} from "../../api/client";

type Document = {
  id: number;
  title: string;
  body: string;
  owner_id: number;
};

type DocumentShare = {
  id: number;
  token: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
};

export default function AdminDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Document | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [shareError, setShareError] = useState<string | null>(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [shares, setShares] = useState<DocumentShare[]>([]);
  const [shareExpiry, setShareExpiry] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [ownerId, setOwnerId] = useState("");

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

  useEffect(() => {
    refreshDocuments();
  }, []);

  useEffect(() => {
    if (selected) {
      refreshShares(selected.id);
      setShareExpiry("");
    } else {
      setShares([]);
    }
  }, [selected?.id]);

  const handleSelect = async (docId: number) => {
    try {
      const doc = await getDocument(docId);
      setSelected(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open document");
    }
  };

  const refreshShares = async (docId: number) => {
    setShareError(null);
    setShareLoading(true);
    try {
      const data = await listDocumentShares(docId);
      setShares(data);
    } catch (err) {
      setShareError(err instanceof Error ? err.message : "Unable to load share links");
    } finally {
      setShareLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!title || !ownerId) {
      setError("Title and owner are required.");
      return;
    }
    setError(null);
    try {
      await createDocument({ title, body, owner_id: Number(ownerId) });
      setTitle("");
      setBody("");
      setOwnerId("");
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create document");
    }
  };

  const handleCreateShare = async () => {
    if (!selected) {
      return;
    }
    setShareError(null);
    let expiresAt: string | null = null;
    if (shareExpiry) {
      const parsed = new Date(shareExpiry);
      if (Number.isNaN(parsed.getTime())) {
        setShareError("Enter a valid expiration date.");
        return;
      }
      expiresAt = parsed.toISOString();
    }
    try {
      await createDocumentShare(selected.id, expiresAt);
      setShareExpiry("");
      await refreshShares(selected.id);
    } catch (err) {
      setShareError(err instanceof Error ? err.message : "Unable to create share link");
    }
  };

  const handleRevokeShare = async (shareId: number) => {
    if (!selected) {
      return;
    }
    const confirmed = window.confirm("Revoke this share link?");
    if (!confirmed) {
      return;
    }
    setShareError(null);
    try {
      await revokeDocumentShare(selected.id, shareId);
      await refreshShares(selected.id);
    } catch (err) {
      setShareError(err instanceof Error ? err.message : "Unable to revoke share link");
    }
  };

  return (
    <>
      {error && <div className="card">{error}</div>}
      {shareError && <div className="card">{shareError}</div>}

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ margin: 0 }}>Documents</h2>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Documents are delivered as PDFs.
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
                      {`Document ID ${doc.id} \u2022 Owner ID ${doc.owner_id}`}
                    </div>
                  </div>
                  <button className="button secondary" onClick={() => handleSelect(doc.id)}>
                    Open
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>{selected.title}</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{selected.body}</p>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Share links</h3>
            <div className="grid">
              <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                Expiration (optional)
                <input
                  className="input"
                  type="datetime-local"
                  value={shareExpiry}
                  onChange={(event) => setShareExpiry(event.target.value)}
                />
              </label>
              <button className="button" onClick={handleCreateShare}>
                Create share link
              </button>
            </div>
            {shareLoading ? (
              <p>Loading share links...</p>
            ) : shares.length === 0 ? (
              <p>No share links yet.</p>
            ) : (
              <div className="grid">
                {shares.map((share) => {
                  const expiresAt = share.expires_at ? new Date(share.expires_at) : null;
                  const isExpired =
                    expiresAt && !Number.isNaN(expiresAt.getTime()) && expiresAt < new Date();
                  const status = share.revoked_at
                    ? "Revoked"
                    : isExpired
                    ? "Expired"
                    : "Active";
                  const shareUrl = `${API_URL}/api/documents/shares/${share.token}/pdf`;
                  return (
                    <div key={share.id} className="card" style={{ padding: 16 }}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <div>
                          <strong>{status}</strong>
                          <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                            {share.expires_at
                              ? `Expires: ${new Date(share.expires_at).toLocaleString()}`
                              : "No expiration"}
                          </div>
                        </div>
                        {!share.revoked_at && (
                          <button
                            className="button secondary"
                            onClick={() => handleRevokeShare(share.id)}
                          >
                            Revoke
                          </button>
                        )}
                      </div>
                      <input className="input" readOnly value={shareUrl} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Create document</h2>
        <div className="grid">
          <input
            className="input"
            placeholder="Title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            className="input"
            rows={4}
            placeholder="Body"
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
          <input
            className="input"
            placeholder="Owner user ID"
            value={ownerId}
            onChange={(event) => setOwnerId(event.target.value)}
          />
          <button className="button" onClick={handleCreate}>
            Create document
          </button>
        </div>
      </div>
    </>
  );
}
