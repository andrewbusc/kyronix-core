import { useEffect, useState } from "react";

import { createDocument, getDocument, listDocuments } from "../../api/client";

type Document = {
  id: number;
  title: string;
  body: string;
  owner_id: number;
};

export default function AdminDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Document | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
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

  const handleSelect = async (docId: number) => {
    try {
      const doc = await getDocument(docId);
      setSelected(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open document");
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

  return (
    <>
      {error && <div className="card">{error}</div>}

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
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{selected.title}</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{selected.body}</p>
        </div>
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
