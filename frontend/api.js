/**
 * Zomato AI Recommender — API Utility Module
 * Handles all communication with the FastAPI backend.
 */

/**
 * API Base URL — uses the Railway backend in production,
 * falls back to localhost for local development.
 * TODO: Replace the Railway URL below with your actual deployed URL.
 */
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://your-service-name.up.railway.app';  // ← Replace with your Railway URL

/**
 * Generic fetch wrapper with error handling.
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || `Request failed with status ${response.status}`);
    }

    return data.data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Cannot connect to the backend server. Make sure the FastAPI server is running on port 8000.');
    }
    throw err;
  }
}

/**
 * Fetch all unique locations for the dropdown.
 * @returns {Promise<string[]>}
 */
async function fetchLocations() {
  return apiFetch('/api/meta/locations');
}

/**
 * Fetch all unique cuisines for the dropdown.
 * @returns {Promise<string[]>}
 */
async function fetchCuisines() {
  return apiFetch('/api/meta/cuisines');
}

/**
 * Get AI restaurant recommendations.
 * @param {Object} preferences
 * @param {string} preferences.location
 * @param {string} [preferences.cuisine]
 * @param {string} [preferences.budget]
 * @param {number} [preferences.min_rating]
 * @param {string} [preferences.extra_preferences]
 * @returns {Promise<Object>}
 */
async function fetchRecommendations(preferences) {
  return apiFetch('/api/restaurants/recommend', {
    method: 'POST',
    body: JSON.stringify(preferences),
  });
}

/**
 * Health check.
 * @returns {Promise<Object>}
 */
async function healthCheck() {
  return apiFetch('/health');
}
