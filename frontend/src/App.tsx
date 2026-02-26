import { useState, useEffect } from 'react';
import { api, getAuthToken, setAuthToken } from './api';
import type { PersonRow } from './api';
import { Search, Mail, Building2, Briefcase, ChevronRight, CheckCircle2, AlertCircle, Loader2, LogOut } from 'lucide-react';
import * as xlsx from 'xlsx';
import { AuthScreen } from './Auth';

function App() {
    const [activeTab, setActiveTab] = useState('extract');
    const [isAuthenticated, setIsAuthenticated] = useState(!!getAuthToken());
    const [user, setUser] = useState<{ email: string, credits: number } | null>(null);

    useEffect(() => {
        if (isAuthenticated) {
            api.getUser().then(res => {
                if (!res.error) setUser({ email: res.email, credits: res.credits });
            });
        }
    }, [isAuthenticated]);

    if (!isAuthenticated) {
        return <AuthScreen onAuthSuccess={() => setIsAuthenticated(true)} />;
    }

    const handleLogout = () => {
        setAuthToken("");
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <div className="flex h-screen w-full bg-[#09090f] text-[#d8dce8] font-sans selection:bg-[#3b5cbd] selection:text-white">
            {/* Sidebar with Logout overlay logic potentially. We will pass handleLogout below */}
            <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onLogout={handleLogout} user={user} />

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden">
                <div className="max-w-6xl mx-auto p-8 border-l border-[#1e2235] flex-1 overflow-y-auto">
                    {activeTab === 'extract' && <WorkflowExtractTab />}
                    {activeTab === 'email' && <SimpleEmailFinderTab />}
                    {activeTab === 'search' && <SmartSearchTab />}
                    {activeTab === 'assetmanager' && <AssetManagerTab />}
                </div>
            </div>
        </div>
    );
}

