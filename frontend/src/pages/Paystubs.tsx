import { useEffect, useMemo, useState } from "react";

import { downloadPaystubPdf, listPaystubs } from "../api/client";

type PaystubSummary = {
  id: number;
  pay_date: string;
  pay_period_start: string;
  pay_period_end: string;
  file_name: string;
};

type PaystubListResponse = {
  items: PaystubSummary[];
  available_years: number[];
};

export default function Paystubs() {
  const [paystubs, setPaystubs] = useState<PaystubSummary[]>([]);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const selectedYearValue = useMemo(() => {
    if (selectedYear === "all") {
      return undefined;
    }
    const parsed = Number(selectedYear);
    return Number.isNaN(parsed) ? undefined : parsed;
  }, [selectedYear]);

  const fetchPaystubs = async (year?: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = (await listPaystubs(year)) as PaystubListResponse;
      setPaystubs(data.items);
      setAvailableYears(data.available_years);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load paystubs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaystubs(selectedYearValue);
  }, [selectedYearValue]);

  const handleDownload = async (stub: PaystubSummary) => {
    try {
      const { blob, filename } = await downloadPaystubPdf(stub.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || stub.file_name || "paystub.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download paystub");
    }
  };

  return (
    <>
      {error && <div className="card">{error}</div>}

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Paystubs</h2>
            <p style={{ marginTop: 6, color: "rgba(11, 31, 42, 0.6)" }}>
              Paystubs are available as PDF downloads.
            </p>
          </div>
          <div className="row" style={{ alignItems: "center" }}>
            <label style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
              Year
              <select
                className="input"
                style={{ marginLeft: 8 }}
                value={selectedYear}
                onChange={(event) => setSelectedYear(event.target.value)}
              >
                <option value="all">All years</option>
                {availableYears.map((year) => (
                  <option key={year} value={String(year)}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <button className="button secondary" onClick={() => fetchPaystubs(selectedYearValue)}>
              Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <p>Loading paystubs...</p>
        ) : paystubs.length === 0 ? (
          <p>No paystubs available.</p>
        ) : (
          <div className="grid">
            {paystubs.map((stub) => (
              <div key={stub.id} className="card" style={{ padding: 16 }}>
                <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{`Pay date: ${stub.pay_date}`}</strong>
                    <div style={{ fontSize: "0.85rem", color: "rgba(11, 31, 42, 0.6)" }}>
                      {`Pay period: ${stub.pay_period_start} to ${stub.pay_period_end}`}
                    </div>
                  </div>
                  <button className="button" onClick={() => handleDownload(stub)}>
                    Download PDF
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
