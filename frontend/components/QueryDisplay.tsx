import "@/styles/components/QueryDisplay.css";

interface QueryDisplayProps {
    query: string;
    isThinking: boolean;
    imagePreview?: string | null;
}

export function QueryDisplay({ query, isThinking, imagePreview }: QueryDisplayProps) {
    return (
        <div className="query-display-section">
            {/* Current Query */}
            <div className="query-display-current-query">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {imagePreview && (
                        <img
                            src={imagePreview}
                            alt="Search"
                            style={{
                                width: '40px',
                                height: '40px',
                                objectFit: 'cover',
                                borderRadius: '8px',
                                border: '1px solid rgba(var(--color-primary), 0.3)'
                            }}
                        />
                    )}
                    <span className="query-display-text">{query}</span>
                </div>
            </div>
        </div>
    );
}
