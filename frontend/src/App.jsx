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
      </div>
    </Router>
  );
}

export default App;
