import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Home from './pages/Home.jsx'
import Search from './pages/Search.jsx'
import Paper from './pages/Paper.jsx'
import Graph from './pages/Graph.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Feedback from './pages/Feedback.jsx'
import AdminFeedback from './pages/AdminFeedback.jsx'

export default function App() {
  const [dark, setDark] = useState(() => {
    return localStorage.getItem('dark') === 'true'
  })

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('dark', dark)
  }, [dark])

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
        <Navbar dark={dark} onToggleDark={() => setDark((d) => !d)} />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/paper/:arxiv_id" element={<Paper />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/admin/feedback" element={<AdminFeedback />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
