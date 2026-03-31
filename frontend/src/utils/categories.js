/**
 * Category metadata for ArXiv categories used in this project.
 * Display format: "Full Name (code)"
 */
export const CATEGORY_LABELS = {
  'cs.CL': 'Natural Language Processing',
  'cs.CV': 'Computer Vision',
  'cs.LG': 'Machine Learning',
  'cs.AI': 'Artificial Intelligence',
  'stat.ML': 'Statistics - ML',
  'cs.NE': 'Neural & Evolutionary Computing',
  'cs.RO': 'Robotics',
  'cs.IR': 'Information Retrieval',
  'hai': 'HAI Lab (SNU)',
}

export const CATEGORY_COLORS = {
  'cs.CL': '#1a73e8',
  'cs.CV': '#34a853',
  'cs.LG': '#ea4335',
  'cs.AI': '#7c3aed',
  'stat.ML': '#f59e0b',
  'cs.NE': '#06b6d4',
  'cs.RO': '#ec4899',
  'cs.IR': '#84cc16',
  'hai': '#0f766e',
}

export const CATEGORY_TAILWIND = {
  'cs.CL': 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  'cs.CV': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  'cs.LG': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  'cs.AI': 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  'stat.ML': 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  'cs.NE': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
  'cs.RO': 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
  'cs.IR': 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300',
  'hai': 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300',
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