function Sidebar({ activeTab, setActiveTab, onLogout, user }: { activeTab: string, setActiveTab: (t: string) => void, onLogout: () => void, user: { email: string, credits: number } | null }) {
    const tabs = [
        { id: 'extract', label: 'Company Extraction', icon: Building2 },
        { id: 'email', label: 'Email Finder', icon: Mail },
        { id: 'search', label: 'Smart Search', icon: Search },
        { id: 'assetmanager', label: 'AM Outreach', icon: Briefcase },
    ];

    return (
        <div className="w-64 bg-[#13151f] flex flex-col pt-8 px-4 h-full relative border-r border-[#1e2235]">
            <div className="mb-10 px-2 flex-col flex gap-0.5">
                <h1 className="text-[#d8dce8] font-semibold text-lg flex items-center gap-2 tracking-wide">
                    <Briefcase size={20} className="text-[#3b5cbd]" />
                    VANGUARD
                </h1>
                <p className="text-[#6b7494] text-[11px] font-medium tracking-widest uppercase">Agentic Desktop</p>
            </div>

            <nav className="flex-1 space-y-2">
                {tabs.map(tab => {
                    const active = activeTab === tab.id;
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group ${active ? 'bg-[#3b5cbd] text-white shadow-[0_0_15px_rgba(59,92,189,0.3)]' : 'text-[#a1a7c0] hover:bg-[#1e2330] hover:text-[#d8dce8]'
                                }`}
                        >
                            <div className="flex items-center gap-3">
                                <Icon size={16} className={active ? 'opacity-100 text-white' : 'opacity-70 group-hover:text-[#3b5cbd] transition-colors'} />
                                <span className="font-medium">{tab.label}</span>
                            </div>
                            {active && <ChevronRight size={14} className="opacity-70" />}
                        </button>
                    )
                })}
            </nav>

            {user && (
                <div className="mb-4 px-3 py-3 rounded-lg border border-[#262d42] bg-[#0f1018]">
                    <div className="text-xs text-[#6b7494] mb-1 font-medium select-none truncate">
                        {user.email}
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-white">Credits</span>
                        <span className="text-xs font-mono font-medium text-[#34d399] tracking-tight">{user.credits.toLocaleString()}</span>
                    </div>
                </div>
            )}

            <button
                onClick={onLogout}
                className="mb-6 w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 text-[#a1a7c0] hover:bg-red-500/10 hover:text-red-400 group"
            >
                <LogOut size={16} />
                <span className="font-medium">Logout</span>
            </button>
        </div>
    );
}

function ProfessionalTable({ data, filename }: { data: PersonRow[], filename: string }) {
    if (!data || data.length === 0) return null;

    const handleDownload = () => {
        const ws = xlsx.utils.json_to_sheet(data);
        const wb = xlsx.utils.book_new();
        xlsx.utils.book_append_sheet(wb, ws, "People");
        xlsx.writeFile(wb, `${filename}.xlsx`);
    };

    return (
        <div className="mt-8">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white">Extracted Data</h3>
                <button onClick={handleDownload} className="text-sm bg-[#1e2235] hover:bg-[#262d42] px-4 py-2 rounded-lg transition-colors">
                    Download CSV/Excel
                </button>
            </div>
            <div className="overflow-hidden rounded-xl border border-[#1e2235] bg-[#0f1018]">
                <table className="w-full text-left text-sm">
                    <thead className="bg-[#13151f]">
                        <tr>
                            <th className="px-6 py-4 font-semibold text-[#6b7494]">Name</th>
                            <th className="px-6 py-4 font-semibold text-[#6b7494]">Company</th>
                            <th className="px-6 py-4 font-semibold text-[#6b7494]">Position</th>
                            <th className="px-6 py-4 font-semibold text-[#6b7494]">Email</th>
                            <th className="px-6 py-4 font-semibold text-[#6b7494]">Confidence</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2235]">
                        {data.map((row, i) => (
                            <tr key={i} className="hover:bg-[#13151f] transition-colors">
                                <td className="px-6 py-4">
                                    <a href={row.link} target="_blank" rel="noreferrer" className="text-[#3b5cbd] hover:text-[#4d70d9]">{row.name}</a>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="font-medium">{row.company}</div>
                                    {(row.company_type || row.size_band) && (
                                        <div className="text-xs text-[#6b7494] mt-1">{row.company_type} • {row.size_band}</div>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-[#d8dce8]">{row.title}</td>
                                <td className="px-6 py-4 font-mono text-sm">{row.email || '—'}</td>
                                <td className="px-6 py-4">
                                    {row.email ? (
                                        <div className="flex items-center space-x-2">
                                            <div className="h-2 w-16 bg-[#1e2235] rounded-full overflow-hidden">
                                                <div className="h-full bg-[#34d399] transition-all" style={{ width: `${row.confidence * 100}%` }}></div>
                                            </div>
                                            <span className="text-xs text-[#6b7494]">{Math.round(row.confidence * 100)}%</span>
                                        </div>
                                    ) : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// -----------------------------------------------------
// TABS
// -----------------------------------------------------

function WorkflowExtractTab() {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<PersonRow[]>([]);
    const [error, setError] = useState('');

    const handleProcess = async () => {
        setLoading(true);
        setError('');
        // 1. Extract companies
        const exRes = await api.extractCompanies(input);
        if (exRes.error || !exRes.companies || exRes.companies.length === 0) {
            setError(exRes.error || "No companies found in text.");
            setLoading(false);
            return;
        }

        // Prepare headcount defaults (or we could fetch sizes theoretically)
        const reqCompanies = exRes.companies.map(c => ({ company_name: c, headcount: 100 })); // Assuming Mid-Tier default for raw extractions

        // 2. Fetch People safely
        const pipeRes = await api.pipelineRun({ companies: reqCompanies, max_per_company: 3 });
        if (pipeRes.error) {
            setError(pipeRes.error);
        } else {
            const flattened = [] as PersonRow[];
            pipeRes.results.forEach(r => r.people?.forEach((p: PersonRow) => flattened.push(p)));
            setResults(flattened);
        }
        setLoading(false);
    };

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-bold mb-2">Career26 Extractor</h1>
            <p className="text-[#6b7494] mb-8">Paste arbitrary text, list of companies, or documents. We'll automatically identify companies, apply the Headcount-Role rule, and find people.</p>

            <div className="bg-[#13151f] rounded-2xl p-6 border border-[#1e2235] shadow-xl">
                <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Paste meeting notes, CSV rows, or bulk text here..."
                    className="w-full h-40 bg-[#0f1018] border border-[#262d42] rounded-xl p-4 text-[#d8dce8] placeholder:text-[#363d52] focus:outline-none focus:border-[#3b5cbd] transition-colors resize-none mb-4"
                />
                <button
                    onClick={handleProcess}
                    disabled={loading || !input.trim()}
                    className="w-full bg-[#3b5cbd] hover:bg-[#4d70d9] text-white px-6 py-3 rounded-xl font-medium transition-all focus:outline-none flex justify-center items-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? <Loader2 className="animate-spin" /> : <span>Extract Companies & Find Prospects</span>}
                </button>
                {error && <div className="mt-4 p-4 bg-[rgba(248,113,113,0.1)] border border-[#f87171] text-[#f87171] rounded-xl text-sm flex items-center"><AlertCircle size={16} className="mr-2" /> {error}</div>}
            </div>

            <ProfessionalTable data={results} filename="Extractor_Results" />
        </div>
    );
}

function SimpleEmailFinderTab() {
    const [fullName, setFullName] = useState('');
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);

    const handleSearch = async () => {
        setLoading(true);
        setResult(null);
        const res = await api.findEmail(fullName, company);
        setResult(res);
        setLoading(false);
    };

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-bold mb-2">Simple Email Finder</h1>
            <p className="text-[#6b7494] mb-8">Directly query Anymail and Hunter.io APIs securely. The input is passed unaltered natively to the endpoints.</p>

            <div className="bg-[#13151f] rounded-2xl p-6 border border-[#1e2235] shadow-xl max-w-2xl">
                <div className="space-y-4 mb-6">
                    <div>
                        <label className="block text-sm font-medium text-[#6b7494] mb-2">Full Name</label>
                        <input
                            type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                            className="w-full bg-[#0f1018] border border-[#262d42] rounded-xl px-4 py-3 focus:outline-none focus:border-[#3b5cbd] transition-colors"
                            placeholder="e.g. John Doe"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-[#6b7494] mb-2">Company Name or Domain</label>
                        <input
                            type="text" value={company} onChange={e => setCompany(e.target.value)}
                            className="w-full bg-[#0f1018] border border-[#262d42] rounded-xl px-4 py-3 focus:outline-none focus:border-[#3b5cbd] transition-colors"
                            placeholder="e.g. Goldman Sachs or gs.com"
                        />
                    </div>
                </div>

                <button
                    onClick={handleSearch} disabled={loading || !fullName || !company}
                    className="w-full bg-[#3b5cbd] hover:bg-[#4d70d9] text-white px-6 py-3 rounded-xl font-medium transition-all flex justify-center items-center disabled:opacity-50"
                >
                    {loading ? <Loader2 className="animate-spin" /> : <span>Resolve Email Address</span>}
                </button>

                {result && (
                    <div className="mt-8">
                        {result.error ? (
                            <div className="p-4 bg-[rgba(248,113,113,0.1)] border border-[#f87171] text-[#f87171] rounded-xl flex items-center text-sm">
                                <AlertCircle size={16} className="mr-2" /> {result.error}
                            </div>
                        ) : result.email ? (
                            <div className="p-6 border border-[#34d399] bg-[rgba(52,211,153,0.05)] rounded-2xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-10"><CheckCircle2 size={100} /></div>
                                <div className="text-sm text-[#34d399] font-medium mb-1">Verified Address Found</div>
                                <div className="text-2xl font-mono text-white mb-4">{result.email}</div>
                                <div className="flex items-center space-x-3">
                                    <span className="text-xs text-[#6b7494]">Confidence Level</span>
                                    <div className="h-1.5 w-32 bg-[#1e2235] rounded-full overflow-hidden">
                                        <div className="h-full bg-[#34d399]" style={{ width: `${result.confidence * 100}%` }}></div>
                                    </div>
                                    <span className="text-xs font-medium text-white">{Math.round(result.confidence * 100)}%</span>
                                </div>
                            </div>
                        ) : (
                            <div className="p-4 bg-[#1e2235] text-[#d8dce8] rounded-xl text-center text-sm">
                                No verifiable email could be found via direct API queries.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function SmartSearchTab() {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<PersonRow[]>([]);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = async () => {
        setLoading(true); setError('');
        const res = await api.aiSearch(query); // limit needs to be passed via API if possible, let's assume it handled internally or modify API call if needed. (I'll stick to query for now, since in handlers.go it has limit field)
        if (res.error) setError(res.error);
        else setResults(res.results);
        setLoading(false);
    };

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-bold mb-2">Smart AI Search Engine</h1>
            <p className="text-[#6b7494] mb-8">Search conceptually. E.g. "early careers head of point72" or "career 26 fellows". We'll interpret it, scrape LinkedIn, and resolve emails using all our APIs sequentially.</p>

            <div className="bg-[#13151f] rounded-2xl p-6 border border-[#1e2235] shadow-xl mb-8 flex space-x-4">
                <input
                    type="text" value={query} onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    className="flex-1 bg-[#0f1018] border border-[#262d42] rounded-xl px-4 py-3 focus:outline-none focus:border-[#3b5cbd] transition-colors"
                    placeholder="Describe who you want to find..."
                />
                <button
                    onClick={handleSearch} disabled={loading || !query}
                    className="bg-[#3b5cbd] hover:bg-[#4d70d9] text-white px-8 py-3 rounded-xl font-medium transition-all flex items-center disabled:opacity-50"
                >
                    {loading ? <Loader2 className="animate-spin" /> : <><Search size={18} className="mr-2" /> Search</>}
                </button>
            </div>

            {error && <div className="mb-8 p-4 bg-[rgba(248,113,113,0.1)] border border-[#f87171] text-[#f87171] rounded-xl text-sm flex items-center"><AlertCircle size={16} className="mr-2" /> {error}</div>}

            <ProfessionalTable data={results} filename="SmartSearch_Results" />
        </div>
    );
}

function AssetManagerTab() {
    const [firms, setFirms] = useState<any[]>([]);
    const [loadingList, setLoadingList] = useState(false);

    const [selectedFirm, setSelectedFirm] = useState<string>('');
    const [processing, setProcessing] = useState(false);
    const [results, setResults] = useState<PersonRow[]>([]);
    const [error, setError] = useState('');

    useEffect(() => {
        async function load() {
            setLoadingList(true);
            const res = await api.getAMFirms();
            if (!res.error) setFirms(res.firms);
            setLoadingList(false);
        }
        load();
    }, []);

    const handleProcess = async () => {
        if (!selectedFirm) return;
        setProcessing(true); setError(''); setResults([]);
        const res = await api.amPipelineRun([selectedFirm]);
        if (res.error) setError(res.error);
        else {
            // Output from amPipelineRun is { results: [ { firm, people, error } ] }
            if (res.results.length > 0) {
                const dataRow = res.results[0];
                if (dataRow.error) setError(dataRow.error);
                else setResults(dataRow.people || []);
            }
        }
        setProcessing(false);
    };

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-bold mb-2">AM Outreach Pipeline</h1>
            <p className="text-[#6b7494] mb-8">Process Asset Management firms from the Companies House database. The AI validates firm type and executes the Career26 role rule.</p>

            <div className="bg-[#13151f] rounded-2xl p-6 border border-[#1e2235] shadow-xl mb-8">
                <div className="flex space-x-4 mb-4">
                    <select
                        value={selectedFirm} onChange={e => setSelectedFirm(e.target.value)}
                        className="flex-1 bg-[#0f1018] border border-[#262d42] rounded-xl px-4 py-3 focus:outline-none focus:border-[#3b5cbd] text-[#d8dce8]"
                    >
                        <option value="" disabled>{loadingList ? 'Loading Companies House List...' : 'Select a UK Asset Management Firm'}</option>
                        {firms.map((f, i) => (
                            <option key={i} value={f.company_name}>{f.company_name} ({f.company_type || 'Unknown Type'})</option>
                        ))}
                    </select>

                    <button
                        onClick={handleProcess} disabled={processing || !selectedFirm}
                        className="bg-[#3b5cbd] hover:bg-[#4d70d9] text-white px-6 py-3 rounded-xl font-medium transition-all flex items-center disabled:opacity-50 min-w-[200px] justify-center"
                    >
                        {processing ? <Loader2 className="animate-spin" /> : <><ChevronRight size={18} className="mr-2" /> Evaluate & Mine</>}
                    </button>
                </div>
                {error && <div className="p-4 bg-[rgba(248,113,113,0.1)] border border-[#f87171] text-[#f87171] rounded-xl text-sm flex items-center"><AlertCircle size={16} className="mr-2" /> Workflow Action Failed: {error}</div>}
            </div>

            <ProfessionalTable data={results} filename={`${selectedFirm}_Outreach_Targets`} />
        </div>
    );
}

export default App;
