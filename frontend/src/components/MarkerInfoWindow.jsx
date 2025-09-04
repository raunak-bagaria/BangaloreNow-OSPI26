import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { X, Maximize2 } from "lucide-react";

const BASEURL = "YOUR_BACKEND_URL"; 

const MarkerInfoWindow = ({ MarkerRef, MarkerId, handleInfoClose }) => {
    const [markerData, setMarkerData] = useState({
  "title": "Bangalore Palace",
  "description": "A historic palace located in Bangalore, known for its beautiful architecture and gardens.",
  "tags": ["historic", "architecture", "tourist spot", "palace"]
});
    const [showFullImage, setShowFullImage] = useState(false);
    
    // const [loading, setLoading] = useState(false); TODO
    // const [error, setError] = useState(null);

//TODO
    // useEffect(() => {
    //     if (!MarkerId) return;
    //     setLoading(true);
    //     setError(null);

    //     const fetchMarkerData = async () => {
    //         try {
    //             const response = await fetch(`${BASEURL}/marker/${MarkerId}`);
    //             if (!response.ok) throw new Error("Failed to fetch marker data");
    //             const data = await response.json();
    //             setMarkerData(data);
    //         } catch (err) {
    //             setError(err.message);
    //         } finally {
    //             setLoading(false);
    //         }
    //     };

    //     fetchMarkerData();
    // }, []); 

    // Example rendering logic
    return (
        <div className="absolute z-50 top-0 left-1/2 transform -translate-x-1/2 -translate-y-full pointer-events-auto">
            <div className="bg-card border border-border rounded-lg shadow-2xl w-80 sm:w-96 lg:w-[32rem] xl:w-[36rem] relative mb-2 mx-2 opacity-0 translate-y-4 animate-slideUp">
                {/* Close button */}
                <button
                    onClick={handleInfoClose}
                    className="absolute top-2 sm:top-3 right-2 sm:right-3 text-muted-foreground hover:text-foreground transition-all duration-200 z-10 p-1 sm:p-1.5 rounded-full hover:bg-secondary"
                >
                    <X size={14} className="sm:hidden" />
                    <X size={16} className="hidden sm:block" />
                </button>
                
                {/* Two-column layout - responsive */}
                <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 lg:gap-5 xl:gap-6 px-3 sm:px-5 lg:px-6 xl:px-7 py-3 sm:py-4 lg:py-5 xl:py-6">
                    {/* Image section */}
                    <div className="w-full sm:flex-shrink-0 sm:w-32 lg:w-48 xl:w-56 opacity-0 animate-fadeInLeft" style={{ animationDelay: '0.1s', animationFillMode: 'forwards' }}>
                        <div className="relative group cursor-pointer" onClick={() => setShowFullImage(true)}>
                            <img 
                                src="/a.jpg" 
                                alt={markerData.title}
                                className="w-full h-32 sm:h-32 lg:h-48 xl:h-56 object-cover rounded-lg border border-border shadow-md group-hover:brightness-110 transition-all duration-200"
                            />
                            {/* Fullscreen icon */}
                            <div className="absolute bottom-2 right-2 bg-background/60 hover:bg-background/80 rounded-md p-1.5 transition-all duration-200 opacity-70 group-hover:opacity-100">
                                <Maximize2 size={14} className="text-foreground" />
                            </div>
                        </div>
                    </div>
                    
                    {/* Right side - Details */}
                    <div className="flex-1 space-y-3 sm:space-y-3 lg:space-y-4 xl:space-y-5 opacity-0 animate-fadeInRight" style={{ animationDelay: '0.2s', animationFillMode: 'forwards' }}>
                        {/* Title */}
                        <div>
                            <h3 className="text-card-foreground text-base sm:text-lg lg:text-xl xl:text-2xl font-semibold leading-tight">
                                {markerData.title}
                            </h3>
                        </div>
                        
                        {/* Description */}
                        <div className="space-y-2 lg:space-y-3">
                            <p className="text-muted-foreground text-xs sm:text-sm lg:text-base xl:text-lg leading-relaxed line-clamp-2 sm:line-clamp-3 lg:line-clamp-4">
                                {markerData.description}
                            </p>
                        </div>
                        
                        <div className="h-px bg-border my-2 sm:my-3"></div>
                        
                        {/* Tags section */}
                        <div className="space-y-1.5 sm:space-y-2 lg:space-y-3">
                            <p className="text-muted-foreground text-xs lg:text-sm font-medium uppercase tracking-wide">
                                Tags
                            </p>
                            <div className="flex flex-wrap gap-1 sm:gap-1.5 lg:gap-2">
                                {markerData.tags.map((tag, idx) => (
                                    <Badge 
                                        key={idx} 
                                        variant="secondary"
                                        className="text-xs h-5 lg:text-sm bg-secondary text-secondary-foreground hover:bg-secondary/80 border-border px-2 sm:px-2.5 lg:px-3 py-0.5 sm:py-1 lg:py-1.5 opacity-0 animate-fadeInScale"
                                        style={{ 
                                            animationDelay: `${0.4 + idx * 0.1}s`,
                                            animationFillMode: 'forwards'
                                        }}
                                    >
                                        {tag}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
                
                {/* Pointer/Arrow with smoother animation */}
                <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 opacity-0 animate-fadeIn" style={{ animationDelay: '0.3s', animationFillMode: 'forwards' }}>
                    <div className="w-4 h-4 bg-card border-r border-b border-border transform rotate-45"></div>
                </div>
            </div>

            {/* Simple Fullscreen Image Modal */}
            {showFullImage && (
                <div 
                    className="fixed inset-0 z-[9999] bg-background/90 flex items-center justify-center"
                    onClick={() => setShowFullImage(false)}
                >
                    <button
                        onClick={() => setShowFullImage(false)}
                        className="absolute top-4 right-4 z-10 text-foreground hover:text-muted-foreground bg-background/50 hover:bg-background/70 rounded-full p-2 transition-all duration-200"
                    >
                        <X size={24} />
                    </button>
                    <img 
                        src="/a.jpg" 
                        alt={markerData.title}
                        className="w-full h-full object-cover"
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            )}
        </div>
    );
};

export default MarkerInfoWindow;