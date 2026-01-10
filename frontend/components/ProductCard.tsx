import { useState } from "react";
import { ProductResult } from "@/lib/types";

import "@/styles/components/ProductCard.css";

interface ProductCardProps {
    product: ProductResult;
    isExpanded: boolean;
    onToggle: () => void;
}

export function ProductCard({ product, isExpanded, onToggle }: ProductCardProps) {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const scorePercentage = Math.round(product.score * 100);

    // Extract meaningful category details
    const getCategories = () => {
        if (!product.categories) return [];

        // Try standard e-commerce keys
        const parts = [];
        if (product.categories.gender) parts.push(product.categories.gender);
        if (product.categories.subCategory) parts.push(product.categories.subCategory);
        if (product.categories.articleType) parts.push(product.categories.articleType);

        // Fallback to numbered categories (Fashion200k style)
        if (parts.length === 0) {
            if (product.categories.category1) parts.push(product.categories.category1);
            if (product.categories.category2) parts.push(product.categories.category2);
            if (product.categories.category3) parts.push(product.categories.category3);
        }

        // Fallback to simple category
        if (parts.length === 0 && product.categories.category) {
            parts.push(product.categories.category);
        }

        // De-duplicate and filter
        const uniqueParts = Array.from(new Set(parts.map(p => p.trim()).filter(Boolean)));

        // Return all items, filtering happens in render
        return uniqueParts;
    };

    const categories = getCategories();
    // Show top 3 or all depending on state
    const visibleCategories = isExpanded ? categories : categories.slice(0, 3);
    const hiddenCount = categories.length - 3;

    return (
        <div className={`product-card-container ${isExpanded ? 'expanded-container' : ''}`}>
            <div
                className={`product-card ${isExpanded ? 'expanded' : ''}`}
                onClick={onToggle}
            >
                {/* Image */}
                <div className="product-card-image-container">
                    <img
                        src={`${API_BASE_URL}/images/${product.image_path.split('/').pop()}`}
                        alt={product.description}
                        className="product-card-image"
                    />

                    {/* Score Badge */}
                    <div className="product-card-score-badge">
                        <div className="product-card-score-indicator" />
                        <span className="product-card-score-text">Matching Score {scorePercentage}%</span>
                    </div>
                </div>

                {/* Content */}
                <div className="product-card-content">
                    {/* Description */}
                    <p className="product-card-description">
                        {product.description}
                    </p>

                    {/* Category Chips */}
                    {categories.length > 0 && (
                        <div className="product-card-chip-container">
                            {visibleCategories.map((cat, index) => (
                                <span key={index} className="product-card-chip">
                                    {cat}
                                </span>
                            ))}
                            {/* Show +N badge if collapsed and hidden items exist */}
                            {!isExpanded && hiddenCount > 0 && (
                                <span className="product-card-chip more-chip">
                                    +{hiddenCount}
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
