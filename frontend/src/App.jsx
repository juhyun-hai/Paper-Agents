import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import TrendingPapers from './components/TrendingPapers';
import Navigation from './components/Navigation';
import Home from './pages/Home';
import Search from './pages/Search';
import Paper from './pages/Paper';
import './App.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <Navigation />

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/trending" element={<TrendingPapers />} />
            <Route path="/search" element={<Search />} />
            <Route path="/paper/:arxiv_id" element={<Paper />} />
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

              {/* Developer */}
              <div className="text-center md:text-right">
                <p className="text-sm">
                  Developed by <span className="text-white font-medium">Juhyun Kim</span>
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  © 2026 Hot Paper · Powered by Claude AI
                </p>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
