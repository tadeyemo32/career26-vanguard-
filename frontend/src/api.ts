export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8765/api";

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

export const api = {
    async checkHealth(): Promise<boolean> {
        try {
            const res = await fetch(`${API_BASE}/health`);
            return res.ok;
        } catch {
            return false;
        }
    },

    async extractCompanies(payload: string): Promise<{ companies: string[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/extract`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
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
                headers: { "Content-Type": "application/json" },
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
                headers: { "Content-Type": "application/json" },
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
                headers: { "Content-Type": "application/json" },
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
    }
};
