/**
 * Personal Collections Management (LocalStorage)
 */

const STORAGE_KEY = 'paper_collections'
const COLLECTIONS_KEY = 'paper_collections_meta'

// Initialize storage structure
const initStorage = () => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
  }
  if (!localStorage.getItem(COLLECTIONS_KEY)) {
    localStorage.setItem(COLLECTIONS_KEY, JSON.stringify({
      'saved': { name: '저장된 논문', color: 'blue', count: 0 },
      'to-read': { name: '읽을 예정', color: 'orange', count: 0 },
      'favorites': { name: '즐겨찾기', color: 'red', count: 0 }
    }))
  }
}

// Get all saved papers
export const getSavedPapers = () => {
  initStorage()
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

// Get collections metadata
export const getCollections = () => {
  initStorage()
  try {
    return JSON.parse(localStorage.getItem(COLLECTIONS_KEY) || '{}')
  } catch {
    return {}
  }
}

// Check if paper is saved
export const isPaperSaved = (arxivId) => {
  const savedPapers = getSavedPapers()
  return savedPapers.some(paper => paper.arxiv_id === arxivId)
}

// Save paper to collection
export const savePaper = (paper, collectionId = 'saved') => {
  initStorage()
  const savedPapers = getSavedPapers()
  const collections = getCollections()

  // Check if already saved
  if (isPaperSaved(paper.arxiv_id)) {
    return { success: false, message: '이미 저장된 논문입니다' }
  }

  // Add to saved papers
  const paperToSave = {
    ...paper,
    savedAt: new Date().toISOString(),
    collection: collectionId
  }

  savedPapers.push(paperToSave)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedPapers))

  // Update collection count
  if (collections[collectionId]) {
    collections[collectionId].count += 1
    localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(collections))
  }

  return { success: true, message: `"${collections[collectionId]?.name || '컬렉션'}"에 저장되었습니다` }
}

// Remove paper from collection
export const removePaper = (arxivId) => {
  const savedPapers = getSavedPapers()
  const collections = getCollections()

  const paperIndex = savedPapers.findIndex(paper => paper.arxiv_id === arxivId)
  if (paperIndex === -1) {
    return { success: false, message: '저장되지 않은 논문입니다' }
  }

  const paper = savedPapers[paperIndex]
  const collectionId = paper.collection || 'saved'

  // Remove from saved papers
  savedPapers.splice(paperIndex, 1)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedPapers))

  // Update collection count
  if (collections[collectionId] && collections[collectionId].count > 0) {
    collections[collectionId].count -= 1
    localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(collections))
  }

  return { success: true, message: '저장된 논문에서 제거되었습니다' }
}

// Move paper to different collection
export const movePaper = (arxivId, newCollectionId) => {
  const savedPapers = getSavedPapers()
  const collections = getCollections()

  const paperIndex = savedPapers.findIndex(paper => paper.arxiv_id === arxivId)
  if (paperIndex === -1) {
    return { success: false, message: '저장되지 않은 논문입니다' }
  }

  const paper = savedPapers[paperIndex]
  const oldCollectionId = paper.collection || 'saved'

  // Update paper collection
  savedPapers[paperIndex] = { ...paper, collection: newCollectionId }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedPapers))

  // Update collection counts
  if (collections[oldCollectionId]) {
    collections[oldCollectionId].count = Math.max(0, collections[oldCollectionId].count - 1)
  }
  if (collections[newCollectionId]) {
    collections[newCollectionId].count += 1
  }
  localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(collections))

  return {
    success: true,
    message: `"${collections[newCollectionId]?.name || '컬렉션'}"으로 이동되었습니다`
  }
}

// Get papers by collection
export const getPapersByCollection = (collectionId) => {
  const savedPapers = getSavedPapers()
  return savedPapers.filter(paper => paper.collection === collectionId)
}

// Search in saved papers
export const searchSavedPapers = (query) => {
  const savedPapers = getSavedPapers()
  if (!query.trim()) return savedPapers

  const lowerQuery = query.toLowerCase()
  return savedPapers.filter(paper =>
    (paper.title || '').toLowerCase().includes(lowerQuery) ||
    (paper.authors || []).some(author => author.toLowerCase().includes(lowerQuery)) ||
    (paper.abstract || '').toLowerCase().includes(lowerQuery)
  )
}

// Get storage stats
export const getStorageStats = () => {
  const savedPapers = getSavedPapers()
  const collections = getCollections()

  const storageSize = new Blob([JSON.stringify(savedPapers)]).size
  const maxSize = 5 * 1024 * 1024 // 5MB typical localStorage limit

  return {
    totalPapers: savedPapers.length,
    collections: Object.keys(collections).length,
    storageUsed: storageSize,
    storagePercent: (storageSize / maxSize * 100).toFixed(1),
    oldestPaper: savedPapers.length > 0 ? savedPapers.reduce((oldest, paper) =>
      new Date(paper.savedAt) < new Date(oldest.savedAt) ? paper : oldest
    ).savedAt : null
  }
}

// Export collections (for backup)
export const exportCollections = () => {
  const savedPapers = getSavedPapers()
  const collections = getCollections()

  const exportData = {
    version: '1.0',
    exportedAt: new Date().toISOString(),
    papers: savedPapers,
    collections,
    stats: getStorageStats()
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `paper-collections-${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Import collections (from backup)
export const importCollections = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)

        if (!data.papers || !Array.isArray(data.papers)) {
          throw new Error('Invalid backup file format')
        }

        // Merge with existing data
        const existingPapers = getSavedPapers()
        const newPapers = data.papers.filter(newPaper =>
          !existingPapers.some(existing => existing.arxiv_id === newPaper.arxiv_id)
        )

        const mergedPapers = [...existingPapers, ...newPapers]
        localStorage.setItem(STORAGE_KEY, JSON.stringify(mergedPapers))

        // Update collection metadata
        const collections = getCollections()
        const updatedCollections = { ...collections }

        // Recalculate counts
        Object.keys(updatedCollections).forEach(key => {
          updatedCollections[key].count = mergedPapers.filter(p => p.collection === key).length
        })

        localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(updatedCollections))

        resolve({
          success: true,
          imported: newPapers.length,
          total: mergedPapers.length
        })
      } catch (error) {
        reject({ success: false, error: error.message })
      }
    }

    reader.onerror = () => reject({ success: false, error: 'Failed to read file' })
    reader.readAsText(file)
  })
}