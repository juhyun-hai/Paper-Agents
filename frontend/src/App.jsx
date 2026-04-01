import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ResearchDashboard from './components/ResearchDashboard';
import GraphExplorer from './components/GraphExplorer';
import TrendingPapers from './components/TrendingPapers';
import Navigation from './components/Navigation';
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
            <Route path="/" element={<Navigate to="/research" replace />} />
            <Route path="/research" element={<ResearchDashboard />} />
            <Route path="/graph" element={<GraphExplorer />} />
            <Route path="/trending" element={<TrendingPapers />} />
            <Route path="/search" element={<Search />} />
            <Route path="/paper/:arxiv_id" element={<Paper />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
