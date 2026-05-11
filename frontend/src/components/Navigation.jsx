import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navigation = () => {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const navItems = [
    { path: '/',         label: 'Home',     icon: '🏠', description: 'Hot Paper homepage' },
    { path: '/search',   label: 'Search',   icon: '🔍', description: 'Search and browse papers' },
    { path: '/trending', label: 'Trending', icon: '🔥', description: 'Discover hottest papers' },
    { path: '/hai',      label: 'HAI Picks', icon: '🎓', description: 'HAI Lab featured papers' },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">🔥</span>
              </div>
              <div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  Hot Paper
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 -mt-1">
                  AI Research Trend Discovery
                </div>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:block">
            <div className="flex items-center space-x-6">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200'
                        : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    <span className="mr-2">{item.icon}</span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Lab + developer credit */}
          <div className="hidden md:flex items-center text-xs text-gray-600 dark:text-gray-400 leading-tight text-right">
            <div>
              <div>
                Curated by{' '}
                <a
                  href="https://hai.snu.ac.kr/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400"
                >
                  SNU HAI Lab
                </a>
              </div>
              <div>
                by{' '}
                <a
                  href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400"
                >
                  Juhyun Kim
                </a>
              </div>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            >
              <span className="sr-only">Open main menu</span>
              {!isMenuOpen ? (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              ) : (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 border-t border-gray-200 bg-gray-50">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <div className="flex items-center">
                      <span className="mr-3">{item.icon}</span>
                      <div>
                        <div>{item.label}</div>
                        <div className="text-xs text-gray-500">{item.description}</div>
                      </div>
                    </div>
                  </Link>
                );
              })}

              {/* Lab + developer credit (mobile) */}
              <div className="px-3 py-3 mt-2 border-t border-gray-300 text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <div>
                  Curated by{' '}
                  <a
                    href="https://hai.snu.ac.kr/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-gray-900 dark:text-white"
                  >
                    SNU HAI Lab
                  </a>
                </div>
                <div>
                  by{' '}
                  <a
                    href="https://hai.snu.ac.kr/bbs/board.php?bo_table=sub2_2&wr_id=43&sca=2Ph.D.+student&page=2"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-gray-700 dark:text-gray-300"
                  >
                    Juhyun Kim
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navigation;