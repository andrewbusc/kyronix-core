const envApiUrl = import.meta.env.VITE_API_URL as string | undefined;
const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
const normalizedEnvApiUrl =
  envApiUrl && isHttps ? envApiUrl.replace(/^http:/, "https:") : envApiUrl;
const inferredApiUrl =
  typeof window !== "undefined" && window.location.hostname === "core.kyronix.ai"
    ? "https://api.core.kyronix.ai"
    : "http://localhost:8000";
export const API_URL = normalizedEnvApiUrl || inferredApiUrl;

function getToken() {
  return localStorage.getItem("kc_token");
}

async function apiRequest(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers.has("Content-Type") && options.body && !isFormData) {
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
  const filename = getFileNameFromDisposition(response.headers.get("Content-Disposition"));
  return { blob, filename };
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

export async function deleteUser(userId: number) {
  await apiRequest(`/api/users/${userId}`, {
    method: "DELETE",
  });
}

export async function updateUser(
  userId: number,
  payload: {
    email?: string | null;
    legal_first_name?: string | null;
    legal_last_name?: string | null;
    preferred_name?: string | null;
    job_title?: string | null;
    department?: string | null;
    hire_date?: string | null;
    phone?: string | null;
    address_line1?: string | null;
    address_line2?: string | null;
    city?: string | null;
    state?: string | null;
    postal_code?: string | null;
    country?: string | null;
    emergency_contact_name?: string | null;
    emergency_contact_phone?: string | null;
    emergency_contact_relationship?: string | null;
    role?: "EMPLOYEE" | "ADMIN";
    employment_status?: "ACTIVE" | "FORMER_EMPLOYEE";
    is_active?: boolean;
  }
) {
  const response = await apiRequest(`/api/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function resetUserPassword(userId: number, newPassword: string) {
  const response = await apiRequest(`/api/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  });
  return response.json();
}

export async function listVerificationRequests() {
  const response = await apiRequest("/api/verification-requests");
  return response.json();
}

export async function createVerificationRequest(payload: {
  verifier_name: string;
  verifier_company?: string | null;
  verifier_email: string;
  purpose: string;
  include_salary: boolean;
  consent: boolean;
}) {
  const response = await apiRequest("/api/verification-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function generateVerificationRequest(
  requestId: number,
  salaryAmount?: number,
  deliveryMethod: "VERIFIER" | "EMPLOYEE" = "VERIFIER"
) {
  const response = await apiRequest(`/api/verification-requests/${requestId}/generate`, {
    method: "POST",
    body: JSON.stringify({
      salary_amount: salaryAmount ?? null,
      delivery_method: deliveryMethod,
    }),
  });
  const blob = await response.blob();
  const filename = getFileNameFromDisposition(response.headers.get("Content-Disposition"));
  return { blob, filename };
}

export async function markVerificationSent(requestId: number, sentNote?: string) {
  const response = await apiRequest(`/api/verification-requests/${requestId}/mark-sent`, {
    method: "POST",
    body: JSON.stringify({ sent_note: sentNote || null }),
  });
  return response.json();
}

export async function declineVerificationRequest(requestId: number, declineReason?: string) {
  const response = await apiRequest(`/api/verification-requests/${requestId}/decline`, {
    method: "POST",
    body: JSON.stringify({ decline_reason: declineReason || null }),
  });
  return response.json();
}

export async function downloadVerificationPdf(requestId: number) {
  const response = await apiRequest(`/api/verification-requests/${requestId}/pdf`);
  const blob = await response.blob();
  const filename = getFileNameFromDisposition(response.headers.get("Content-Disposition"));
  return { blob, filename };
}

export async function listDocumentShares(docId: number) {
  const response = await apiRequest(`/api/documents/${docId}/shares`);
  return response.json();
}

export async function createDocumentShare(docId: number, expiresAt?: string | null) {
  const response = await apiRequest(`/api/documents/${docId}/shares`, {
    method: "POST",
    body: JSON.stringify({ expires_at: expiresAt || null }),
  });
  return response.json();
}

export async function revokeDocumentShare(docId: number, shareId: number) {
  const response = await apiRequest(`/api/documents/${docId}/shares/${shareId}/revoke`, {
    method: "POST",
  });
  return response.json();
}

export async function listPaystubsForUser(userId: number, year?: number) {
  const params = new URLSearchParams();
  params.set("user_id", String(userId));
  if (year) {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiRequest(`/api/paystubs?${query}`);
  return response.json();
}

export async function uploadPaystub(payload: {
  userId: number;
  pay_date: string;
  pay_period_start: string;
  pay_period_end: string;
  file: File;
  file_name?: string | null;
}) {
  const form = new FormData();
  form.set("user_id", String(payload.userId));
  form.set("pay_date", payload.pay_date);
  form.set("pay_period_start", payload.pay_period_start);
  form.set("pay_period_end", payload.pay_period_end);
  form.set("file", payload.file);
  if (payload.file_name) {
    form.set("file_name", payload.file_name);
  }
  const response = await apiRequest("/api/paystubs/upload", {
    method: "POST",
    body: form,
  });
  return response.json();
}

export async function deletePaystub(paystubId: number) {
  await apiRequest(`/api/paystubs/${paystubId}`, {
    method: "DELETE",
  });
}
