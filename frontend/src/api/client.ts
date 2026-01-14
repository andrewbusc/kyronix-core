const envApiUrl = import.meta.env.VITE_API_URL as string | undefined;
const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
const normalizedEnvApiUrl =
  envApiUrl && isHttps ? envApiUrl.replace(/^http:/, "https:") : envApiUrl;
const inferredApiUrl =
  typeof window !== "undefined" && window.location.hostname === "core.kyronix.ai"
    ? "https://api.core.kyronix.ai"
    : "http://localhost:8000";
const API_URL = normalizedEnvApiUrl || inferredApiUrl;

function getToken() {
  return localStorage.getItem("kc_token");
}

async function apiRequest(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }
  return response;
}

function getFileNameFromDisposition(disposition: string | null) {
  if (!disposition) {
    return null;
  }
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  return match ? match[1] : null;
}

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!response.ok) {
    throw new Error("Invalid credentials");
  }
  return response.json();
}

export async function getMe() {
  const response = await apiRequest("/api/auth/me");
  return response.json();
}

export async function requestPasswordReset(email: string) {
  const response = await apiRequest("/api/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  return response.json();
}

export async function confirmPasswordReset(token: string, newPassword: string) {
  const response = await apiRequest("/api/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  return response.json();
}

export async function listDocuments() {
  const response = await apiRequest("/api/documents");
  return response.json();
}

export async function createDocument(payload: { title: string; body: string; owner_id: number }) {
  const response = await apiRequest("/api/documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function getDocument(docId: number) {
  const response = await apiRequest(`/api/documents/${docId}`);
  return response.json();
}

export async function downloadDocumentPdf(docId: number) {
  const response = await apiRequest(`/api/documents/${docId}/pdf`);
  const blob = await response.blob();
  return blob;
}

export async function listPaystubs(year?: number) {
  const params = year ? `?year=${year}` : "";
  const response = await apiRequest(`/api/paystubs${params}`);
  return response.json();
}

export async function downloadPaystubPdf(paystubId: number) {
  const response = await apiRequest(`/api/paystubs/${paystubId}/pdf`);
  const blob = await response.blob();
  const filename = getFileNameFromDisposition(response.headers.get("Content-Disposition"));
  return { blob, filename };
}

export async function generatePaystubPdf(payload: unknown) {
  const response = await apiRequest("/api/v1/paystubs/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const blob = await response.blob();
  const filename = getFileNameFromDisposition(response.headers.get("Content-Disposition"));
  return { blob, filename };
}

export async function listUsers() {
  const response = await apiRequest("/api/users");
  return response.json();
}

export async function createUser(payload: {
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
}) {
  const response = await apiRequest("/api/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.json();
}
