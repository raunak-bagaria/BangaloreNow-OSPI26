import React from 'react';
import { useApiLoadingStatus, APILoadingStatus } from '@vis.gl/react-google-maps';

const MapErrorBoundary = ({ children }) => {
  const loadingStatus = useApiLoadingStatus();

  if (loadingStatus === APILoadingStatus.FAILED) {
    return (
      <div className="w-full h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4 p-8 bg-card border border-border rounded-lg shadow-lg">
          <div className="text-red-500 text-4xl">⚠️</div>
          <h2 className="text-xl font-semibold text-foreground">Failed to Load Maps</h2>
          <p className="text-muted-foreground">
            There was an error loading Google Maps. Please check your internet connection and try refreshing the page.
          </p>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-accent hover:bg-accent/80 text-accent-foreground rounded-md transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return children;
};

export default MapErrorBoundary;
