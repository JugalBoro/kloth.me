"use client";

import { useState, useRef, useEffect, FormEvent, ChangeEvent } from "react";
import { ProductCard } from "@/components/ProductCard";
import { SkeletonLoader } from "@/components/SkeletonLoader";
import { QueryDisplay } from "@/components/QueryDisplay";
import { sendChatMessage } from "@/lib/api";
import { ChatMessage as ChatMessageType, ProductResult, DebugInfo } from "@/lib/types";
import { Send, Image as ImageIcon, Shirt, ShoppingBag, Search, Sparkles, Sun, Plus } from "lucide-react";
import "@/styles/components/Page.css";

// Type for search history
interface SearchHistoryItem {
    query: string;
    results: ProductResult[];
    summary?: string;
    imagePreview?: string | null;
}

export default function Home() {
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [inputMessage, setInputMessage] = useState("");
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([]);
    const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [currentQuery, setCurrentQuery] = useState<string>("");
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Ref for skeleton loader to scroll to
    const skeletonRef = useRef<HTMLDivElement>(null);

    // Ref for latest results section to scroll to after loading
    const latestResultsRef = useRef<HTMLDivElement>(null);

    // Track currently expanded product to enforce single expansion
    const [expandedProductId, setExpandedProductId] = useState<string | null>(null);

    // Auto-scroll to skeleton when loading starts (for follow-up searches)
    useEffect(() => {
        if (isLoading && skeletonRef.current && searchHistory.length > 0) {
            setTimeout(() => {
                skeletonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 100);
        }
    }, [isLoading, searchHistory.length]);

    // Auto-scroll to latest results when new results are added
    useEffect(() => {
        if (!isLoading && searchHistory.length > 0 && latestResultsRef.current) {
            setTimeout(() => {
                latestResultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 300);
        }
    }, [searchHistory.length, isLoading]);

    const handleImageSelect = (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedImage(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setImagePreview(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        setSearchHistory([]);
        setInputMessage("");
        setSelectedImage(null);
        setImagePreview(null);
        setExpandedProductId(null);
        setDebugInfo(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!inputMessage.trim() && !selectedImage) return;

        setIsLoading(true);
        // Set the current query for display (or use placeholder for image-only)
        setCurrentQuery(inputMessage || "Image search");

        // Add user message
        const userMessage: ChatMessageType = {
            role: "user",
            content: inputMessage,
            imageUrl: imagePreview || undefined,
            image: undefined
        };
        setMessages((prev) => [...prev, userMessage]);

        try {
            // Smart Logic: If Image Only (no text), treat as fresh query (ignore history)
            // This prevents "red dress" history from polluting a "blue jeans" image search
            const isImageOnly = (selectedImage && !inputMessage.trim());
            const historyToSend = isImageOnly ? [] : messages;

            // Send to API
            const response = await sendChatMessage(inputMessage, selectedImage || undefined, historyToSend);

            // Add assistant message
            const assistantMessage: ChatMessageType = {
                role: "assistant",
                content: response.assistant_message,
                image: undefined
            };
            setMessages((prev) => [...prev, assistantMessage]);

            // Add to search history (query + results pair)
            setSearchHistory((prev) => [...prev, {
                query: inputMessage,
                results: response.results,
                summary: response.assistant_message,
                imagePreview: imagePreview // Save the image used for this search
            }]);
            setCurrentQuery("");  // Clear current query after results added

            // Update debug info
            if (response.debug) {
                setDebugInfo(response.debug);
            }
        } catch (error) {
            console.error("Error:", error);
            const errorMessage: ChatMessageType = {
                role: "assistant",
                content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : "Unknown error"}. Please try again.`,
                image: undefined
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
            setInputMessage("");
            setSelectedImage(null);
            setImagePreview(null);
        }
    };

    const handleChipClick = (query: string) => {
        setInputMessage(query);
    };

    const showEmptyState = messages.length === 0 && searchHistory.length === 0;

    return (
        <div className="home-page-container">
            {showEmptyState ? (
                /* Initial Empty State - Perplexity Style */
                <div className="home-page-center-content">
                    {/* Logo */}
                    <div className="home-page-logo-section">
                        <h1 className="home-page-logo">Fashion Search</h1>
                        <p className="home-page-tagline">AI-powered multimodal fashion discovery</p>
                    </div>

                    {/* Search Box */}
                    <form onSubmit={handleSubmit}>
                        <div className="home-page-search-container">
                            <div className="home-page-search-box">
                                {imagePreview && (
                                    <div className="home-page-image-preview-box">
                                        <img src={imagePreview} alt="Selected" className="home-page-image-preview" />
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setSelectedImage(null);
                                                setImagePreview(null);
                                            }}
                                            className="home-page-remove-button"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                )}

                                <div className="home-page-input-row">
                                    <input
                                        type="text"
                                        value={inputMessage}
                                        onChange={(e) => setInputMessage(e.target.value)}
                                        placeholder="Describe what you're looking for..."
                                        className="home-page-search-input"
                                        disabled={isLoading}
                                    />

                                    <div className="home-page-icon-buttons">
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            onChange={handleImageSelect}
                                            accept="image/*"
                                            style={{ display: 'none' }}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => fileInputRef.current?.click()}
                                            className="home-page-icon-button"
                                            disabled={isLoading}
                                        >
                                            <ImageIcon size={18} />
                                        </button>

                                        <button
                                            type="submit"
                                            disabled={isLoading || (!inputMessage.trim() && !selectedImage)}
                                            className="home-page-primary-button"
                                        >
                                            {isLoading ? <Sparkles size={18} className="animate-spin" /> : <Send size={18} />}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Suggestion Chips */}
                        <div className="home-page-suggestion-chips">
                            <button
                                type="button"
                                onClick={() => handleChipClick("black midi dress for a summer wedding")}
                                className="home-page-chip"
                            >
                                <Shirt size={16} className="home-page-chip-icon" />
                                <span>Summer Dress</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => handleChipClick("yellow shirts for summer")}
                                className="home-page-chip"
                            >
                                <Sun size={16} className="home-page-chip-icon" style={{ color: "#eab308" }} />
                                <span>Yellow Summer Shirts</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => handleChipClick("vintage denim jacket")}
                                className="home-page-chip"
                            >
                                <Sparkles size={16} className="home-page-chip-icon" />
                                <span>Vintage</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => handleChipClick("professional office blazer")}
                                className="home-page-chip"
                            >
                                <Search size={16} className="home-page-chip-icon" />
                                <span>Office Wear</span>
                            </button>
                        </div>
                    </form>
                </div>
            ) : (
                /* Results View - Stacked Query-Result Pairs */
                <div className="home-page-results-layout">
                    {/* Main Content Area */}
                    <div className="home-page-main-content">

                        {/* Search History - Stacked Query → Results */}
                        {searchHistory.map((item, index) => (
                            <div key={index} className="home-page-search-section" ref={index === searchHistory.length - 1 ? latestResultsRef : null}>
                                {/* Query Box - Right Aligned */}
                                <div className="home-page-query-header-wrapper">
                                    <div className="home-page-query-box">
                                        <div className="home-page-query-content" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            {/* Show Image if available */}
                                            {item.imagePreview && (
                                                <img
                                                    src={item.imagePreview}
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

                                            {/* Show Text or Fallback */}
                                            <span className="home-page-query-text">
                                                {item.query ? item.query : (
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.8 }}>
                                                        {!item.imagePreview && <ImageIcon size={18} />}
                                                        <span>Image search</span>
                                                    </div>
                                                )}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Result Summary - Left Side, Plain Text */}
                                <div className="home-page-result-count-text">
                                    {item.summary || `We have found ${item.results.length} result${item.results.length !== 1 ? 's' : ''}`}
                                </div>

                                {/* Results Grid for this Query */}
                                <div className="home-page-products-grid">
                                    {item.results.map((product) => (
                                        <ProductCard
                                            key={product.product_id}
                                            product={product}
                                            isExpanded={expandedProductId === product.product_id}
                                            onToggle={() => setExpandedProductId(
                                                expandedProductId === product.product_id ? null : product.product_id
                                            )}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}

                        {/* Loading Skeleton - Show at bottom during follow-up searches */}
                        {isLoading && (
                            <div ref={skeletonRef}>
                                <QueryDisplay
                                    query={currentQuery}
                                    isThinking={isLoading}
                                    imagePreview={imagePreview}
                                />
                                <SkeletonLoader />
                            </div>
                        )}
                    </div>

                    {/* Sticky Search Bar at Bottom */}
                    <div className="home-page-sticky-search-bottom">
                        <div className="home-page-bottom-search-container">
                            <form onSubmit={handleSubmit} className="home-page-bottom-search-form">
                                <div className="home-page-search-box">
                                    {imagePreview && (
                                        <div className="home-page-image-preview-box">
                                            <img src={imagePreview} alt="Selected" className="home-page-image-preview" />
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setSelectedImage(null);
                                                    setImagePreview(null);
                                                }}
                                                className="home-page-remove-button"
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    )}

                                    <div className="home-page-input-row">
                                        <input
                                            type="text"
                                            value={inputMessage}
                                            onChange={(e) => setInputMessage(e.target.value)}
                                            placeholder="Ask a follow-up question..."
                                            className="home-page-search-input"
                                            disabled={isLoading}
                                        />

                                        <div className="home-page-icon-buttons">
                                            <button
                                                type="button"
                                                onClick={handleNewChat}
                                                className="home-page-new-chat-button"
                                                title="New Chat (Clear History)"
                                                disabled={isLoading}
                                            >
                                                <span>New Chat</span>
                                            </button>
                                            <input
                                                type="file"
                                                ref={fileInputRef}
                                                onChange={handleImageSelect}
                                                accept="image/*"
                                                style={{ display: 'none' }}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => fileInputRef.current?.click()}
                                                className="home-page-icon-button"
                                                disabled={isLoading}
                                            >
                                                <ImageIcon size={18} />
                                            </button>

                                            <button
                                                type="submit"
                                                disabled={isLoading || (!inputMessage.trim() && !selectedImage)}
                                                className="home-page-primary-button"
                                            >
                                                {isLoading ? <Sparkles size={18} className="animate-spin" /> : <Send size={18} />}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
