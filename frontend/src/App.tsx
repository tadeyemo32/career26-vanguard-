import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity, Search, Settings, Check, Download, Building,
  Terminal, Layers, Mail, ExternalLink, RefreshCw, Upload,
  X, Key, Cpu, FileText, Eye, EyeOff, Trash2, Lock, AlertTriangle,
  ShieldCheck, LogOut, Users, Trophy, Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, getAuthToken, setAuthToken } from './api';
import type { PersonRow } from './api';
import { parseFile } from './fileParser';
import { AuthScreen } from './Auth';
import './index.css';

// ── Auth types ────────────────────────────────────────────────────────────────
interface User { email: string; credits: number; role: string; }

const JOB_TITLES = [
  "Director", "Partner", "VP", "Managing Director", "Principal", "Associate",
  "Head of Business Development", "Head of Investor Relations", "CFO", "CEO",
  "Analyst", "Graduate", "Intern", "Early Careers", "Talent Acquisition", "Recruiter",
  "HR Director", "Head of People", "Chief People Officer", "General Counsel",
  "Legal Counsel", "Head of Operations", "COO", "Head of Strategy",
  "Business Development Manager", "Account Manager",
];

// File-accept string for FileUploadZone
const ACCEPTED = '.csv,.txt,.tsv,.xlsx,.xls,.ods,.pdf,.numbers';


// ── Key status type ───────────────────────────────────────────────────────────
type KeyStatus = Record<string, boolean>;

// ── Key requirement definitions ───────────────────────────────────────────────
const KEY_REQUIREMENTS: Record<string, { keys: string[]; label: string }[]> = {
  Pipeline: [
    { keys: ['SERPAPI_KEY'], label: 'SerpAPI (LinkedIn search)' },
    { keys: ['OPENAI_API_KEY'], label: 'OpenAI (company extraction)' },
  ],
  'Find Email': [
    { keys: ['ANYMAIL_API_KEY', 'HUNTER_API_KEY'], label: 'Anymail Finder or Hunter.io' },
  ],
  'AI Search': [
    { keys: ['SERPAPI_KEY'], label: 'SerpAPI (search)' },
    { keys: ['OPENAI_API_KEY'], label: 'OpenAI (query enhancement)' },
  ],
  'Entity Intel': [
    { keys: ['SERPAPI_KEY'], label: 'SerpAPI (company lookup)' },
    { keys: ['OPENAI_API_KEY'], label: 'OpenAI (intel classification)' },
  ],
};

// ── Key Gate ──────────────────────────────────────────────────────────────────
function KeyGate({ tab, keyStatus, onGoToSettings }: {
  tab: string;
  keyStatus: KeyStatus;
  onGoToSettings: () => void;
  children: React.ReactNode;
}) {
  const reqs = KEY_REQUIREMENTS[tab] ?? [];
  const missing = reqs.filter(r => !r.keys.some(k => keyStatus[k]));
  if (missing.length === 0) return null; // all good, parent renders children

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="max-w-lg bg-[#0f1018] border border-[#f87171]/25 rounded-xl p-6 flex gap-4">
      <div className="w-9 h-9 rounded-lg bg-[#f87171]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Lock size={16} className="text-[#f87171]" />
      </div>
      <div>
        <div className="text-sm font-semibold text-white mb-1">API keys required</div>
        <p className="text-[12px] text-[#6b7494] mb-4 leading-relaxed">
          This feature needs the following keys to be configured before it can run:
        </p>
        <ul className="space-y-1.5 mb-5">
          {missing.map(r => (
            <li key={r.label} className="flex items-center gap-2 text-[12px] text-[#f87171]">
              <AlertTriangle size={11} /> {r.label}
            </li>
          ))}
        </ul>
        <button onClick={onGoToSettings}
          className="flex items-center gap-2 text-[13px] font-medium text-white bg-[#3b5cbd] hover:bg-[#4d70d9] px-4 py-2 rounded-lg border border-white/10 transition-all">
          <Key size={13} /> Open Settings
        </button>
      </div>
    </motion.div>
  );
}

