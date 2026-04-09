/**
 * Category metadata for ArXiv categories used in this project.
 * Display format: "Full Name (code)"
 */
export const CATEGORY_LABELS = {
  'cs.LG': 'Machine Learning',
  'cs.AI': 'Artificial Intelligence',
  'cs.CV': 'Computer Vision',
  'cs.CL': 'Natural Language Processing',
  'stat.ML': 'Statistics - ML',
  'cs.IR': 'Information Retrieval',
  'cs.HC': 'Human-Computer Interaction',
  'cs.RO': 'Robotics',
  'cs.CY': 'Computers & Society',
  'stat.ME': 'Statistics - Methodology',
  'math.ST': 'Statistics Theory',
  'math.OC': 'Optimization & Control',
  'cs.SE': 'Software Engineering',
  'cs.MA': 'Multi-Agent Systems',
  'cs.CR': 'Cryptography & Security',
  'cs.SD': 'Sound',
  'cs.MM': 'Multimedia',
  'stat.AP': 'Statistics - Applications',
  'cs.NE': 'Neural & Evolutionary Computing',
  'cs.DB': 'Databases',
  'cs.GR': 'Graphics',
  'eess.SY': 'Systems & Control',
  'cs.DC': 'Distributed Computing',
  'cs.SI': 'Social & Info Networks',
  'quant-ph': 'Quantum Physics',
  'cs.DL': 'Digital Libraries',
  'eess.IV': 'Image & Video Processing',
  'eess.AS': 'Audio & Speech Processing',
  'cs.PL': 'Programming Languages',
  'cs.IT': 'Information Theory',
}

export const CATEGORY_COLORS = {
  'cs.LG': '#ea4335',
  'cs.AI': '#7c3aed',
  'cs.CV': '#34a853',
  'cs.CL': '#1a73e8',
  'stat.ML': '#f59e0b',
  'cs.IR': '#84cc16',
  'cs.HC': '#14b8a6',
  'cs.RO': '#ec4899',
  'cs.CY': '#8b5cf6',
  'stat.ME': '#d97706',
  'math.ST': '#b45309',
  'math.OC': '#0d9488',
  'cs.SE': '#6366f1',
  'cs.MA': '#e11d48',
  'cs.CR': '#dc2626',
  'cs.SD': '#a855f7',
  'cs.MM': '#f472b6',
  'stat.AP': '#ca8a04',
  'cs.NE': '#06b6d4',
  'cs.DB': '#0ea5e9',
  'cs.GR': '#10b981',
  'eess.SY': '#64748b',
  'cs.DC': '#475569',
  'cs.SI': '#f97316',
  'quant-ph': '#2dd4bf',
  'cs.DL': '#78716c',
  'eess.IV': '#22c55e',
  'eess.AS': '#c084fc',
  'cs.PL': '#fb923c',
  'cs.IT': '#38bdf8',
}

export const CATEGORY_TAILWIND = {
  'cs.LG': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  'cs.AI': 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  'cs.CV': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  'cs.CL': 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  'stat.ML': 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  'cs.IR': 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300',
  'cs.HC': 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300',
  'cs.RO': 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
  'cs.CY': 'bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300',
  'stat.ME': 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  'math.ST': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  'math.OC': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  'cs.SE': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300',
  'cs.MA': 'bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300',
  'cs.CR': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  'cs.SD': 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900 dark:text-fuchsia-300',
  'cs.MM': 'bg-pink-100 text-pink-600 dark:bg-pink-900 dark:text-pink-300',
  'stat.AP': 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  'cs.NE': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
  'cs.DB': 'bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300',
  'cs.GR': 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300',
  'eess.SY': 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  'cs.DC': 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  'cs.SI': 'bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-300',
  'quant-ph': 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  'cs.DL': 'bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300',
  'eess.IV': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  'eess.AS': 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300',
  'cs.PL': 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200',
  'cs.IT': 'bg-sky-100 text-sky-600 dark:bg-sky-900 dark:text-sky-300',
}

/**
 * Returns "Full Name (code)" format for display
 */
export function getCategoryLabel(code) {
  const name = CATEGORY_LABELS[code]
  return name ? `${name} (${code})` : code
}

/**
 * Returns just the full name, or code if not found
 */
export function getCategoryName(code) {
  return CATEGORY_LABELS[code] || code
}

export const ALL_CATEGORIES = Object.keys(CATEGORY_LABELS)
