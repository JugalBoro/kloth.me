export interface ChatMessage {
    image: any;
    role: "user" | "assistant";
    content: string;
    imageUrl?: string;
}

export interface ProductResult {
    product_id: string;
    description: string;
    image_path: string;
    score: number;
    categories?: Record<string, string>;
}

export interface QueryPlan {
    refined_queries: string[];
    use_image: boolean;
    text_weight: number;
    top_k: number;
    reasoning?: string;
}

export interface DebugInfo {
    query_plan?: QueryPlan;
    text_results_count: number;
    image_results_count: number;
    total_unique_results: number;
    processing_time_ms: number;
}

export interface ChatResponse {
    assistant_message: string;
    results: ProductResult[];
    debug?: DebugInfo;
}