// ── Results Table ─────────────────────────────────────────────────────────────
function ResultsTable({ rows, onExport }: { rows: PersonRow[]; onExport?: () => void }) {
  if (!rows.length) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="bg-[#0f1018] border border-[#1e2235] rounded-xl overflow-hidden mt-6">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e2235]">
        <span className="text-xs text-[#6b7494] font-medium">{rows.length} result{rows.length !== 1 ? 's' : ''}</span>
        {onExport && (
          <button onClick={onExport}
            className="flex items-center gap-1.5 text-xs text-[#6b7494] hover:text-white px-3 py-1.5 rounded-md bg-[#141620] border border-[#1e2235] hover:border-[#262d42] transition-all">
            <Download size={12} /> Export CSV
          </button>
        )}
      </div>
      <div className="overflow-auto max-h-[480px]">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-[#0d0f16] border-b border-[#1e2235]">
              {['Name', 'Title', 'Company', 'Email', 'Confidence', 'LinkedIn'].map(h => (
                <th key={h} className="text-left text-[10px] font-semibold tracking-wide uppercase text-[#6b7494] px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-[#1e2235] hover:bg-[#3b5cbd]/5 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#1e2d56] to-[#101520] border border-[#2a3a60] text-[#a0b4f0] text-xs font-semibold flex items-center justify-center flex-shrink-0">
                      {r.name.charAt(0)}
                    </div>
                    <span className="font-medium text-white">{r.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-[#6b7494]">{r.title || '—'}</td>
                <td className="px-4 py-3 font-medium text-[#d8dce8]">{r.company}</td>
                <td className="px-4 py-3">
                  {r.email
                    ? <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium text-xs"><Check size={12} />{r.email}</span>
                    : <span className="text-[#363d52] text-xs">Not found</span>}
                </td>
                <td className="px-4 py-3">
                  {r.email ? (
                    <div className="flex items-center gap-2">
                      <div className="w-14 h-1 bg-[#1e2235] rounded-full overflow-hidden">
                        <div className="h-full bg-[#3b5cbd] rounded-full transition-all duration-500" style={{ width: `${Math.round(r.confidence * 100)}%` }} />
                      </div>
                      <span className="text-[11px] text-[#6b7494]">{Math.round(r.confidence * 100)}%</span>
                    </div>
                  ) : <span className="text-[#363d52]">—</span>}
                </td>
                <td className="px-4 py-3">
                  {r.link
                    ? <a href={r.link} target="_blank" rel="noreferrer" className="text-[#6b7494] hover:text-[#4d70d9] transition-colors"><ExternalLink size={14} /></a>
                    : <span className="text-[#363d52]">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

// ── File Upload Zone ──────────────────────────────────────────────────────────
function FileUploadZone({ onText }: { onText: (t: string) => void }) {
  const [files, setFiles] = useState<Array<{ name: string; rows: number; text: string }>>([]);
  const [parsing, setParsing] = useState(false);
  const [drag, setDrag] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const process = useCallback(async (fileList: FileList) => {
    setParsing(true);
    const added: typeof files = [];
    for (const f of Array.from(fileList)) {
      const r = await parseFile(f);
      if (!r.error && r.text.trim()) added.push({ name: r.filename, rows: r.rowCount ?? 0, text: r.text });
    }
    const next = [...files, ...added];
    setFiles(next);
    onText(next.map(f => f.text).join('\n'));
    setParsing(false);
  }, [files, onText]);

  const remove = (i: number) => {
    const next = files.filter((_, idx) => idx !== i);
    setFiles(next);
    onText(next.map(f => f.text).join('\n'));
  };

  return (
    <div className="max-w-xl">
      <div
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files.length) process(e.dataTransfer.files); }}
        onClick={() => ref.current?.click()}
        className={`flex items-center justify-center gap-3 border border-dashed rounded-xl px-6 py-8 cursor-pointer transition-all text-sm select-none
          ${drag ? 'border-[#3b5cbd] bg-[#3b5cbd]/8 text-white' : 'border-[#262d42] bg-[#0f1018] text-[#6b7494] hover:border-[#3b5cbd]/60 hover:text-[#d8dce8]'}`}
      >
        <input ref={ref} type="file" multiple accept={ACCEPTED} className="hidden"
          onChange={e => e.target.files && process(e.target.files)} />
        {parsing
          ? <><RefreshCw size={18} className="spin text-[#3b5cbd]" /><span>Parsing…</span></>
          : <><Upload size={18} /><span>Drop files or click to upload</span><span className="text-[10px] text-[#363d52] ml-1">CSV · XLSX · PDF · TXT</span></>}
      </div>
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {files.map((f, i) => (
            <motion.div key={i} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 bg-[#111825] border border-[#1e2235] rounded-full px-3 py-1.5 text-xs text-[#d8dce8]">
              <FileText size={11} className="text-[#6b7494]" />
              <span>{f.name}</span>
              <span className="text-[#363d52]">{f.rows} rows</span>
              <button onClick={e => { e.stopPropagation(); remove(i); }} className="text-[#6b7494] hover:text-red-400 transition-colors ml-1"><X size={11} /></button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Company Autocomplete ───────────────────────────────────────────────────────
const COMPANY_SUGGESTIONS: { name: string; domain: string; category: string }[] = [
  { name: 'Goldman Sachs', domain: 'gs.com', category: 'Investment Bank' },
  { name: 'JP Morgan', domain: 'jpmorgan.com', category: 'Investment Bank' },
  { name: 'Morgan Stanley', domain: 'morganstanley.com', category: 'Investment Bank' },
  { name: 'Barclays', domain: 'barclays.com', category: 'Bank' },
  { name: 'HSBC', domain: 'hsbc.com', category: 'Bank' },
  { name: 'Deutsche Bank', domain: 'db.com', category: 'Investment Bank' },
  { name: 'UBS', domain: 'ubs.com', category: 'Investment Bank' },
  { name: 'Credit Suisse', domain: 'credit-suisse.com', category: 'Investment Bank' },
  { name: 'Citigroup', domain: 'citi.com', category: 'Bank' },
  { name: 'BNP Paribas', domain: 'bnpparibas.com', category: 'Bank' },
  { name: 'Societe Generale', domain: 'societegenerale.com', category: 'Bank' },
  { name: 'Nomura', domain: 'nomura.com', category: 'Investment Bank' },
  { name: 'Wells Fargo', domain: 'wellsfargo.com', category: 'Bank' },
  { name: 'Bank of America', domain: 'bankofamerica.com', category: 'Bank' },
  { name: 'Lazard', domain: 'lazard.com', category: 'Investment Bank' },
  { name: 'Rothschild & Co', domain: 'rothschildandco.com', category: 'Investment Bank' },
  { name: 'Evercore', domain: 'evercore.com', category: 'Investment Bank' },
  { name: 'Jefferies', domain: 'jefferies.com', category: 'Investment Bank' },
  { name: 'Mizuho', domain: 'mizuho-fg.com', category: 'Investment Bank' },
  { name: 'BlackRock', domain: 'blackrock.com', category: 'Asset Manager' },
  { name: 'Vanguard', domain: 'vanguard.com', category: 'Asset Manager' },
  { name: 'Fidelity', domain: 'fidelity.com', category: 'Asset Manager' },
  { name: 'State Street', domain: 'statestreet.com', category: 'Asset Manager' },
  { name: 'PIMCO', domain: 'pimco.com', category: 'Asset Manager' },
  { name: 'T. Rowe Price', domain: 'troweprice.com', category: 'Asset Manager' },
  { name: 'Invesco', domain: 'invesco.com', category: 'Asset Manager' },
  { name: 'Franklin Templeton', domain: 'franklintempleton.com', category: 'Asset Manager' },
  { name: 'Capital Group', domain: 'capitalgroup.com', category: 'Asset Manager' },
  { name: 'Wellington Management', domain: 'wellington.com', category: 'Asset Manager' },
  { name: 'Schroders', domain: 'schroders.com', category: 'Asset Manager' },
  { name: 'abrdn', domain: 'abrdn.com', category: 'Asset Manager' },
  { name: 'Man Group', domain: 'man.com', category: 'Hedge Fund' },
  { name: 'Brevan Howard', domain: 'brevanhoward.com', category: 'Hedge Fund' },
  { name: 'AQR Capital', domain: 'aqr.com', category: 'Hedge Fund' },
  { name: 'Two Sigma', domain: 'twosigma.com', category: 'Hedge Fund' },
  { name: 'Renaissance Technologies', domain: 'rentec.com', category: 'Hedge Fund' },
  { name: 'Citadel', domain: 'citadel.com', category: 'Hedge Fund' },
  { name: 'Millennium Management', domain: 'mlp.com', category: 'Hedge Fund' },
  { name: 'Point72', domain: 'point72.com', category: 'Hedge Fund' },
  { name: 'Bridgewater Associates', domain: 'bridgewater.com', category: 'Hedge Fund' },
  { name: 'Atomico', domain: 'atomico.com', category: 'Venture Capital' },
  { name: 'Apollo Global', domain: 'apollo.com', category: 'Private Equity' },
  { name: 'Carlyle Group', domain: 'carlyle.com', category: 'Private Equity' },
  { name: 'KKR', domain: 'kkr.com', category: 'Private Equity' },
  { name: 'Blackstone', domain: 'blackstone.com', category: 'Private Equity' },
  { name: 'Bain Capital', domain: 'baincapital.com', category: 'Private Equity' },
  { name: 'General Atlantic', domain: 'generalatlantic.com', category: 'Private Equity' },
  { name: 'Ares Management', domain: 'aresmgmt.com', category: 'Private Equity' },
  { name: 'Blue Owl', domain: 'blueowl.com', category: 'Private Equity' },
  { name: 'TPG', domain: 'tpg.com', category: 'Private Equity' },
  { name: 'Warburg Pincus', domain: 'warburgpincus.com', category: 'Private Equity' },
  { name: 'McKinsey & Company', domain: 'mckinsey.com', category: 'Consulting' },
  { name: 'Bain & Company', domain: 'bain.com', category: 'Consulting' },
  { name: 'Boston Consulting Group', domain: 'bcg.com', category: 'Consulting' },
  { name: 'Deloitte', domain: 'deloitte.com', category: 'Consulting' },
  { name: 'KPMG', domain: 'kpmg.com', category: 'Consulting' },
  { name: 'PwC', domain: 'pwc.com', category: 'Consulting' },
  { name: 'EY', domain: 'ey.com', category: 'Consulting' },
];

function CompanyAutocomplete({ value, onChange, onSubmit }: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  const [focused, setFocused] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const query = value.trim().toLowerCase();

  const suggestions = query.length >= 1
    ? COMPANY_SUGGESTIONS
      .map(s => {
        const nameLower = s.name.toLowerCase();
        const domainLower = s.domain.toLowerCase();
        let score = 0;
        if (nameLower.startsWith(query)) score = 100;
        else if (nameLower.includes(query)) score = 60;
        else if (domainLower.startsWith(query)) score = 40;
        else if (domainLower.includes(query)) score = 20;
        query.split(' ').forEach(tok => {
          if (tok.length > 1 && nameLower.includes(tok)) score += 10;
        });
        return { ...s, score };
      })
      .filter(s => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8)
    : [];

  const showDropdown = focused && suggestions.length > 0;

  useEffect(() => { setHighlightIdx(0); }, [query]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocused(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const select = (s: typeof COMPANY_SUGGESTIONS[0]) => {
    onChange(s.domain); setFocused(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showDropdown) { if (e.key === 'Enter') onSubmit(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlightIdx(i => Math.min(i + 1, suggestions.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlightIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); if (suggestions[highlightIdx]) select(suggestions[highlightIdx]); else onSubmit(); }
    else if (e.key === 'Escape') { setFocused(false); }
    else if (e.key === 'Tab') { setFocused(false); }
  };

  return (
    <div ref={containerRef} className="relative">
      <input
        value={value}
        onChange={e => { onChange(e.target.value); setFocused(true); }}
        onFocus={() => { setFocused(true); }}
        onKeyDown={handleKeyDown}
        placeholder="Man Group or mangroup.com"
        autoComplete="off"
        spellCheck={false}
        className="w-full bg-[#09090f] border border-[#262d42] rounded-lg px-4 py-2.5 text-sm text-white placeholder-[#363d52] focus:outline-none focus:border-[#3b5cbd] focus:ring-1 focus:ring-[#3b5cbd]/30 transition-all"
      />
      <AnimatePresence>
        {showDropdown && (
          <motion.div
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute z-50 left-0 right-0 mt-1.5 bg-[#0d0f1a] border border-[#1e2235] rounded-xl overflow-hidden shadow-2xl shadow-black/60"
          >
            {suggestions.map((s, idx) => (
              <button
                key={s.name}
                onMouseDown={e => { e.preventDefault(); select(s); }}
                onMouseEnter={() => setHighlightIdx(idx)}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-left transition-colors border-b border-[#141620] last:border-0
                  ${idx === highlightIdx ? 'bg-[#3b5cbd]/15' : 'hover:bg-[#11141e]'}`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-md bg-[#141b2e] border border-[#1e2a45] text-[9px] font-black text-[#728bee] flex items-center justify-center flex-shrink-0 tracking-wide">
                    {s.name.charAt(0)}
                  </div>
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium text-white truncate">{s.name}</div>
                    <div className="text-[10px] text-[#4a5273] truncate">{s.domain}</div>
                  </div>
                </div>
                <span className="text-[9px] font-semibold uppercase tracking-wider text-[#363d52] ml-3 flex-shrink-0">{s.category}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Find Email Tab ─────────────────────────────────────────────────────────────
function FindEmailTab({ keyStatus, onGoToSettings }: { keyStatus: KeyStatus; onGoToSettings: () => void }) {
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [resolve, setResolve] = useState(true);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [email, setEmail] = useState('');
  const [conf, setConf] = useState(0);
  const [source, setSource] = useState('');
  const [err, setErr] = useState('');

  const missingEmail = !keyStatus['ANYMAIL_API_KEY'] && !keyStatus['HUNTER_API_KEY'];

  const find = async () => {
    if (!name || !company) return;
    setLoading(true); setLogs([]); setEmail(''); setConf(0); setErr(''); setSource('');
    const res = await api.findEmail(name.trim(), company.trim(), resolve);
    if (res.logs?.length) setLogs(res.logs);
    if (res.email) { setEmail(res.email); setConf(res.confidence); setSource(res.source || ''); }
    if (!res.email && !res.logs?.length) setErr(res.error || 'No result returned');
    setLoading(false);
  };

  if (missingEmail) {
    return <KeyGate tab="Find Email" keyStatus={keyStatus} onGoToSettings={onGoToSettings}><></></KeyGate>;
  }

  const confColor = conf >= 0.9 ? 'text-emerald-400' : conf >= 0.6 ? 'text-yellow-400' : 'text-orange-400';
  const confLabel = conf >= 0.9 ? 'Verified by API' : conf >= 0.6 ? 'High confidence' : 'Medium confidence';

  return (
    <div className="max-w-xl space-y-5">
      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-6 space-y-5">
        {/* Active sources indicator */}
        <div className="flex items-center gap-2 text-[11px] text-[#6b7494]">
          Sources active:
          {keyStatus['ANYMAIL_API_KEY'] && <span className="bg-emerald-400/10 text-emerald-400 px-2 py-0.5 rounded-full">Anymail</span>}
          {keyStatus['HUNTER_API_KEY'] && <span className="bg-emerald-400/10 text-emerald-400 px-2 py-0.5 rounded-full">Hunter.io</span>}
        </div>

        <div>
          <label className="block text-xs font-medium text-[#6b7494] mb-2">Full name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Adam Milner"
            className="w-full bg-[#09090f] border border-[#262d42] rounded-lg px-4 py-2.5 text-sm text-white placeholder-[#363d52] focus:outline-none focus:border-[#3b5cbd] focus:ring-1 focus:ring-[#3b5cbd]/30 transition-all" />
        </div>
        <div>
          <label className="block text-xs font-medium text-[#6b7494] mb-2">Company or domain</label>
          <CompanyAutocomplete value={company} onChange={setCompany} onSubmit={find} />
        </div>
        <label className="flex items-start gap-3 cursor-pointer">
          <input type="checkbox" checked={resolve} onChange={e => setResolve(e.target.checked)} className="mt-0.5 accent-[#3b5cbd]" />
          <span className="text-xs text-[#6b7494] leading-relaxed">Resolve company to domain via web search</span>
        </label>
        <motion.button onClick={find} disabled={loading || !name || !company}
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          className="w-full flex items-center justify-center gap-2 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-sm font-medium rounded-lg py-2.5 transition-all border border-white/10">
          {loading ? <><RefreshCw size={14} className="spin" />Finding…</> : <><Mail size={14} />Find email</>}
        </motion.button>
      </div>

      <AnimatePresence>
        {(logs.length > 0 || err) && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="bg-[#0f1018] border border-[#1e2235] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-[#1e2235] text-xs font-semibold text-[#6b7494] tracking-wide uppercase">Log</div>
            <div className="bg-[#06070d] px-5 py-4 font-mono text-[11px] leading-7 space-y-0.5 min-h-[60px]">
              {logs.map((l, i) => (
                <div key={i} className={l.startsWith('→') ? 'text-emerald-400 font-semibold mt-1' : l.startsWith('✓') ? 'text-emerald-400' : 'text-[#4a5273]'}>{l}</div>
              ))}
              {err && <div className="text-red-400">Error: {err}</div>}
            </div>
            {email && (
              <div className="flex items-center justify-between px-5 py-4 bg-emerald-400/5 border-t border-emerald-400/20">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-400/10 flex items-center justify-center">
                    <Check size={16} className="text-emerald-400" />
                  </div>
                  <div>
                    <div className="text-white font-semibold text-sm">{email}</div>
                    <div className={`text-xs mt-0.5 ${confColor}`}>{Math.round(conf * 100)}% — {confLabel} {source && `via ${source}`}</div>
                  </div>
                </div>
                <button onClick={() => navigator.clipboard.writeText(email)}
                  className="text-xs text-[#6b7494] hover:text-white px-3 py-1.5 rounded-md bg-[#141620] border border-[#1e2235] transition-all">
                  Copy
                </button>
              </div>
            )}
            {!email && !loading && logs.length > 0 && !err && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex items-center gap-3 px-5 py-4 bg-red-400/5 border-t border-red-400/20">
                <div className="w-8 h-8 rounded-lg bg-red-400/10 flex items-center justify-center flex-shrink-0">
                  <X size={15} className="text-red-400" />
                </div>
                <div>
                  <div className="text-red-400 font-semibold text-sm">No email found</div>
                  <div className="text-[11px] text-[#6b7494] mt-0.5 leading-relaxed">
                    Neither Anymail nor Hunter.io returned a verified address for this person.
                    Check the name &amp; company spelling, or top up API credits.
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Settings Tab ──────────────────────────────────────────────────────────────
const PROVIDERS = [
  {
    id: 'openai',
    name: 'OpenAI',
    abbr: 'OAI',
    keyId: 'OPENAI_API_KEY',
    models: [
      { value: 'gpt-4o', label: 'GPT-4o', note: 'Best', sub: 'Highest capability · multimodal' },
      { value: 'gpt-4o-mini', label: 'GPT-4o mini', note: 'Fastest', sub: 'Low latency · affordable default' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', note: 'Cheapest', sub: 'Lowest cost · good for bulk tasks' },
    ],
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    abbr: 'GEM',
    keyId: 'GEMINI_API_KEY',
    models: [
      { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro', note: 'Best', sub: 'Strongest reasoning · 2M context' },
      { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', note: 'Fastest', sub: 'Very fast · ideal for extraction' },
      { value: 'gemini-1.5-flash-8b', label: 'Gemini Flash 8B', note: 'Cheapest', sub: 'Lowest Gemini cost · lightweight' },
    ],
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    abbr: 'CLN',
    keyId: 'ANTHROPIC_API_KEY',
    models: [
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', note: 'Best', sub: 'State-of-the-art · complex reasoning' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku', note: 'Fastest', sub: 'Near-instant · great for pipelines' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku', note: 'Cheapest', sub: 'Best value · reliable extraction' },
    ],
  },
];

const KEYS_CFG = [
  { id: 'SERPAPI_KEY', label: 'SerpAPI Key', ph: 'Insert key…', hint: 'Powers LinkedIn SERP scraping and domain resolution.' },
  { id: 'ANYMAIL_API_KEY', label: 'Anymail Finder Key', ph: 'Insert key…', hint: 'Primary email resolution. Requires active subscription.' },
  { id: 'HUNTER_API_KEY', label: 'Hunter.io Key', ph: 'Insert key…', hint: 'Secondary email resolution. Used when Anymail fails or quota is exceeded.' },
  { id: 'OPENAI_API_KEY', label: 'OpenAI API Key', ph: 'sk-…', hint: 'Required for OpenAI provider (GPT-4o, GPT-4o mini, GPT-3.5).' },
  { id: 'GEMINI_API_KEY', label: 'Google Gemini Key', ph: 'AIza…', hint: 'Required for Gemini provider. Get from Google AI Studio.' },
  { id: 'ANTHROPIC_API_KEY', label: 'Anthropic Claude Key', ph: 'sk-ant-…', hint: 'Required for Claude provider. Get from console.anthropic.com.' },
];

function SettingsTab({ onKeysChange }: { onKeysChange: (status: KeyStatus) => void }) {
  type KeyInfo = { connected: boolean; masked: string };
  const [serverKeys, setServerKeys] = useState<Record<string, KeyInfo>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});
  const [vis, setVis] = useState<Record<string, boolean>>({});
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o-mini');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState('');

  const refreshStatus = async () => {
    try {
      // Admin users get full key details; others get boolean status only
      const { keys, error } = await api.getKeys();
      if (!error) {
        setServerKeys(keys as any);
        const bools: KeyStatus = {};
        Object.entries(keys).forEach(([k, v]: any) => { bools[k] = typeof v === 'object' ? v.connected : !!v; });
        onKeysChange(bools);
      }
    } catch { /* ignore */ }
  };

  useEffect(() => {
    refreshStatus();
    api.getModel().then(d => {
      if (d.provider) setProvider(d.provider);
      if (d.model) setModel(d.model);
    });
  }, []);


  const startEdit = (id: string) => {
    setEditing(p => ({ ...p, [id]: true }));
    setDrafts(p => ({ ...p, [id]: '' })); // clear so user types fresh
  };
  const cancelEdit = (id: string) => {
    setEditing(p => ({ ...p, [id]: false }));
    setDrafts(p => ({ ...p, [id]: '' }));
  };

  const save = async () => {
    setSaving(true); setSaved(false); setErr('');
    try {
      const payload: Record<string, string> = {};
      KEYS_CFG.forEach(({ id }) => {
        if (editing[id] && drafts[id]?.trim()) payload[id] = drafts[id].trim();
      });

      const hasKeyChanges = Object.keys(payload).length > 0;
      if (hasKeyChanges) {
        const { error } = await api.saveKeys(payload);
        if (error) throw new Error(error);
        setEditing({});
        setDrafts({});
        await refreshStatus();
      }
      const { error: modelErr } = await api.setModel(provider, model);
      if (modelErr) throw new Error(modelErr);
      setSaved(true);
      setTimeout(() => setSaved(false), 4000);
    } catch (e: any) { setErr(e.message); }
    setSaving(false);
  };

  return (
    <div className="max-w-2xl space-y-5">
      {/* API Keys card */}
      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-white mb-1"><Key size={15} /> API Keys</div>
        <p className="text-xs text-[#6b7494] mb-6 leading-relaxed">
          Keys persist to <code className="text-[#6b7494]">.env</code> and survive restarts.
          Click <span className="text-white font-medium">Edit</span> next to any key to update it.
        </p>

        <div className="space-y-6">
          {KEYS_CFG.map(({ id, label, ph, hint }) => {
            const info = serverKeys[id] ?? { connected: false, masked: '' };
            const isEditing = !!editing[id];
            const isVisible = !!vis[id];
            return (
              <div key={id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-[#8090a8]">{label}</span>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${info.connected ? 'bg-emerald-400/10 text-emerald-400' : 'bg-[#f87171]/10 text-[#f87171]'
                      }`}>
                      {info.connected ? <><Check size={9} />Connected</> : '○ Not set'}
                    </span>
                    {!isEditing && (
                      <button onClick={() => startEdit(id)}
                        className="text-[10px] text-[#6b7494] hover:text-white px-2 py-0.5 rounded border border-[#1e2235] hover:border-[#262d42] transition-all bg-[#111520]">
                        {info.connected ? 'Change' : 'Set key'}
                      </button>
                    )}
                    {isEditing && (
                      <button onClick={() => cancelEdit(id)}
                        className="text-[10px] text-[#f87171] hover:text-red-300 px-2 py-0.5 rounded border border-red-400/20 hover:border-red-400/40 transition-all bg-[#111520]">
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-[11px] text-[#363d52] mb-2 leading-relaxed">{hint}</p>

                {/* Current masked value (read-only, shown when not editing) */}
                {!isEditing && info.connected && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-[#09090f] border border-[#1e2235] rounded-lg font-mono text-xs text-[#6b7494]">
                    <span className="flex-1">{isVisible ? '(click Show to reveal actual value)' : info.masked}</span>
                    <button onClick={() => setVis(p => ({ ...p, [id]: !p[id] }))}
                      className="text-[#363d52] hover:text-[#6b7494] transition-colors">
                      {isVisible ? <EyeOff size={12} /> : <Eye size={12} />}
                    </button>
                  </div>
                )}
                {!isEditing && !info.connected && (
                  <div className="px-3 py-2 bg-[#09090f] border border-dashed border-[#1e2235] rounded-lg text-xs text-[#363d52]">
                    Not configured — click <span className="text-[#6b7494]">Set key</span> to add
                  </div>
                )}

                {/* Edit input (shown when editing) */}
                {isEditing && (
                  <div className="flex gap-2">
                    <input
                      autoFocus
                      type={isVisible ? 'text' : 'password'}
                      placeholder={ph}
                      value={drafts[id] ?? ''}
                      onChange={e => setDrafts(p => ({ ...p, [id]: e.target.value }))}
                      className="flex-1 bg-[#09090f] border border-[#3b5cbd]/50 focus:border-[#3b5cbd] focus:ring-1 focus:ring-[#3b5cbd]/25 rounded-lg px-3 py-2 font-mono text-xs text-white placeholder-[#363d52] outline-none transition-all"
                    />
                    <button onClick={() => setVis(p => ({ ...p, [id]: !p[id] }))}
                      className="px-3 bg-[#111520] border border-[#1e2235] hover:border-[#262d42] rounded-lg text-[#6b7494] hover:text-white transition-all">
                      {isVisible ? <EyeOff size={13} /> : <Eye size={13} />}
                    </button>
                    {drafts[id] && (
                      <button onClick={() => setDrafts(p => ({ ...p, [id]: '' }))}
                        className="px-3 bg-[#111520] border border-[#1e2235] hover:border-red-400/40 rounded-lg text-[#6b7494] hover:text-red-400 transition-all">
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Provider & Model */}
      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl overflow-hidden">
        <div className="px-6 pt-5 pb-4 border-b border-[#1e2235]">
          <div className="flex items-center gap-2 text-sm font-semibold text-white mb-1"><Cpu size={14} /> AI Provider &amp; Model</div>
          <p className="text-[11px] text-[#4a5273] leading-relaxed">
            Choose the provider and tier used across all inference — extraction, search enhancement, and entity classification.
          </p>
        </div>

        {/* Provider rows */}
        <div className="divide-y divide-[#141620]">
          {PROVIDERS.map(p => {
            const keyInfo = serverKeys[p.keyId] ?? { connected: false, masked: '' };
            const isActive = provider === p.id;
            return (
              <div key={p.id}>
                {/* Row header — click to select provider */}
                <button
                  onClick={() => { setProvider(p.id); setModel(p.models[0].value); }}
                  className={`w-full flex items-center gap-4 px-6 py-4 text-left transition-colors ${isActive ? 'bg-[#111825]' : 'hover:bg-[#0c0e14]'
                    }`}
                >
                  {/* Wordmark abbrev */}
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 text-[10px] font-black tracking-widest transition-all ${isActive
                    ? 'bg-[#3b5cbd] text-white'
                    : 'bg-[#0d0f16] border border-[#1e2235] text-[#363d52]'
                    }`}>
                    {p.abbr}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className={`text-[13px] font-semibold transition-colors ${isActive ? 'text-white' : 'text-[#6b7494]'}`}>
                      {p.name}
                    </div>
                    {isActive && (
                      <div className="text-[11px] text-[#4a5273] mt-0.5">
                        {p.models.find(m => m.value === model)?.label ?? p.models[0].label}
                      </div>
                    )}
                    {!isActive && !keyInfo.connected && (
                      <div className="text-[10px] text-[#f87171]/70 mt-0.5">API key required</div>
                    )}
                  </div>

                  {/* Selection indicator */}
                  <div className={`w-[18px] h-[18px] rounded-full border flex items-center justify-center flex-shrink-0 transition-all ${isActive ? 'border-[#3b5cbd] bg-[#3b5cbd]/20' : 'border-[#262d42]'
                    }`}>
                    {isActive && <div className="w-2 h-2 rounded-full bg-[#728bee]" />}
                  </div>
                </button>

                {/* Model sub-rows — visible only when this provider is active */}
                {isActive && (
                  <div className="bg-[#0a0c12] border-t border-[#141620]">
                    {p.models.map((m) => (
                      <button
                        key={m.value}
                        onClick={() => setModel(m.value)}
                        className={`w-full flex items-center gap-5 px-6 py-3.5 text-left transition-colors border-b border-[#0f1118] last:border-0 ${model === m.value ? 'bg-[#3b5cbd]/8' : 'hover:bg-[#0d1018]'
                          }`}
                      >
                        {/* Rank dot */}
                        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors ${model === m.value ? 'bg-[#728bee]' : 'bg-[#1e2235]'
                          }`} />

                        {/* Model name + sub */}
                        <div className="flex-1 min-w-0">
                          <span className={`text-[12px] font-medium transition-colors ${model === m.value ? 'text-white' : 'text-[#6b7494]'
                            }`}>{m.label}</span>
                          <span className="text-[11px] text-[#363d52] ml-2">{m.sub}</span>
                        </div>

                        {/* Tier label — plain text, no pill */}
                        <span className={`text-[10px] font-semibold uppercase tracking-wider flex-shrink-0 ${m.note === 'Best' ? 'text-[#728bee]' :
                          m.note === 'Fastest' ? 'text-[#52c07b]' :
                            'text-[#8e7a4a]'
                          }`}>{m.note}</span>

                        {/* Check */}
                        {model === m.value && <Check size={12} className="text-[#3b5cbd] flex-shrink-0" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-4">
        <motion.button onClick={save} disabled={saving}
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          className="flex items-center gap-2 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-sm font-medium px-6 py-2.5 rounded-lg border border-white/10 transition-all">
          {saving ? <><RefreshCw size={13} className="spin" />Saving…</> : saved ? <><Check size={13} />Saved</> : 'Save settings'}
        </motion.button>
        {err && <span className="text-xs text-red-400">{err}</span>}
        {saved && <span className="flex items-center gap-1.5 text-xs text-emerald-400"><Check size={12} />Saved to .env</span>}
      </div>
    </div>
  );
}


// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  // DEV BYPASS: if VITE_DEV_TOKEN is set (local run.sh), auto-authenticate
  const devToken = import.meta.env.VITE_DEV_TOKEN as string | undefined;
  if (devToken) {
    setAuthToken(devToken);
  }

  const [isAuthenticated, setIsAuthenticated] = useState(!!getAuthToken());
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      api.getUser().then(res => {
        if (!res.error) setUser({ email: res.email, credits: res.credits, role: res.role });
        else { setAuthToken(''); setIsAuthenticated(false); }
        setAuthLoading(false);
      });
    } else { setAuthLoading(false); }
  }, [isAuthenticated]);

  if (authLoading) return <div className="h-screen bg-[#09090f] flex items-center justify-center"><Loader2 className="animate-spin text-[#3b5cbd]" size={36} /></div>;
  if (!isAuthenticated) return <AuthScreen onAuthSuccess={() => setIsAuthenticated(true)} />;

  const handleLogout = () => { setAuthToken(''); setIsAuthenticated(false); setUser(null); };

  return <AppShell user={user} onLogout={handleLogout} />;
}

function AppShell({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  const [tab, setTab] = useState('Pipeline');
  const [health, setHealth] = useState<boolean | null>(null);
  const [keyStatus, setKeyStatus] = useState<KeyStatus>({});

  useEffect(() => {
    api.checkHealth().then(setHealth);
    api.getKeyStatus().then(setKeyStatus);
  }, []);

  const goToSettings = () => setTab('Settings');

  // Pipeline state
  const [fileText, setFileText] = useState('');
  const [extractedCos, setExtractedCos] = useState<string[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [titles, setTitles] = useState<Record<string, boolean>>({ Director: true, Partner: true });
  const [running, setRunning] = useState(false);
  const [pResults, setPResults] = useState<PersonRow[]>([]);
  const [pErr, setPErr] = useState('');

  // AI Search
  const [aiQ, setAiQ] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResults, setAiResults] = useState<PersonRow[]>([]);
  const [aiErr, setAiErr] = useState('');

  // Intel
  const [intelCo, setIntelCo] = useState('');
  const [intelLoading, setIntelLoading] = useState(false);
  const [intelData, setIntelData] = useState<any>(null);
  const [intelErr, setIntelErr] = useState('');

  const toggleTitle = (t: string) => setTitles(p => ({ ...p, [t]: !p[t] }));

  const extract = async () => {
    if (!fileText.trim()) { setPErr('Upload at least one file first.'); return; }
    setExtracting(true); setPErr(''); setPResults([]);
    const { companies, error } = await api.extractCompanies(fileText);
    if (error) { setPErr(error); setExtractedCos([]); } else setExtractedCos(companies);
    setExtracting(false);
  };

  const runPipeline = async () => {
    if (!extractedCos.length) { setPErr('Extract companies first.'); return; }
    setRunning(true); setPErr(''); setPResults([]);
    const selected = Object.keys(titles).filter(k => titles[k]);
    const { results, error } = await api.outreachRun({
      count: extractedCos.length, max_per_company: 5, fetch_metadata: true, min_score: 0.8,
      companies: extractedCos, job_titles: selected.length ? selected : ['Director'],
    });
    if (error) setPErr(error); else setPResults(results);
    setRunning(false);
  };

  const runAI = async () => {
    if (!aiQ.trim()) return;
    setAiLoading(true); setAiErr('');
    const { results, error } = await api.aiSearch(aiQ);
    if (error) setAiErr(error); else setAiResults(results);
    setAiLoading(false);
  };

  const runIntel = async () => {
    if (!intelCo.trim()) return;
    setIntelLoading(true); setIntelErr(''); setIntelData(null);
    const { intel, error } = await api.runCompanyIntel(intelCo);
    if (error) setIntelErr(error); else setIntelData(intel);
    setIntelLoading(false);
  };

  const exportCSV = (rows: PersonRow[]) => {
    if (!rows.length) return;
    const cols = ['name', 'title', 'company', 'email', 'confidence', 'link'];
    const csv = [cols.join(','), ...rows.map(r => cols.map(c => `"${((r as any)[c] ?? '').toString().replace(/"/g, '""')}"`).join(','))].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'vanguard_export.csv'; document.body.appendChild(a); a.click(); a.remove();
  };

  const NAV = [
    { name: 'Pipeline', icon: Layers, badge: null },
    { name: 'Find Email', icon: Mail, badge: null },
    { name: 'AI Search', icon: Search, badge: null },
    { name: 'Entity Intel', icon: Building, badge: 'testing' },
    { name: 'Settings', icon: Settings, badge: null },
    ...(user?.role === 'admin' ? [{ name: 'Admin', icon: ShieldCheck, badge: null }] : []),
  ];

  // Check if a tab has any missing required keys
  const tabLocked = (name: string) => {
    const reqs = KEY_REQUIREMENTS[name] ?? [];
    return reqs.some(r => !r.keys.some(k => keyStatus[k]));
  };

  return (
    <div className="flex h-full bg-[#09090f] text-[#d8dce8]">
      {/* Sidebar */}
      <motion.aside initial={{ x: -200 }} animate={{ x: 0 }} transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        className="w-[200px] flex-shrink-0 bg-[#080810] border-r border-[#1e2235] flex flex-col">
        <div className="px-5 pt-6 pb-4">
          <div className="text-[11px] font-black tracking-[2px] uppercase text-[#728bee] [text-shadow:0_0_20px_rgba(114,139,238,0.4)]">CAREER26</div>
          <p className="text-[11px] text-[#6b7494] mt-1 leading-snug">Turn data into people.</p>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-0.5">
          {NAV.map((item, i) => {
            const Icon = item.icon;
            const active = tab === item.name;
            const locked = tabLocked(item.name);
            return (
              <motion.button key={item.name} onClick={() => setTab(item.name)}
                initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.04 * i }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-[13px] font-medium transition-all border
                  ${active ? 'bg-[#3b5cbd]/12 text-white border-[#3b5cbd]/30' : 'text-[#6b7494] border-transparent hover:bg-[#11141e] hover:text-[#d8dce8]'}`}>
                <div className="flex items-center gap-2.5">
                  <Icon size={15} stroke={active ? '#728bee' : locked ? '#f87171' : 'currentColor'} />
                  {item.name}
                </div>
                <div className="flex items-center gap-1">
                  {item.badge && (
                    <span className="text-[9px] font-bold uppercase tracking-wide bg-yellow-400/15 text-yellow-400 border border-yellow-400/25 px-1.5 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                  {locked && !active && <Lock size={10} className="text-[#f87171]/60" />}
                </div>
              </motion.button>
            );
          })}
        </nav>

        <div className="px-4 py-3 border-t border-[#1e2235] space-y-2">
          {user && (
            <div className="px-2 py-2 rounded-lg bg-[#0f1018] border border-[#1e2235]">
              <div className="text-[10px] text-[#6b7494] truncate font-mono">{user.email}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-emerald-400 font-bold">{user.credits?.toLocaleString()} cr</span>
                <span className={`text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded ${user.role === 'admin' ? 'text-[#728bee] bg-[#3b5cbd]/10' : 'text-[#6b7494]'}`}>{user.role}</span>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between">
            <div className={`w-2 h-2 rounded-full ${health ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]' : 'bg-red-400'}`}
              title={health ? 'Backend online' : 'Backend offline'} />
            <button onClick={onLogout} className="flex items-center gap-1.5 text-[10px] font-bold text-[#6b7494] hover:text-red-400 transition-colors uppercase tracking-widest">
              <LogOut size={11} /> Logout
            </button>
          </div>
        </div>
      </motion.aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto px-14 py-10 relative">
        <div className="pointer-events-none fixed top-0 left-[200px] right-0 h-64 bg-gradient-to-b from-[#3b5cbd]/8 to-transparent z-0" />

        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }} className="relative z-10">

            {/* ── PIPELINE ───────────────────────────────────────── */}
            {tab === 'Pipeline' && (<>
              <h1 className="text-2xl font-bold text-white mb-2">Pipeline</h1>
              <p className="text-[#6b7494] text-[13px] mb-8 max-w-lg leading-relaxed">Upload a company list in any format. AI extracts the names, then finds and verifies contacts.</p>

              {tabLocked('Pipeline') && <KeyGate tab="Pipeline" keyStatus={keyStatus} onGoToSettings={goToSettings}><></></KeyGate>}
              {!tabLocked('Pipeline') && (
                <div className="space-y-8">
                  {/* Step 1 */}
                  <div className="flex gap-5">
                    <div className="flex-shrink-0 flex flex-col items-center">
                      <div className="w-7 h-7 rounded-full bg-[#13151f] border border-[#262d42] text-[#6b7494] text-xs font-semibold flex items-center justify-center">1</div>
                      <div className="w-px flex-1 bg-[#1e2235] mt-2" />
                    </div>
                    <div className="pb-8 flex-1">
                      <h2 className="text-sm font-semibold text-white mb-1">Upload company list</h2>
                      <p className="text-[12px] text-[#6b7494] mb-4">CSV, Excel, PDF, or text file — AI extracts company names automatically.</p>
                      <FileUploadZone onText={setFileText} />
                      <div className="flex items-center gap-3 mt-4">
                        <motion.button onClick={extract} disabled={extracting || !fileText}
                          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                          className="flex items-center gap-2 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-[13px] font-medium px-5 py-2 rounded-lg border border-white/10 transition-all">
                          {extracting ? <><RefreshCw size={13} className="spin" />Extracting…</> : 'Extract Companies'}
                        </motion.button>
                        {extractedCos.length > 0 && !pErr && (
                          <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            className="flex items-center gap-1.5 text-emerald-400 text-xs">
                            <Check size={13} /> {extractedCos.length} companies ready
                          </motion.span>
                        )}
                        {pErr && <span className="text-xs text-red-400">{pErr}</span>}
                      </div>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="flex gap-5">
                    <div className="flex-shrink-0">
                      <div className="w-7 h-7 rounded-full bg-[#13151f] border border-[#262d42] text-[#6b7494] text-xs font-semibold flex items-center justify-center">2</div>
                    </div>
                    <div className="flex-1">
                      <h2 className="text-sm font-semibold text-white mb-1">Select titles &amp; find people</h2>
                      <p className="text-[12px] text-[#6b7494] mb-5">Tick any roles to target. Each company is searched for people matching at least one.</p>
                      <div className="grid grid-cols-4 gap-x-6 gap-y-3 mb-6">
                        {JOB_TITLES.map(t => (
                          <label key={t} className="flex items-center gap-2 cursor-pointer group">
                            <input type="checkbox" checked={!!titles[t]} onChange={() => toggleTitle(t)} className="w-3.5 h-3.5 accent-[#3b5cbd] cursor-pointer" />
                            <span className="text-[12px] text-[#8090a8] group-hover:text-[#d8dce8] transition-colors">{t}</span>
                          </label>
                        ))}
                      </div>
                      <motion.button onClick={runPipeline} disabled={running || !extractedCos.length}
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                        className="flex items-center gap-2 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-[13px] font-medium px-5 py-2 rounded-lg border border-white/10 transition-all">
                        <Activity size={13} />{running ? 'Scanning…' : 'Find People'}
                      </motion.button>
                    </div>
                  </div>
                </div>
              )}
              <ResultsTable rows={pResults} onExport={() => exportCSV(pResults)} />
            </>)}

            {/* ── FIND EMAIL ─────────────────────────────────────── */}
            {tab === 'Find Email' && (<>
              <h1 className="text-2xl font-bold text-white mb-2">Find email</h1>
              <p className="text-[#6b7494] text-[13px] mb-8 max-w-md leading-relaxed">Name + company or domain. Anymail → Hunter.io. No AI-generated guesses — only verified API results.</p>
              <FindEmailTab keyStatus={keyStatus} onGoToSettings={goToSettings} />
            </>)}

            {/* ── AI SEARCH ──────────────────────────────────────── */}
            {tab === 'AI Search' && (<>
              <h1 className="text-2xl font-bold text-white mb-2">Search people</h1>
              <p className="text-[#6b7494] text-[13px] mb-8 max-w-lg leading-relaxed">Natural language search across LinkedIn.</p>
              {tabLocked('AI Search') && <KeyGate tab="AI Search" keyStatus={keyStatus} onGoToSettings={goToSettings}><></></KeyGate>}
              {!tabLocked('AI Search') && (<>
                <div className="flex gap-3 max-w-2xl mb-6">
                  <input value={aiQ} onChange={e => setAiQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && runAI()}
                    placeholder="IB analysts in London…"
                    className="flex-1 h-11 bg-[#111c3a] border border-[#3b5cbd]/30 rounded-xl px-4 text-sm text-white placeholder-[#6b7494] focus:outline-none focus:border-[#3b5cbd] focus:ring-1 focus:ring-[#3b5cbd]/30 transition-all" />
                  <motion.button onClick={runAI} disabled={aiLoading || !aiQ}
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                    className="h-11 px-6 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-[13px] font-medium rounded-xl border border-white/10 transition-all">
                    {aiLoading ? 'Searching…' : 'Search'}
                  </motion.button>
                </div>
                {aiErr && <div className="text-sm text-red-400 mb-4">⚠ {aiErr}</div>}
                <ResultsTable rows={aiResults} onExport={() => exportCSV(aiResults)} />
              </>)}
            </>)}

            {/* ── ENTITY INTEL ───────────────────────────────────── */}
            {tab === 'Entity Intel' && (<>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold text-white">Entity Intel</h1>
                <span className="text-[10px] font-bold uppercase tracking-wide bg-yellow-400/15 text-yellow-400 border border-yellow-400/25 px-2 py-1 rounded-full">Testing</span>
              </div>
              <p className="text-[#6b7494] text-[13px] mb-8 max-w-lg leading-relaxed">Deep-scan a company — headcount, optimal outreach roles, and verified contacts.</p>
              {tabLocked('Entity Intel') && <KeyGate tab="Entity Intel" keyStatus={keyStatus} onGoToSettings={goToSettings}><></></KeyGate>}
              {!tabLocked('Entity Intel') && (<>
                <div className="flex gap-3 max-w-xl mb-8">
                  <input value={intelCo} onChange={e => setIntelCo(e.target.value)} onKeyDown={e => e.key === 'Enter' && runIntel()}
                    placeholder="Baillie Gifford"
                    className="flex-1 h-11 bg-[#09090f] border border-[#262d42] rounded-xl px-4 text-sm text-white placeholder-[#363d52] focus:outline-none focus:border-[#3b5cbd] transition-all" />
                  <motion.button onClick={runIntel} disabled={intelLoading || !intelCo}
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    className="h-11 px-6 bg-[#3b5cbd] hover:bg-[#4d70d9] disabled:opacity-40 text-white text-[13px] font-medium rounded-xl border border-white/10 transition-all">
                    {intelLoading ? 'Scanning…' : 'Deep Scan'}
                  </motion.button>
                </div>
                {intelErr && <div className="text-sm text-red-400 mb-4">⚠ {intelErr}</div>}
                {intelData && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-5">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-[#6b7494] mb-2">Company Scale</div>
                        <div className="text-xl font-bold text-white">{intelData.company_size_text}</div>
                      </div>
                      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-5">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-[#6b7494] mb-3">Target Roles</div>
                        <div className="flex flex-wrap gap-2">
                          {intelData.target_roles_used.map((r: string, i: number) => (
                            <span key={i} className="text-[11px] text-[#a0b4f0] bg-[#3b5cbd]/12 border border-[#3b5cbd]/25 px-3 py-1 rounded-full">{r}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-5">
                      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-[#6b7494] mb-4"><Terminal size={12} /> Workflow log</div>
                      <div className="bg-[#06070d] rounded-lg p-4 border border-[#1e2235] font-mono text-[11px] leading-7">
                        {intelData.source_log.map((l: string, i: number) => (
                          <div key={i} className="text-[#3e4a68]"><span className="text-emerald-400 mr-2">{">"}</span>{l}</div>
                        ))}
                      </div>
                    </div>
                    {intelData.people_found?.length > 0 && <ResultsTable rows={intelData.people_found} onExport={() => exportCSV(intelData.people_found)} />}
                  </motion.div>
                )}
              </>)}
            </>)}

            {/* ── SETTINGS ───────────────────────────────────────── */}
            {tab === 'Settings' && (<>
              <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
              <p className="text-[#6b7494] text-[13px] mb-8 max-w-md leading-relaxed">Configure API integrations and the AI model used across all workflows.</p>
              <SettingsTab onKeysChange={setKeyStatus} />
            </>)}

            {/* ── ADMIN ──────────────────────────────────────────── */}
            {tab === 'Admin' && user?.role === 'admin' && <AdminDashboardTab />}

          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

// ── Admin Dashboard ───────────────────────────────────────────────────────────
function AdminDashboardTab() {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [sRes, uRes] = await Promise.all([api.adminGetStats(), api.adminListUsers()]);
    if (!sRes.error) setStats(sRes.stats);
    if (!uRes.error) setUsers(uRes.users);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const handleCredits = async (id: number, cur: number) => {
    const val = prompt('New credit balance:', String(cur + 50000));
    if (val) { const r = await api.adminUpdateCredits(id, parseInt(val)); if (r.success) load(); }
  };
  const handleRole = async (id: number, cur: string) => {
    const next = cur === 'admin' ? 'user' : 'admin';
    if (confirm(`Change to ${next}?`)) { const r = await api.adminUpdateRole(id, next); if (r.success) load(); }
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-[#3b5cbd]" size={36} /></div>;

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Admin Dashboard</h1>
        <p className="text-[#6b7494] text-[13px] max-w-lg leading-relaxed">System-wide usage, token burn, and account management.</p>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {[
          { label: 'Total Users', value: stats?.total_users ?? 0, icon: Users, color: 'text-[#728bee]' },
          { label: 'Verified', value: `${Math.round((stats?.verified_users / stats?.total_users) * 100) || 0}%`, icon: Check, color: 'text-emerald-400' },
          { label: 'Token Burn', value: stats?.total_tokens?.toLocaleString() ?? 0, icon: Trophy, color: 'text-orange-400' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f1018] border border-[#1e2235] rounded-xl p-6">
            <div className="flex items-center gap-2 text-[#6b7494] text-[11px] uppercase tracking-wider mb-3"><s.icon size={14} className={s.color} />{s.label}</div>
            <div className={`text-3xl font-black ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#0f1018] border border-[#1e2235] rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e2235]">
          <span className="text-sm font-semibold text-white flex items-center gap-2"><Users size={15} /> User Directory</span>
          <button onClick={load} className="text-[10px] text-[#6b7494] hover:text-white flex items-center gap-1.5 uppercase tracking-widest"><RefreshCw size={11} /> Refresh</button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-[#0d0f16] border-b border-[#1e2235]">
            <tr>{['Name', 'Email', 'Role', 'Credits', 'Actions'].map(h => <th key={h} className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-[#4a5273]">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-[#1e2235]">
            {users.map(u => (
              <tr key={u.ID} className="hover:bg-[#3b5cbd]/5 transition-colors group">
                <td className="px-5 py-4 font-medium text-white">{u.first_name} {u.last_name}</td>
                <td className="px-5 py-4 font-mono text-[11px] text-[#6b7494]">{u.Email}</td>
                <td className="px-5 py-4"><span className={`text-[9px] font-black uppercase px-2 py-1 rounded ${u.role === 'admin' ? 'bg-[#3b5cbd]/15 text-[#728bee]' : 'bg-[#1e2235] text-[#6b7494]'}`}>{u.role}</span></td>
                <td className="px-5 py-4 font-mono text-emerald-400 text-[13px]">{u.Credits?.toLocaleString()}</td>
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => handleCredits(u.ID, u.Credits)} className="text-[10px] text-[#6b7494] hover:text-white border border-[#1e2235] hover:border-[#262d42] px-2 py-1 rounded bg-[#111520] transition-all">Edit Credits</button>
                    <button onClick={() => handleRole(u.ID, u.role)} className="text-[10px] text-[#6b7494] hover:text-white transition-colors">Toggle Role</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
