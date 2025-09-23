import React, { useState, useCallback, useEffect, useRef } from 'react';
import { APIProvider, Map, useApiLoadingStatus, useApiIsLoaded } from '@vis.gl/react-google-maps';
import MarkerwithInfo from './MarkerWithInfo.jsx';
import MapErrorBoundary from './MapErrorBoundary.jsx';
import Navbar from './Navbar.jsx';

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// Loading component to show while API loads
const LoadingOverlay = () => {
  const apiLoadingStatus = useApiLoadingStatus();
  const apiIsLoaded = useApiIsLoaded();

  if (apiIsLoaded) return null;

  const getLoadingMessage = () => {
    switch (apiLoadingStatus) {
      case 'LOADING':
        return 'Loading Google Maps...';
      case 'LOADED':
        return 'Maps loaded, initializing...';
      case 'FAILED':
        return 'Failed to load Maps';
      default:
        return 'Initializing...';
    }
  };

  return (
    <div className="absolute inset-0 bg-background/90 flex items-center justify-center z-50">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
        <p className="text-foreground font-medium">{getLoadingMessage()}</p>
        {apiLoadingStatus === 'LOADING' && (
          <p className="text-muted-foreground text-sm">Please wait while we load the map...</p>
        )}
      </div>
    </div>
  );
};

