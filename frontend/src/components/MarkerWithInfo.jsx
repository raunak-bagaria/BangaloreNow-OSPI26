import { AdvancedMarker, InfoWindow, useAdvancedMarkerRef, Pin, Marker, useMap } from "@vis.gl/react-google-maps";
import { MapPin, X } from "lucide-react";
import { useCallback, useState, useEffect, useRef } from "react";
import MarkerInfoWindow from "@/components/MarkerInfoWindow";
import { Badge } from "@/components/ui/badge";

const MarkerWithInfo = ({ 
  position, 
  currentZoom, 
  eventId, 
  isSelected, 
  eventDetails, 
  isLoadingDetails, 
  onMarkerClick, 
  onInfoClose 
}) => {
    const [isHovered, setIsHovered] = useState(false);
    const [markerRef, marker] = useAdvancedMarkerRef();
    const infoWindowRef = useRef(null);
    const map = useMap(); // Get access to the map instance

    // Calculate radius size based on zoom level
    const getRadiusSize = () => {
        if (!currentZoom) return 0;
        
        // Only show radius when zoomed in (zoom > 14)
        if (currentZoom <= 14) return 0;
        
        // Scale radius based on zoom level
        const baseSize = 20;
        const zoomScale = Math.max(0, (currentZoom - 14) * 8); // Increases by 8px per zoom level
        return baseSize + zoomScale;
    };

    const radiusSize = getRadiusSize();

    const handleMarkerClick = useCallback(() => {
        onMarkerClick(eventId);
        
        // Pan to marker when clicked (smooth animation)
        if (map && !isSelected) {
            map.panTo(position);
        }
    }, [map, position, isSelected, eventId, onMarkerClick]);
    
    const handleInfoClose = useCallback(() => {
        onInfoClose();
        
        // Optional: Reset map view when closing info window
        if (map) {
            // Small zoom out for better context
            const currentZoom = map.getZoom();
            if (currentZoom && currentZoom > 12) {
                map.setZoom(Math.max(12, currentZoom - 1));
            }
        }
    },[map]);

    const handleMarkerHover = useCallback(() => {
        setIsHovered(true);
    }, []);

    const handleMarkerLeave = useCallback(() => {
        setIsHovered(false);
    }, []);

    // Close info window when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (isSelected && infoWindowRef.current && !infoWindowRef.current.contains(event.target)) {
                onInfoClose();
            }
        };

        if (isSelected) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isSelected, onInfoClose]);

    return(
        <>
            {/* Background glowing circle that appears only when zoomed in */}
            {radiusSize > 0 && (
                <AdvancedMarker
                    position={position}
                    zIndex={0}
                >
                    <div 
                        className={`rounded-full transition-all duration-500 ease-out ${
                            isSelected ? 'bg-green-400/40' : isHovered ? 'bg-green-500/30' : 'bg-green-600/25'
                        }`}
                        style={{
                            width: `${radiusSize}px`,
                            height: `${radiusSize}px`,
                            boxShadow: isSelected 
                                ? `0 0 ${radiusSize/1.5}px rgba(34, 197, 94, 0.8), 0 0 ${radiusSize}px rgba(34, 197, 94, 0.6), 0 0 ${radiusSize*1.5}px rgba(34, 197, 94, 0.3)`
                                : isHovered 
                                ? `0 0 ${radiusSize/2}px rgba(34, 197, 94, 0.7), 0 0 ${radiusSize}px rgba(34, 197, 94, 0.4), 0 0 ${radiusSize*1.2}px rgba(34, 197, 94, 0.2)`
                                : `0 0 ${radiusSize/2.5}px rgba(34, 197, 94, 0.6), 0 0 ${radiusSize/1.5}px rgba(34, 197, 94, 0.3), 0 0 ${radiusSize}px rgba(34, 197, 94, 0.15)`,
                            animation: isSelected ? 'pulse 2s infinite' : 'none'
                        }}
                    />
                </AdvancedMarker>
            )}
            
            <AdvancedMarker
                ref={markerRef}
                position={position}
                onClick={handleMarkerClick}
                onMouseEnter={handleMarkerHover}
                onMouseLeave={handleMarkerLeave}
                zIndex={isSelected ? 999 : 1}
                className="transition-all duration-300 ease-out"
            >
                {/* Dark themed Pin with enhanced glow effect */}
                <div 
                    className={`transition-all duration-300 ease-out ${
                        isSelected ? 'drop-shadow-[0_0_20px_rgba(34,197,94,0.9)]' : 
                        isHovered ? 'drop-shadow-[0_0_15px_rgba(34,197,94,0.7)]' : 
                        'drop-shadow-[0_0_10px_rgba(34,197,94,0.5)]'
                    }`}
                    style={{
                        filter: isSelected 
                            ? 'drop-shadow(0 0 20px rgba(34, 197, 94, 0.9)) drop-shadow(0 0 40px rgba(34, 197, 94, 0.4))'
                            : isHovered 
                            ? 'drop-shadow(0 0 15px rgba(34, 197, 94, 0.7)) drop-shadow(0 0 30px rgba(34, 197, 94, 0.3))'
                            : 'drop-shadow(0 0 10px rgba(34, 197, 94, 0.5)) drop-shadow(0 0 20px rgba(34, 197, 94, 0.2))'
                    }}
                >
                    <Pin
                        background="hsl(0 0% 3.9%)"
                        borderColor="hsl(0 0% 14.9%)"
                        glyphColor="hsl(142 76% 36%)"
                        scale={isSelected ? 1.3 : isHovered ? 1.1 : 1}
                    />
                </div>
            </AdvancedMarker>
            {isSelected && (
                <AdvancedMarker
                    position={position}
                    zIndex={1000}
                >
                    <div 
                        ref={infoWindowRef}
                        className="animate-in fade-in-0 zoom-in-95 duration-500 ease-out"
                    >
                        <MarkerInfoWindow
                            MarkerRef={marker}
                            MarkerId={eventId}
                            eventDetails={eventDetails}
                            isLoadingDetails={isLoadingDetails}
                            handleInfoClose={handleInfoClose}
                        />
                    </div>
                </AdvancedMarker>
            )}
        </>
    );
}

export default MarkerWithInfo;