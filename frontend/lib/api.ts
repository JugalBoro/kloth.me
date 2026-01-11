import { ChatMessage, ChatResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Send a chat message to the backend API
 */
export async function sendChatMessage(
    message: string,
    image?: File,
    history?: ChatMessage[]
): Promise<ChatResponse> {
    const formData = new FormData();

    formData.append("message", message);

    if (image) {
        formData.append("image", image);
    }

    if (history && history.length > 0) {
        formData.append("history", JSON.stringify(history));
    }

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API error: ${response.status}`);
    }

    return response.json();
}

/**
 * Health check for the API
 */
export async function checkApiHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
