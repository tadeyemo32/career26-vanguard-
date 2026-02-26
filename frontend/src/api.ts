export const API_BASE = import.meta.env.VITE_API_URL || "https://vanguard26-sac4otr44q-ew.a.run.app/api";
export function getAuthToken() {
    return localStorage.getItem("vanguard_token") || "";
}

export function setAuthToken(token: string) {
    if (!token) localStorage.removeItem("vanguard_token");
    else localStorage.setItem("vanguard_token", token);
}

export interface PersonRow {
    name: string;
    title: string;
    company: string;
    link: string;
    email: string;
    confidence: number;
    source: string;
    company_size?: string;
    headquarters?: string;
    company_type?: string;
    size_band?: string;
    target_roles?: string;
}

async function safeJson(res: Response) {
    const text = await res.text();
    try {
        return JSON.parse(text);
    } catch {
        return { error: text || res.statusText || "System error. Is the backend running?" };
    }
}

function getDefaultHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getAuthToken()}`,
        "X-Vanguard-Key": import.meta.env.VITE_VANGUARD_API_KEY || ""
    };
}

export const api = {
    // ---- AUTHENTICATION ---- //
    async signup(firstName: string, lastName: string, email: string, password: string): Promise<{ success: boolean, message?: string, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/auth/signup`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Vanguard-Key": import.meta.env.VITE_VANGUARD_API_KEY || ""
                },
                body: JSON.stringify({ first_name: firstName, last_name: lastName, email, password }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true, message: data.message };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },
    async verify(email: string, code: string): Promise<{ success: boolean, token?: string, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/auth/verify`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Vanguard-Key": import.meta.env.VITE_VANGUARD_API_KEY || ""
                },
                body: JSON.stringify({ email, code }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true, token: data.token };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },
    async login(email: string, password: string): Promise<{ success: boolean, token?: string, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Vanguard-Key": import.meta.env.VITE_VANGUARD_API_KEY || ""
                },
                body: JSON.stringify({ email, password }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true, token: data.token };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },
    async getUser(): Promise<{ email: string, credits: number, role: string, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/auth/me`, {
                headers: getDefaultHeaders(),
            });
            const data = await safeJson(res);
            if (!res.ok) return { email: "", credits: 0, role: "user", error: data.error };
            return { email: data.email || "", credits: data.credits || 0, role: data.role || "user" };
        } catch (e: any) {
            return { email: "", credits: 0, role: "user", error: e.message };
        }
    },
    // ---- ADMIN MANAGEMENT ---- //
    async adminListUsers(): Promise<{ users: any[], error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/admin/users`, {
                headers: getDefaultHeaders(),
            });
            const data = await safeJson(res);
            if (!res.ok) return { users: [], error: data.error };
            return { users: data || [] };
        } catch (e: any) {
            return { users: [], error: e.message };
        }
    },
    async adminUpdateCredits(userId: number, credits: number): Promise<{ success: boolean, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/admin/users/${userId}/credits`, {
                method: "PATCH",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ credits }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },
    async adminUpdateRole(userId: number, role: string): Promise<{ success: boolean, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/admin/users/${userId}/role`, {
                method: "PATCH",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ role }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },
    async adminGetStats(): Promise<{ stats: any, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/admin/stats`, {
                headers: getDefaultHeaders(),
            });
            const data = await safeJson(res);
            if (!res.ok) return { stats: null, error: data.error };
            return { stats: data };
        } catch (e: any) {
            return { stats: null, error: e.message };
        }
    },
    // ------------------------- //
    // ------------------------- //

    async checkHealth(): Promise<boolean> {
        try {
            const res = await fetch(`${API_BASE}/health`); // Health check doesn't need auth
            return res.ok;
        } catch {
            return false;
        }
    },

    async extractCompanies(payload: string): Promise<{ companies: string[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/extract`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ payload }),
            });
            const data = await safeJson(res);
            if (!res.ok) {
                return { companies: [], error: data.error || "Failed request" };
            }
            return { companies: data.companies || [] };
        } catch (e: any) {
            return { companies: [], error: e.message };
        }
    },

    async outreachRun(params: {
        count: number;
        max_per_company: number;
        fetch_metadata: boolean;
        min_score: number;
        companies: string[];
        job_titles: string[];
    }): Promise<{ results: PersonRow[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/outreach/run`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify(params),
            });
            const data = await safeJson(res);
            if (!res.ok) {
                return { results: [], error: data.error || "Failed request" };
            }
            return { results: data.results || [] };
        } catch (e: any) {
            return { results: [], error: e.message };
        }
    },

    async aiSearch(query: string): Promise<{ results: PersonRow[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/ai-search`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ query }),
            });
            const data = await safeJson(res);
            if (!res.ok) {
                return { results: [], error: data.error || "Failed request" };
            }
            return { results: data.results || [] };
        } catch (e: any) {
            return { results: [], error: e.message };
        }
    },

    async runCompanyIntel(companyName: string): Promise<{ intel: any; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/company-intel`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ company_name: companyName }),
            });
            const data = await safeJson(res);
            if (!res.ok) {
                return { intel: null, error: data.error || "Failed request" };
            }
            return { intel: data.intel || null };
        } catch (e: any) {
            return { intel: null, error: e.message };
        }
    },

    async pipelineRun(params: {
        companies: { company_name: string; headcount: number }[];
        max_per_company: number;
    }): Promise<{ results: any[]; skipped: string[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/pipeline/run`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify(params),
            });
            const data = await safeJson(res);
            if (!res.ok) return { results: [], skipped: [], error: data.error };
            return { results: data.results || [], skipped: data.skipped || [] };
        } catch (e: any) {
            return { results: [], skipped: [], error: e.message };
        }
    },

    async findEmail(fullName: string, company: string): Promise<{ email: string; confidence: number; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/find-email`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ full_name: fullName, company }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { email: "", confidence: 0, error: data.error };
            return { email: data.email || "", confidence: data.confidence || 0 };
        } catch (e: any) {
            return { email: "", confidence: 0, error: e.message };
        }
    },

    async getAMFirms(): Promise<{ firms: any[]; total: number; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/am-firms`, {
                headers: getDefaultHeaders()
            });
            const data = await safeJson(res);
            if (!res.ok) return { firms: [], total: 0, error: data.error };
            return { firms: data.firms || [], total: data.total || 0 };
        } catch (e: any) {
            return { firms: [], total: 0, error: e.message };
        }
    },

    async amPipelineRun(firms: string[]): Promise<{ results: any[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/am-pipeline/run`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ firms }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { results: [], error: data.error };
            return { results: data.results || [] };
        } catch (e: any) {
            return { results: [], error: e.message };
        }
    },

    async getKeys(): Promise<{ keys: Record<string, any>; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/keys`, {
                headers: getDefaultHeaders()
            });
            const data = await safeJson(res);
            if (!res.ok) return { keys: {}, error: data.error };
            return { keys: data || {} };
        } catch (e: any) {
            return { keys: {}, error: e.message };
        }
    },

    async saveKeys(keys: Record<string, string>): Promise<{ success: boolean; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/keys`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify(keys),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    },

    async getModel(): Promise<{ provider: string, model: string, error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/model`, {
                headers: getDefaultHeaders()
            });
            const data = await safeJson(res);
            if (!res.ok) return { provider: "", model: "", error: data.error };
            return { provider: data.provider || "openai", model: data.model || "gpt-4o-mini" };
        } catch (e: any) {
            return { provider: "", model: "", error: e.message };
        }
    },

    async setModel(provider: string, model: string): Promise<{ success: boolean; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/model`, {
                method: "POST",
                headers: getDefaultHeaders(),
                body: JSON.stringify({ provider, model }),
            });
            const data = await safeJson(res);
            if (!res.ok) return { success: false, error: data.error };
            return { success: true };
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    }
};
