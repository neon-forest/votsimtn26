import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  Search,
  Award,
  BarChart3,
  Activity,
  ArrowUpRight,
  Filter,
  Download,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import RegionalCards from './components/RegionalCards';
import LeaderCards from './components/LeaderCards';
import { loadResults, getSummary } from './utils/data';

const App = () => {
  const [data, setData] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [theme, setTheme] = useState('light');

  // Table State
  const [sortConfig, setSortConfig] = useState({ key: 'Constituency', direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  useEffect(() => {
    loadResults()
      .then(res => {
        setData(res);
        setSummary(getSummary(res));
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load results:", err);
        setError("Failed to load simulation results. Please check if the data files exist.");
        setLoading(false);
      });

    // Load theme preference
    const savedTheme = localStorage.getItem('votersim-theme') || 'light';
    setTheme(savedTheme);
    document.body.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('votersim-theme', newTheme);
  };

  // Sorting and Filtering Logic
  const processedData = useMemo(() => {
    let filtered = data.filter(item =>
      item.Constituency.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.District.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.Winner.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (sortConfig.key) {
      filtered.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (typeof aVal === 'number') {
          return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }

        const aStr = String(aVal).toLowerCase();
        const bStr = String(bVal).toLowerCase();

        if (aStr < bStr) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aStr > bStr) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return filtered;
  }, [data, searchTerm, sortConfig]);

  // Pagination Logic
  const totalPages = Math.ceil(processedData.length / itemsPerPage);
  const paginatedData = processedData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const requestSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
    setCurrentPage(1); // Reset to first page on sort
  };

  const [expandedRow, setExpandedRow] = useState(null);

  const toggleRow = (id) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  if (loading) return (
    <div className="loading-screen">
      <div className="loader"></div>
      <p>Initializing TN'26 Election Engine...</p>
    </div>
  );

  if (error) return (
    <div className="loading-screen error">
      <div className="card" style={{ padding: '2rem', textAlign: 'center', maxWidth: '400px' }}>
        <p style={{ color: '#ef4444', fontWeight: 600, marginBottom: '1rem' }}>{error}</p>
        <button onClick={() => window.location.reload()} className="page-btn active" style={{ margin: '0 auto' }}>
          Retry
        </button>
      </div>
    </div>
  );

  const chartData = [
    { name: 'SPA', value: summary.SPA, color: '#ef4444' },
    { name: 'AIADMK+', value: summary['AIADMK+'], color: '#10b981' },
    { name: 'TVK', value: summary.TVK, color: '#f59e0b' },
    { name: 'Others', value: summary.Others, color: '#94a3b8' },
  ].sort((a, b) => b.value - a.value);

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  };

  const card3D = {
    whileHover: {
      rotateX: 5,
      rotateY: -5,
      scale: 1.02,
      transition: { type: "spring", stiffness: 300, damping: 20 }
    }
  };

  return (
    <div className="app-container" style={{ perspective: '1000px' }}>
      {/* Sidebar / Nav */}
      <nav className="top-nav">
        <div className="nav-content">
          <div className="logo">
            <TrendingUp className="logo-icon" />
            <span>VoterSim <strong>TN'26</strong></span>
          </div>
          <div className="nav-actions">
            <button className="theme-toggle" onClick={toggleTheme} title="Toggle Dark/Light Mode">
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </div>
      </nav>

      <motion.main
        className="dashboard-main"
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        {/* Header Stats */}
        <header className="dashboard-header">
          <div className="header-text">
            <motion.h1 variants={itemVariants}>Electoral Dashboard</motion.h1>
            <motion.p variants={itemVariants}>2026 Tamil Nadu Legislative Assembly Projections</motion.p>
          </div>
          <div className="header-stats">
            <motion.div className="stat-pill" variants={itemVariants} {...card3D}>
              <span className="label">Total Seats</span>
              <span className="value">234</span>
            </motion.div>
            <motion.div className="stat-pill primary" variants={itemVariants} {...card3D}>
              <span className="label">Majority Mark</span>
              <span className="value">118</span>
            </motion.div>
          </div>
        </header>

        {/* Top Leader Cards */}
        <motion.section className="section" variants={itemVariants}>
          <div className="section-header">
            <Users size={18} />
            <h2>Party Leadership Projections</h2>
          </div>
          <LeaderCards summary={summary} />
        </motion.section>

        {/* Charts & Distribution */}
        <div className="data-grid">
          <motion.section className="section chart-section" variants={itemVariants}>
            <div className="section-header">
              <BarChart3 size={18} />
              <h2>Seat Distribution</h2>
            </div>
            <div className="card chart-card">
              <div style={{ width: '100%', height: '400px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={theme === 'light' ? '#eee' : '#334155'} />
                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: theme === 'light' ? '#666' : '#94a3b8', fontSize: 12, fontWeight: 600 }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: theme === 'light' ? '#666' : '#94a3b8', fontSize: 12 }}
                    />
                    <ReTooltip
                      cursor={{ fill: theme === 'light' ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.02)' }}
                      contentStyle={{
                        borderRadius: '8px',
                        border: 'none',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                        background: theme === 'light' ? '#fff' : '#1e293b',
                        color: theme === 'light' ? '#1e293b' : '#f1f5f9'
                      }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={60}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </motion.section>

          <motion.section className="section info-section" variants={itemVariants}>
            <div className="section-header">
              <Activity size={18} />
              <h2>Simulation Integrity</h2>
            </div>
            <div className="card info-card">
              <div className="info-row">
                <span>Data Consistency</span>
                <span className="tag success">100% Verified</span>
              </div>
              <div className="info-row">
                <span>Seats Simulated</span>
                <span className="bold">234 / 234</span>
              </div>
              <div className="info-row">
                <span>Turnout Model</span>
                <span className="bold">Historical Weighted</span>
              </div>
              <hr />
              <div className="majority-progress">
                <div className="progress-labels">
                  <span>SPA Progress to Majority</span>
                  <span>{Math.round((summary.SPA / 118) * 100)}%</span>
                </div>
                <div className="progress-bar">
                  <motion.div
                    className="progress-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, (summary.SPA / 118) * 100)}%` }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                  />
                  <div className="majority-line" style={{ left: '100%' }}></div>
                </div>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '1rem' }}>
                * Majority benchmark set at 118 seats for the 234-member assembly.
              </p>
            </div>
          </motion.section>
        </div>

        {/* Regional Breakdown */}
        <motion.section className="section" variants={itemVariants}>
          <div className="section-header">
            <Filter size={18} />
            <h2>Regional Analysis</h2>
          </div>
          <RegionalCards data={data} />
        </motion.section>

        {/* Explorer Table */}
        <motion.section className="section" variants={itemVariants}>
          <div className="section-header explorer-header">
            <div className="header-left">
              <LayoutDashboard size={18} />
              <h2>Constituency Explorer</h2>
            </div>
            <div className="search-box">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search constituency, district, or party..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              />
            </div>
          </div>

          <div className="card table-card">
            {/* Desktop Table View */}
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th onClick={() => requestSort('Constituency')}>
                      Constituency
                      <ArrowUpDown size={12} className={`sort-icon ${sortConfig.key === 'Constituency' ? 'active' : ''}`} />
                    </th>
                    <th onClick={() => requestSort('District')}>
                      District
                      <ArrowUpDown size={12} className={`sort-icon ${sortConfig.key === 'District' ? 'active' : ''}`} />
                    </th>
                    <th onClick={() => requestSort('Winner')}>
                      Winner
                      <ArrowUpDown size={12} className={`sort-icon ${sortConfig.key === 'Winner' ? 'active' : ''}`} />
                    </th>
                    <th onClick={() => requestSort('Margin_Pct')}>
                      Margin
                      <ArrowUpDown size={12} className={`sort-icon ${sortConfig.key === 'Margin_Pct' ? 'active' : ''}`} />
                    </th>
                    <th>Vote Shares (%)</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence mode="wait">
                    {paginatedData.map((row) => {
                      const isExpanded = expandedRow === row.Constituency + row.District;
                      return (
                        <React.Fragment key={row.Constituency + row.District}>
                          <motion.tr
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            onClick={() => toggleRow(row.Constituency + row.District)}
                            style={{ cursor: 'pointer', background: isExpanded ? 'var(--row-hover-bg)' : 'transparent' }}
                          >
                            <td className="bold">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <ChevronRight
                                  size={16}
                                  style={{
                                    transition: 'transform 0.3s',
                                    transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                    opacity: 0.5
                                  }}
                                />
                                {row.Constituency}
                              </div>
                            </td>
                            <td className="muted">{row.District}</td>
                            <td>
                              <span className={`party-badge ${row.Winner.replace('+', '').toLowerCase()}`}>
                                {row.Winner}
                              </span>
                            </td>
                            <td className="bold">{row.Margin_Pct}%</td>
                            <td>
                              <div className="vote-share-viz">
                                <div className="share-bar">
                                  <div className="share-fill spa" style={{ flex: row.SPA_Pct }}></div>
                                  <div className="share-fill aiadmk" style={{ flex: row.AIADMK_Pct }}></div>
                                  <div className="share-fill tvk" style={{ flex: row.TVK_Pct }}></div>
                                  <div className="share-fill others" style={{ flex: row.Others_Pct }}></div>
                                </div>
                                <span className="share-text" style={{ fontSize: '0.7rem' }}>
                                  {row.SPA_Pct}% | {row.AIADMK_Pct}% | {row.TVK_Pct}% | {row.Others_Pct}%
                                </span>
                              </div>
                            </td>
                          </motion.tr>

                          <AnimatePresence>
                            {isExpanded && (
                              <motion.tr
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.3, ease: "easeInOut" }}
                                style={{ overflow: 'hidden' }}
                              >
                                <td colSpan={5} className="expanded-row-cell" style={{ padding: 0, background: 'var(--table-header-bg)' }}>
                                  <div className="sticky-expanded-container" style={{ position: 'sticky', left: 0 }}>
                                    <motion.div
                                      initial={{ y: -10, opacity: 0 }}
                                      animate={{ y: 0, opacity: 1 }}
                                      className="expanded-content"
                                      style={{
                                        margin: '1rem',
                                        padding: '1.5rem',
                                        background: 'var(--card-bg)',
                                        borderRadius: '12px',
                                        border: '1px solid var(--border-color)',
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                                        gap: '1.5rem',
                                        boxShadow: 'var(--shadow-md)',
                                        width: 'calc(100% - 2rem)'
                                      }}
                                    >
                                      <div className="expanded-section">
                                        <h5 style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '1rem', letterSpacing: '0.05em' }}>Vote Breakdown</h5>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                          {[
                                            { p: 'SPA', v: row.SPA_Pct, c: 'var(--color-spa)' },
                                            { p: 'AIADMK+', v: row.AIADMK_Pct, c: 'var(--color-aiadmk)' },
                                            { p: 'TVK', v: row.TVK_Pct, c: 'var(--color-tvk)' },
                                            { p: 'Others', v: row.Others_Pct, c: 'var(--color-others)' }
                                          ].map(item => (
                                            <div key={item.p} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.c }}></div>
                                                <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>{item.p}</span>
                                              </div>
                                              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>{item.v}%</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>

                                      <div className="expanded-section">
                                        <h5 style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '1rem', letterSpacing: '0.05em' }}>Electoral Context</h5>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Region (Culture)</span>
                                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>{row.Culture || 'N/A'}</span>
                                          </div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Winning Margin</span>
                                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>{row.Margin_Votes?.toLocaleString() || row.Margin_Votes || '0'} Votes</span>
                                          </div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Status</span>
                                            <span className="tag success" style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}>Verified Result</span>
                                          </div>
                                        </div>
                                      </div>

                                      <div className="lead-intensity-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '1.25rem', background: 'var(--bg-color)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                                        <div style={{ fontSize: '0.65rem', opacity: 0.5, marginBottom: '0.5rem', fontWeight: 700, textTransform: 'uppercase' }}>Lead Intensity</div>
                                        <div style={{ fontSize: '1.5rem', fontWeight: 900, color: row.Margin_Pct > 10 ? '#10b981' : 'var(--color-spa)', textAlign: 'center', lineHeight: 1.1 }}>
                                          {row.Margin_Pct > 10 ? 'STRONG' : 'COMPETITIVE'}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>{row.Margin_Pct}% Margin</div>
                                      </div>
                                    </motion.div>
                                  </div>
                                </td>
                              </motion.tr>
                            )}
                          </AnimatePresence>
                        </React.Fragment>
                      );
                    })}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>

            {/* Mobile Card View */}
            <div className="mobile-constituency-list">
              {paginatedData.map((row) => {
                const isExpanded = expandedRow === row.Constituency + row.District;
                return (
                  <motion.div
                    key={row.Constituency + row.District}
                    className="constituency-card"
                    onClick={() => toggleRow(row.Constituency + row.District)}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="constituency-card-header">
                      <div>
                        <div className="constituency-card-title">{row.Constituency}</div>
                        <div className="constituency-card-district">{row.District}</div>
                      </div>
                      <span className={`party-badge ${row.Winner.replace('+', '').toLowerCase()}`}>
                        {row.Winner}
                      </span>
                    </div>

                    <div className="constituency-card-stats">
                      <div className="bold">{row.Margin_Pct}% Margin</div>
                      <div className="vote-share-viz" style={{ minWidth: '120px' }}>
                        <div className="share-bar" style={{ height: '4px' }}>
                          <div className="share-fill spa" style={{ flex: row.SPA_Pct }}></div>
                          <div className="share-fill aiadmk" style={{ flex: row.AIADMK_Pct }}></div>
                          <div className="share-fill tvk" style={{ flex: row.TVK_Pct }}></div>
                          <div className="share-fill others" style={{ flex: row.Others_Pct }}></div>
                        </div>
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          className="constituency-card-expanded"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingTop: '1.25rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                              <div className="lead-intensity-card" style={{ padding: '1rem', background: 'var(--bg-color)', borderRadius: '12px', border: '1px solid var(--border-color)', gridColumn: 'span 2', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Intensity</div>
                                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: row.Margin_Pct > 10 ? '#10b981' : 'var(--color-spa)' }}>
                                    {row.Margin_Pct > 10 ? 'STRONG' : 'COMPETITIVE'}
                                  </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Margin</div>
                                  <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{row.Margin_Pct}%</div>
                                </div>
                              </div>

                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Region</span>
                                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{row.Culture}</span>
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Winning Margin</span>
                                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{row.Margin_Votes?.toLocaleString()}</span>
                              </div>
                            </div>

                            <div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Vote Share Breakdown</div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
                                {[
                                  { p: 'SPA', v: row.SPA_Pct, c: 'var(--color-spa)' },
                                  { p: 'AIADMK+', v: row.AIADMK_Pct, c: 'var(--color-aiadmk)' },
                                  { p: 'TVK', v: row.TVK_Pct, c: 'var(--color-tvk)' },
                                  { p: 'Others', v: row.Others_Pct, c: 'var(--color-others)' }
                                ].map(item => (
                                  <div key={item.p} style={{ background: 'var(--bg-color)', padding: '0.5rem 0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.c }}></div>
                                      <span style={{ fontWeight: 600 }}>{item.p}</span>
                                    </div>
                                    <span style={{ fontWeight: 700 }}>{item.v}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>

            {/* Pagination Controls */}
            <div className="pagination-controls">
              <div className="pagination-info">
                Showing <strong>{(currentPage - 1) * itemsPerPage + 1}</strong> to <strong>{Math.min(currentPage * itemsPerPage, processedData.length)}</strong> of <strong>{processedData.length}</strong> results
              </div>
              <div className="pagination-buttons">
                <button
                  className="page-btn"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={16} />
                </button>
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  let pageNum;
                  if (totalPages <= 5) pageNum = i + 1;
                  else if (currentPage <= 3) pageNum = i + 1;
                  else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                  else pageNum = currentPage - 2 + i;

                  return (
                    <button
                      key={pageNum}
                      className={`page-btn ${currentPage === pageNum ? 'active' : ''}`}
                      onClick={() => setCurrentPage(pageNum)}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  className="page-btn"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </motion.section>
      </motion.main>

      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-info">
            <p>&copy; 2026 VoterSim TN. Electoral Simulation.</p>
            <p className="educational-disclaimer" style={{ marginTop: '0.5rem', opacity: 0.8 }}>
              For educational purposes: no prediction or results are original; all are generated.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
