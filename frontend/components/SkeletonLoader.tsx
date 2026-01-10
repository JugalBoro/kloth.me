import { Sparkles } from "lucide-react";
import "@/styles/components/SkeletonLoader.css";

export function SkeletonLoader() {
    return (
        <div className="skeleton-loader-container">
            {/* Searching Text with Animation */}
            <div className="skeleton-loader-thinking-text">
                <Sparkles size={20} className="skeleton-loader-thinking-icon" />
                <span className="skeleton-loader-thinking-message">
                    Searching through fashion items
                    <span className="skeleton-loader-dots">
                        <span className="skeleton-loader-dot">.</span>
                        <span className="skeleton-loader-dot">.</span>
                        <span className="skeleton-loader-dot">.</span>
                    </span>
                </span>
            </div>

            {/* Skeleton Cards Grid */}
            <div className="skeleton-loader-grid">
                {[...Array(12)].map((_, i) => (
                    <div key={i} className="skeleton-loader-card">
                        <div className="skeleton-loader-image" />
                        <div className="skeleton-loader-content">
                            <div className="skeleton-loader-line" />
                            <div className="skeleton-loader-line skeleton-loader-line-medium" />
                            <div className="skeleton-loader-line skeleton-loader-line-short" />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
