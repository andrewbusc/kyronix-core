import { useEffect, useState } from "react";

import { downloadDocumentPdf, getDocument, listDocuments } from "../api/client";

type Document = {
  id: number;
  title: string;
  body: string;
  owner_id: number;
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

  const handleDownload = async (doc: Document) => {
    const blob = await downloadDocumentPdf(doc.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = getSafeFileName(doc.title);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <>
      {error && <div className="card">{error}</div>}

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