const MapComponent = () => {
  // Default Bangalore coordinates
  const defaultCenter = { lat: 12.9716, lng: 77.5946 };
  const [currentZoom, setCurrentZoom] = useState(12);
  const [isMapMoving, setIsMapMoving] = useState(false);
  
  // Event data states
  const [events, setEvents] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [eventDetailsCache, setEventDetailsCache] = useState({}); // Cache for event details
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  
  // Debouncing refs for navbar animation
  const minimizeTimeoutRef = useRef(null);
  const expandTimeoutRef = useRef(null);
  const fallbackTimeoutRef = useRef(null); // Fallback to ensure navbar always returns
  
  // API Functions
  const fetchAllEvents = async () => {
    try {
      setIsLoadingEvents(true);
      const response = await fetch(`${API_BASE_URL}/get-all-events`);
      if (!response.ok) {
        throw new Error('Failed to fetch events');
      }
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error('Error fetching events:', error);
      setEvents([]);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  const fetchEventDetails = async (eventId) => {
    // Check if we already have the details cached
    if (eventDetailsCache[eventId]) {
      console.log(`Using cached details for event ${eventId}`);
      return eventDetailsCache[eventId];
    }

    try {
      setIsLoadingDetails(true);
      console.log(`Fetching details for event ${eventId}`);
      const response = await fetch(`${API_BASE_URL}/get-event-details/${eventId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch event details');
      }
      const data = await response.json();
      
      // Cache the fetched details
      setEventDetailsCache(prev => ({
        ...prev,
        [eventId]: data
      }));
      
      return data;
    } catch (error) {
      console.error('Error fetching event details:', error);
      return null;
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // Handle marker click with lazy loading and caching
  const handleMarkerClick = useCallback(async (eventId) => {
    setSelectedEvent(eventId);
    
    // Only fetch if not already cached
    if (!eventDetailsCache[eventId]) {
      await fetchEventDetails(eventId);
    }
  }, [eventDetailsCache]);

  // Handle info window close
  const handleInfoClose = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  // Load events on component mount
  useEffect(() => {
    fetchAllEvents();
  }, []);
  
  // Use dark-themed map ID (create a separate one in Cloud Console for dark theme)
  const DARK_MAP_ID = 'da06caae89cc4238b61f553a'; // Configure this as dark in Cloud Console
  
  // Bangalore city boundaries (approximate)
  const bangaloreBounds = {
    north: 13.15, // North boundary
    south: 12.75, // South boundary  
    east: 77.85,  // East boundary
    west: 77.35   // West boundary
  };
  
  // Map options with restrictions
  const mapOptions = {
    restriction: {
      latLngBounds: bangaloreBounds,
      strictBounds: true
    },
    minZoom: 11,
    maxZoom: 18,
    gestureHandling: 'greedy',
    disableDefaultUI: false,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    mapTypeId: 'roadmap', // Use roadmap with dark styling
    // Remove styles when using mapId - configure in Cloud Console instead
  };

  // Handle zoom changes
  const handleZoomChanged = useCallback((map) => {
    const zoom = map.detail.zoom;
    setCurrentZoom(zoom);
  }, []);

  // Handle map movement start
  const handleDragStart = useCallback(() => {
    // Clear any pending expand and fallback timeouts
    if (expandTimeoutRef.current) {
      clearTimeout(expandTimeoutRef.current);
      expandTimeoutRef.current = null;
    }
    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
    
    // Only minimize after a delay to avoid flickering on quick movements
    if (!minimizeTimeoutRef.current) {
      minimizeTimeoutRef.current = setTimeout(() => {
        setIsMapMoving(true);
        minimizeTimeoutRef.current = null;
        
        // Set fallback timeout to ensure navbar returns even if end events are missed
        fallbackTimeoutRef.current = setTimeout(() => {
          setIsMapMoving(false);
          fallbackTimeoutRef.current = null;
        }, 5000); // 5 second fallback
      }, 300); // 300ms delay before minimizing
    }
  }, []);

  // Handle map movement end
  const handleDragEnd = useCallback(() => {
    // Clear minimize timeout if movement stopped quickly
    if (minimizeTimeoutRef.current) {
      clearTimeout(minimizeTimeoutRef.current);
      minimizeTimeoutRef.current = null;
      return; // Don't set to false if we never set to true
    }
    
    // Clear fallback timeout since we have a proper end event
    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
    
    // Add delay before expanding to ensure smooth animation
    expandTimeoutRef.current = setTimeout(() => {
      setIsMapMoving(false);
      expandTimeoutRef.current = null;
    }, 200);
  }, []);

  // Handle zoom start (also considered movement)
  const handleZoomStart = useCallback(() => {
    // Clear any pending expand and fallback timeouts
    if (expandTimeoutRef.current) {
      clearTimeout(expandTimeoutRef.current);
      expandTimeoutRef.current = null;
    }
    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
    
    // Only minimize after a delay to avoid flickering on quick movements
    if (!minimizeTimeoutRef.current) {
      minimizeTimeoutRef.current = setTimeout(() => {
        setIsMapMoving(true);
        minimizeTimeoutRef.current = null;
        
        // Set fallback timeout to ensure navbar returns even if end events are missed
        fallbackTimeoutRef.current = setTimeout(() => {
          setIsMapMoving(false);
          fallbackTimeoutRef.current = null;
        }, 5000); // 5 second fallback
      }, 300); // 300ms delay before minimizing
    }
  }, []);

  // Handle zoom end
  const handleZoomEnd = useCallback(() => {
    // Clear minimize timeout if movement stopped quickly
    if (minimizeTimeoutRef.current) {
      clearTimeout(minimizeTimeoutRef.current);
      minimizeTimeoutRef.current = null;
      return; // Don't set to false if we never set to true
    }
    
    // Clear fallback timeout since we have a proper end event
    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
    
    // Add delay before expanding
    expandTimeoutRef.current = setTimeout(() => {
      setIsMapMoving(false);
      expandTimeoutRef.current = null;
    }, 200);
  }, []);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (minimizeTimeoutRef.current) {
        clearTimeout(minimizeTimeoutRef.current);
      }
      if (expandTimeoutRef.current) {
        clearTimeout(expandTimeoutRef.current);
      }
      if (fallbackTimeoutRef.current) {
        clearTimeout(fallbackTimeoutRef.current);
      }
    };
  }, []);
  
  return (
    <div className="w-full h-screen bg-gray-900 relative">
      <APIProvider apiKey="AIzaSyCTWEDs6_36PKstsj2jfzZzs4TqxquA1RA">
        <MapErrorBoundary>
          <LoadingOverlay />
          <Map
            defaultCenter={defaultCenter}
            defaultZoom={12}
            options={mapOptions}
            className="w-full h-full"
            mapId={DARK_MAP_ID}
            colorScheme="DARK"
            onZoomChanged={handleZoomChanged}
            onDragstart={handleDragStart}
            onDragend={handleDragEnd}
            onZoomStart={handleZoomStart}
            onZoomEnd={handleZoomEnd}
          >
            {/* Render markers for all events */}
            {!isLoadingEvents && events.map((event) => (
              <MarkerwithInfo
                key={event.id}
                position={{ lat: event.latitude, lng: event.longitude }}
                currentZoom={currentZoom}
                eventId={event.id}
                isSelected={selectedEvent === event.id}
                eventDetails={selectedEvent === event.id ? eventDetailsCache[event.id] : null}
                isLoadingDetails={selectedEvent === event.id ? isLoadingDetails : false}
                onMarkerClick={handleMarkerClick}
                onInfoClose={handleInfoClose}
              />
            ))}
          </Map>
          <Navbar isMapMoving={isMapMoving} />
        </MapErrorBoundary>
      </APIProvider>
    </div>
  );
};

export default MapComponent;
