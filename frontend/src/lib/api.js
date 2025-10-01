// API configuration utility
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Validate required environment variables
if (!import.meta.env.VITE_GOOGLE_MAPS_API_KEY) {
  console.warn('VITE_GOOGLE_MAPS_API_KEY is not set. Google Maps may not work properly.');
}

if (!import.meta.env.VITE_GOOGLE_MAPS_MAP_ID) {
  console.warn('VITE_GOOGLE_MAPS_MAP_ID is not set. Advanced markers may not work properly.');
}

export const getApiUrl = (endpoint) => {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${API_BASE_URL}/${cleanEndpoint}`;
};

export const API_ENDPOINTS = {
  GET_ALL_EVENTS: 'api/get-all-events',
  GET_EVENT_DETAILS: (eventId) => `api/get-event-details/${eventId}`,
};

// Export environment variables for use in components
export const ENV = {
  API_BASE_URL,
  GOOGLE_MAPS_API_KEY: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
  GOOGLE_MAPS_MAP_ID: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID,
};

export default {
  getApiUrl,
  API_ENDPOINTS,
  ENV,
};