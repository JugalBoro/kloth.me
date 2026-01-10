import { ChatMessage as ChatMessageType } from "@/lib/types";
import "@/styles/components/ChatMessage.css";

interface ChatMessageProps {
    message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isUser = message.role === "user";

    return (
        <div className={`chat-message-container ${isUser ? 'chat-message-user' : ''}`}>
            {/* Avatar */}
            <div className={`chat-message-avatar ${isUser ? 'chat-message-user' : 'chat-message-assistant'}`}>
                {isUser ? 'U' : 'AI'}
            </div>

            {/* Message Bubble */}
            <div className={`chat-message-bubble ${isUser ? 'chat-message-user' : 'chat-message-assistant'}`}>
                <p className="chat-message-text">{message.content}</p>

                {/* Image Preview if uploaded */}
                {message.image && (
                    <div className="chat-message-image-preview">
                        <img
                            src={message.image}
                            alt="Uploaded"
                            className="chat-message-preview-image"
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
