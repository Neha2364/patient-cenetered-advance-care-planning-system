const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function getHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("acp_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function apiFetch<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errMsg = "An error occurred";
    try {
      const errData = await response.json();
      const rawMsg = errData.message || errData.error;
      if (typeof rawMsg === "string") {
        errMsg = rawMsg;
      } else if (Array.isArray(rawMsg)) {
        errMsg = rawMsg.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item))).join("; ");
      } else if (typeof rawMsg === "object" && rawMsg !== null) {
        errMsg = Object.entries(rawMsg)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(", ") : val}`)
          .join("; ");
      }
    } catch {}
    throw new ApiError(errMsg, response.status);
  }

  // Handle redirects or empty response
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response.text() as unknown as Promise<T>;
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { headers: getHeaders() });
  if (!response.ok) {
    let message = "Unable to download the document.";
    try { const body = await response.json(); message = body.message || body.error || message; } catch {}
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename;
  document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
}
// Authentication Service
export const authService = {
  async login(payload: any) {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("acp_token", data.token);
      localStorage.setItem(
        "acp_user",
        JSON.stringify({
          user_id: data.user_id,
          full_name: data.full_name,
          role: data.role,
          email: payload.email,
        })
      );
    }
    return data;
  },

  async register(payload: any) {
    // Map fullName to full_name for backend schema validation
    const backendPayload = {
      email: payload.email,
      password: payload.password,
      full_name: payload.fullName,
      role: payload.role,
    };
    return apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify(backendPayload),
    });
  },

  logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("acp_token");
      localStorage.removeItem("acp_user");
    }
  },

  getCurrentUser() {
    if (typeof window !== "undefined") {
      const user = localStorage.getItem("acp_user");
      return user ? JSON.parse(user) : null;
    }
    return null;
  },
};

// Patient and Care Service
export const patientService = {
  async getProfile(): Promise<any> {
    return apiFetch("/patients/me");
  },

  async createProfile(payload: any): Promise<any> {
    return apiFetch("/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateProfile(id: number, payload: any): Promise<any> {
    return apiFetch(`/patients/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async getACP(patientId: number): Promise<any> {
    try {
      return await apiFetch(`/acp/${patientId}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  async saveACP(payload: any): Promise<any> {
    return apiFetch("/acp", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateACP(patientId: number, payload: any): Promise<any> {
    return apiFetch(`/acp/${patientId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async createDHR(payload: any): Promise<any> {
    return apiFetch("/dhr", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getDHRs(patientId: number): Promise<any[]> {
    return apiFetch(`/dhr/${patientId}`);
  },

  async updateDHR(id: number, payload: any): Promise<any> {
    return apiFetch(`/dhr/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async generateAMD(payload: any): Promise<any> {
    return apiFetch("/amd/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getAMDHistory(patientId: number): Promise<any[]> {
    return apiFetch(`/doctor/amd/${patientId}`);
  },

  async downloadAMD(patientId: number, amdId?: number): Promise<void> { return downloadFile(`/amd/download/${patientId}${amdId ? `/${amdId}` : ""}`, "advance-medical-directive.pdf"); },

  async getAuditLogs(patientId: number): Promise<any[]> {
    return apiFetch(`/audit-logs/patient/${patientId}`);
  },
};

// Chat Service
export const chatService = {
  async getHistory(patientId: number): Promise<any[]> {
    return apiFetch(`/chat/history/${patientId}`);
  },

  async processChat(payload: any): Promise<any> {
    return apiFetch("/chat/process", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};

// Doctor Dashboard Service
export const doctorService = {
  async getPatients(params?: { search?: string; language?: string; is_completed?: boolean; review_status?: string }): Promise<any[]> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append("search", params.search);
    if (params?.language && params.language !== "all") searchParams.append("language", params.language);
    if (params?.is_completed !== undefined) searchParams.append("is_completed", String(params.is_completed));
    if (params?.review_status && params.review_status !== "all") searchParams.append("review_status", params.review_status);

    const queryStr = searchParams.toString();
    return apiFetch(`/doctor/patients${queryStr ? `?${queryStr}` : ""}`);
  },

  async getPatientDetails(id: number): Promise<any> {
    return apiFetch(`/doctor/patient/${id}`);
  },

  async reviewPatientACP(patientId: number, status: string): Promise<any> {
    return apiFetch(`/doctor/review/${patientId}`, {
      method: "PUT",
      body: JSON.stringify({ review_status: status }),
    });
  },
};
