import React, { useState } from 'react';
import { Activity, Mail, Search, Shield, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './index.css';

const JOB_TITLES = [
  "Director", "Partner", "VP", "Managing Director",
  "Principal", "Associate", "Head of Business Development", "Head of Investor Relations",
  "CFO", "CEO", "Analyst", "Graduate",
  "Intern", "Early Careers", "Talent Acquisition", "Recruiter",
  "HR Director", "Head of People", "Chief People Officer", "General Counsel",
  "Legal Counsel", "Head of Operations", "COO", "Head of Strategy",
  "Business Development Manager", "Account Manager",
];

const RECENT_IMPORTS = [
  { file: "sample_companies.csv", meta: "5 companies · 2/15/2026" },
  { file: "sample_companies.csv", meta: "5 companies · 2/15/2026" }
];

function App() {
  const [activeTab, setActiveTab] = useState('Pipeline');

  const [checkedTitles, setCheckedTitles] = useState<Record<string, boolean>>({
    "Director": true,
    "Partner": true
  });

  const toggleTitle = (title: string) => {
    setCheckedTitles(prev => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <div className="app-layout">
      {/* Sidebar with framer-motion slide in */}
      <motion.aside
        className="sidebar"
        initial={{ x: -250 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
      >
        <div className="sidebar-header">
          <motion.div
            className="logo"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            CAREER26
          </motion.div>
        </div>
        <ul className="nav-links">
          {[
            { name: 'Pipeline', icon: <Activity className="nav-icon" /> },
            { name: 'Find Email', icon: <Mail className="nav-icon" /> },
            { name: 'Search People', icon: <Search className="nav-icon" /> },
            { name: 'Vanguard', icon: <Shield className="nav-icon" /> },
            { name: 'Settings', icon: <Settings className="nav-icon" /> },
          ].map((item, i) => (
            <motion.li
              key={item.name}
              className={`nav-item ${activeTab === item.name ? 'active' : ''}`}
              onClick={() => setActiveTab(item.name)}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {React.cloneElement(item.icon, {
                stroke: activeTab === item.name ? '#aebdf1' : 'currentColor'
              })}
              {item.name}
            </motion.li>
          ))}
        </ul>
        <div className="sidebar-footer">
          v1.0.0 — Web
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <main className="main-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            <h1 className="page-title">{activeTab}</h1>
            <p className="page-subtitle">Upload data, extract companies, find people, and export results.</p>

            {activeTab === 'Pipeline' && (
              <>
                {/* Step Placeholder */}
                <motion.div
                  className="step-container"
                  style={{ marginBottom: 20 }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <div className="step-circle" style={{ opacity: 0, border: 'none' }}></div>
                  <div className="step-content">
                    <motion.button
                      className="btn-blue"
                      style={{ marginTop: 8 }}
                      whileHover={{ scale: 1.05, backgroundColor: "var(--btn-blue-hover)" }}
                      whileTap={{ scale: 0.95 }}
                    >
                      Load & Extract
                    </motion.button>
                  </div>
                </motion.div>

                {/* Step 3: Find People */}
                <motion.div
                  className="step-container"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <motion.div
                    className="step-circle"
                    whileHover={{ scale: 1.1, backgroundColor: "#272f44" }}
                  >
                    3
                  </motion.div>
                  <div className="step-content">
                    <h2 className="step-title">Find People</h2>
                    <p className="step-desc">Set job titles and search for people at each company.</p>

                    <p className="step-label">Job titles (optional — tick any that apply)</p>
                    <div className="checkbox-grid">
                      {JOB_TITLES.map((title, i) => (
                        <motion.label
                          key={title}
                          className="checkbox-item"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.3 + (i * 0.01) }}
                          whileHover={{ scale: 1.02 }}
                        >
                          <input
                            type="checkbox"
                            className="checkbox-input"
                            checked={!!checkedTitles[title]}
                            onChange={() => toggleTitle(title)}
                          />
                          <span className="checkbox-label">{title}</span>
                        </motion.label>
                      ))}
                    </div>

                    <motion.button
                      className="btn-blue"
                      whileHover={{ scale: 1.05, backgroundColor: "var(--btn-blue-hover)" }}
                      whileTap={{ scale: 0.95 }}
                    >
                      Find People
                    </motion.button>
                  </div>
                </motion.div>

                {/* Step 4: Export Results */}
                <motion.div
                  className="step-container"
                  style={{ marginBottom: 0 }}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <motion.div
                    className="step-circle"
                    whileHover={{ scale: 1.1, backgroundColor: "#272f44" }}
                  >
                    4
                  </motion.div>
                  <div className="step-content">
                    <h2 className="step-title">Export Results</h2>
                    <p className="step-desc">Save the people list as CSV or Excel.</p>

                    <div className="button-group">
                      <motion.button
                        className="btn-dark"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Export CSV
                      </motion.button>
                      <motion.button
                        className="btn-dark"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Export Excel
                      </motion.button>
                    </div>
                  </div>
                </motion.div>

                {/* Recent Imports Panel */}
                <motion.div
                  className="panel"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className="panel-header">RECENT IMPORTS</div>
                  {RECENT_IMPORTS.map((item, idx) => (
                    <motion.div
                      key={idx}
                      className="panel-row"
                      whileHover={{ backgroundColor: "rgba(255,255,255,0.02)" }}
                    >
                      <span>{item.file}</span>
                      <span className="panel-meta">{item.meta}</span>
                    </motion.div>
                  ))}
                </motion.div>
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
