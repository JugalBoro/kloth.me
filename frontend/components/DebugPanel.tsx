import { DebugInfo } from "@/lib/types";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import "@/styles/components/DebugPanel.css";

interface DebugPanelProps {
    debug: DebugInfo;
}

export function DebugPanel({ debug }: DebugPanelProps) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="debug-panel-container">
            {/* Header */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="debug-panel-header"
            >
                <div className="debug-panel-header-left">
                    <ChevronRight
                        size={20}
                        className={`debug-panel-toggle-icon ${isOpen ? 'expanded' : ''}`}
                    />
                    <h3 className="debug-panel-title">Debug Information</h3>
                    <span className="debug-panel-badge">
                        {debug.processing_time_ms.toFixed(0)}ms
                    </span>
                </div>
            </button>

            {/* Content */}
            {isOpen && (
                <div className="debug-panel-content">
                    {/* Query Plan */}
                    {debug.query_plan && (
                        <div className="debug-panel-section">
                            <h4 className="debug-panel-section-title">
                                🎯 Query Plan
                            </h4>

                            {/* Info Grid */}
                            <div className="debug-panel-info-grid">
                                <div className="debug-panel-info-item">
                                    <div className="debug-panel-info-label">Text Weight</div>
                                    <div className="debug-panel-info-value">
                                        {(debug.query_plan.text_weight * 100).toFixed(0)}%
                                    </div>
                                </div>
                                <div className="debug-panel-info-item">
                                    <div className="debug-panel-info-label">Image Weight</div>
                                    <div className="debug-panel-info-value">
                                        {((1 - debug.query_plan.text_weight) * 100).toFixed(0)}%
                                    </div>
                                </div>
                                <div className="debug-panel-info-item">
                                    <div className="debug-panel-info-label">Top K</div>
                                    <div className="debug-panel-info-value">
                                        {debug.query_plan.top_k}
                                    </div>
                                </div>
                            </div>

                            {/* Refined Queries */}
                            {debug.query_plan.refined_queries.length > 0 && (
                                <div>
                                    <div className="debug-panel-info-label" style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>
                                        Refined Queries
                                    </div>
                                    <ul className="debug-panel-query-list">
                                        {debug.query_plan.refined_queries.map((q, i) => (
                                            <li key={i} className="debug-panel-query-item">
                                                {q}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Reasoning */}
                            {debug.query_plan.reasoning && (
                                <div style={{ marginTop: '1rem' }}>
                                    <div className="debug-panel-info-label" style={{ marginBottom: '0.5rem' }}>
                                        Reasoning
                                    </div>
                                    <p className="debug-panel-reasoning">
                                        {debug.query_plan.reasoning}
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Results Stats */}
                    <div className="debug-panel-section">
                        <h4 className="debug-panel-section-title">
                            📊 Results Statistics
                        </h4>

                        <div className="debug-panel-metric-bar">
                            <div className="debug-panel-metric-label">Text Results</div>
                            <div className="debug-panel-progress-bar">
                                <div
                                    className="debug-panel-progress-fill"
                                    style={{ width: `${(debug.text_results_count / Math.max(debug.total_unique_results, 1)) * 100}%` }}
                                />
                            </div>
                            <div className="debug-panel-metric-value">{debug.text_results_count}</div>
                        </div>

                        <div className="debug-panel-metric-bar">
                            <div className="debug-panel-metric-label">Image Results</div>
                            <div className="debug-panel-progress-bar">
                                <div
                                    className="debug-panel-progress-fill"
                                    style={{ width: `${(debug.image_results_count / Math.max(debug.total_unique_results, 1)) * 100}%` }}
                                />
                            </div>
                            <div className="debug-panel-metric-value">{debug.image_results_count}</div>
                        </div>

                        <div className="debug-panel-metric-bar">
                            <div className="debug-panel-metric-label">Total Unique</div>
                            <div className="debug-panel-progress-bar">
                                <div
                                    className="debug-panel-progress-fill"
                                    style={{ width: '100%' }}
                                />
                            </div>
                            <div className="debug-panel-metric-value">{debug.total_unique_results}</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
