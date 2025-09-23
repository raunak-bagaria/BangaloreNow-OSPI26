import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { X, Maximize2 } from "lucide-react";

const BASEURL = "YOUR_BACKEND_URL"; 

const MarkerInfoWindow = ({ MarkerRef, MarkerId, eventDetails, isLoadingDetails, handleInfoClose }) => {
    const [showFullImage, setShowFullImage] = useState(false);

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
                <div className="flex flex-col gap-3 sm:gap-4 lg:gap-5 xl:gap-6 px-3 sm:px-5 lg:px-6 xl:px-7 py-3 sm:py-4 lg:py-5 xl:py-6">
                    {isLoadingDetails ? (
                        <div className="space-y-3">
                            <div className="animate-pulse">
                                <div className="h-6 bg-muted rounded w-3/4 mb-2"></div>
                                <div className="h-4 bg-muted rounded w-full mb-1"></div>
                                <div className="h-4 bg-muted rounded w-5/6"></div>
                            </div>
                        </div>
                    ) : eventDetails ? (
                        <>
                            {/* Event Details */}
                            <div className="space-y-3 sm:space-y-3 lg:space-y-4 xl:space-y-5 opacity-0 animate-fadeInRight" style={{ animationDelay: '0.2s', animationFillMode: 'forwards' }}>
                                {/* Title */}
                                <div>
                                    <h3 className="text-card-foreground text-base sm:text-lg lg:text-xl xl:text-2xl font-semibold leading-tight">
                                        {eventDetails.title}
                                    </h3>
                                    <div className="flex items-center justify-between mt-1">
                                        <p className="text-muted-foreground text-sm">
                                            By {eventDetails.author}
                                        </p>
                                        {/* Optional: Show cache indicator */}
                                        <span className="text-xs text-muted-foreground/60">
                                            {isLoadingDetails ? "⏳" : "💾"}
                                        </span>
                                    </div>
                                </div>
                                
                                {/* Date Information */}
                                <div className="space-y-1">
                                    <p className="text-muted-foreground text-xs sm:text-sm">
                                        📅 {new Date(eventDetails.start_date).toLocaleDateString()} - {new Date(eventDetails.end_date).toLocaleDateString()}
                                    </p>
                                </div>
                                
                                {/* Description */}
                                <div className="space-y-2 lg:space-y-3">
                                    <p className="text-muted-foreground text-xs sm:text-sm lg:text-base leading-relaxed line-clamp-3 sm:line-clamp-4">
                                        {eventDetails.description}
                                    </p>
                                </div>
                                
                                <div className="h-px bg-border my-2 sm:my-3"></div>
                                
                                {/* Tags section */}
                                <div className="space-y-1.5 sm:space-y-2 lg:space-y-3">
                                    <p className="text-muted-foreground text-xs lg:text-sm font-medium uppercase tracking-wide">
                                        Tags
                                    </p>
                                    <div className="flex flex-wrap gap-1 sm:gap-1.5 lg:gap-2">
                                        {eventDetails.keyword_names && eventDetails.keyword_names.map((tag, idx) => (
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
                                
                                {/* Source Link */}
                                {eventDetails.source && (
                                    <div className="pt-2">
                                        <a 
                                            href={eventDetails.source}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center text-sm text-accent hover:text-accent/80 underline underline-offset-4 transition-colors"
                                        >
                                            🔗 View Event Details →
                                        </a>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="text-center py-4">
                            <p className="text-muted-foreground text-sm">Failed to load event details</p>
                        </div>
                    )}
                </div>
                
                {/* Pointer/Arrow with smoother animation */}
                <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 opacity-0 animate-fadeIn" style={{ animationDelay: '0.3s', animationFillMode: 'forwards' }}>
                    <div className="w-4 h-4 bg-card border-r border-b border-border transform rotate-45"></div>
                </div>
            </div>
        </div>
    );
};

export default MarkerInfoWindow;