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

export const api = {
    async checkHealth(): Promise<boolean> {
        try {
            const res = await fetch(`${API_BASE}/health`);
            return res.ok;
        } catch {
            return false;
        }
    },

    async outreachRun(params: {
        count: number;
        max_per_company: number;
        fetch_metadata: boolean;
        min_score: number;
    }): Promise<{ results: PersonRow[]; error?: string }> {
        try {
            const res = await fetch(`${API_BASE}/outreach/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params),
            });
            if (!res.ok) {
                const err = await res.json();
                return { results: [], error: err.error || "Failed request" };
            }
            const data = await res.json();
            return { results: data.results || [] };
        } catch (e: any) {
            return { results: [], error: e.message };
        }
    },
};
