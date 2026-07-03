import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import TrendingPapers from './components/TrendingPapers';
import Navigation from './components/Navigation';
import PaperAgentModal from './components/PaperAgentModal';
import Home from './pages/Home';
import Search from './pages/Search';
import Paper from './pages/Paper';
import HaiPapers from './pages/HaiPapers';
import TagPage from './pages/TagPage';
import Bookmarks from './pages/Bookmarks';
import Alerts from './pages/Alerts';
import './App.css';

function App() {
  const [agentOpen, setAgentOpen] = useState(false);
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <Navigation onOpenAgent={() => setAgentOpen(true)} />

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/trending" element={<TrendingPapers />} />
            <Route path="/search" element={<Search />} />
            <Route path="/paper/:arxiv_id" element={<Paper />} />
            <Route path="/hai" element={<HaiPapers />} />
            <Route path="/tag/:tagname" element={<TagPage />} />
            <Route path="/tags/:tagname" element={<TagPage />} />
            <Route path="/bookmarks" element={<Bookmarks />} />
            <Route path="/alerts" element={<Alerts />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-gray-900 text-gray-400 py-10 mt-16">
          <div className="max-w-5xl mx-auto px-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              {/* Lab Info */}
              <div className="flex items-center gap-4">
                <img
                  src="https://usecloud.s3-us-west-1.amazonaws.com/snu_logo.png"
                  alt="SNU"
                  className="h-10 w-10 object-contain rounded bg-white p-1"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
                <div>
                  <a
                    href="https://hai.snu.ac.kr/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-white font-semibold hover:text-blue-400 transition-colors"
                  >
                    Hyperautonomy AI Lab
                  </a>
                  <p className="text-xs text-gray-500">Seoul National University</p>
                </div>
              </div>

              {/* Subscribe / Tools */}
              <div className="flex items-center gap-4 text-sm">
                <a
                  href="/api/feed/rss"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-white hover:text-orange-400 transition-colors"
                  title="Feedly/Inoreader 등록"
                >
                  <span className="text-orange-500">📡</span> RSS
                </a>
                <a
                  href="https://github.com/juhyun-hai/Paper-Agents/tree/master/mcp_server"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-white hover:text-indigo-400 transition-colors"
                  title="Claude Desktop / Cursor에서 hotpaper 검색"
                >
                  <span className="text-indigo-400">🔌</span> MCP
                </a>
              </div>

              {/* Developer */}
              <div className="text-center md:text-right">
                <p className="text-sm">
                  Developed by{' '}
                  <a
                    href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-white font-medium hover:text-blue-400 transition-colors"
                  >
                    Juhyun Kim
                  </a>
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  © 2026 Hot Paper
                </p>
              </div>
            </div>
          </div>
        </footer>

        {/* Floating Paper Agent button — accessible from every page */}
        <button
          onClick={() => setAgentOpen(true)}
          aria-label="Paper Agent 열기"
          title="Paper Agent (Beta)"
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 px-4 py-3 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg hover:shadow-xl transition-all"
        >
          <span className="text-xl leading-none">🤖</span>
          <span className="hidden sm:inline font-medium text-sm">Paper Agent</span>
        </button>

        <PaperAgentModal isOpen={agentOpen} onClose={() => setAgentOpen(false)} />
      </div>
    </Router>
  );
}

export default App;
