/* ai-widget.js - Universal AI Assistant Floating Widget for Marsa Maroc */

(function () {
    // 1. Create and inject CSS Styles for the Widget
    const style = document.createElement('style');
    style.innerHTML = `
        .ai-widget-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
            font-family: 'Outfit', sans-serif;
        }
        
        .ai-widget-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            border: 2px solid #334155;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            cursor: pointer;
            box-shadow: 0 8px 32px rgba(2, 132, 199, 0.4);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            outline: none;
        }
        
        .ai-widget-btn:hover {
            transform: scale(1.1) rotate(15deg);
            box-shadow: 0 12px 40px rgba(56, 189, 248, 0.6);
        }
        
        .ai-widget-btn i {
            display: flex;
        }

        .ai-chat-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 380px;
            height: 500px;
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 20px;
            box-shadow: 0 12px 48px rgba(15, 23, 42, 0.7);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            opacity: 0;
            transform: scale(0.9) translateY(20px);
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .ai-chat-window.active {
            opacity: 1;
            transform: scale(1) translateY(0);
            pointer-events: all;
        }
        
        .ai-chat-header {
            padding: 16px 20px;
            background-color: #0b0f19;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .ai-chat-header-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .ai-chat-header-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        
        .ai-chat-header-title {
            display: flex;
            flex-direction: column;
        }
        
        .ai-chat-header-title h4 {
            font-size: 0.95rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0;
        }
        
        .ai-chat-header-title span {
            font-size: 0.75rem;
            color: #10b981;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .ai-chat-header-title span::before {
            content: '';
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: #10b981;
            display: inline-block;
        }
        
        .ai-chat-close {
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 20px;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .ai-chat-close:hover {
            color: #f8fafc;
        }
        
        .ai-chat-messages {
            flex-grow: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .ai-msg {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 14px;
            font-size: 0.9rem;
            line-height: 1.4;
        }
        
        .ai-msg-received {
            background-color: #0b0f19;
            color: #f8fafc;
            align-self: flex-start;
            border-bottom-left-radius: 2px;
            border: 1px solid #334155;
        }
        
        .ai-msg-sent {
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: #ffffff;
            align-self: flex-end;
            border-bottom-right-radius: 2px;
        }
        
        .ai-chat-input-area {
            padding: 16px;
            border-top: 1px solid #334155;
            background-color: #0b0f19;
            display: flex;
            gap: 10px;
        }
        
        .ai-chat-input {
            flex-grow: 1;
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            color: #f8fafc;
            padding: 10px 14px;
            font-family: inherit;
            font-size: 0.9rem;
            outline: none;
        }
        
        .ai-chat-input:focus {
            border-color: #38bdf8;
        }
        
        .ai-chat-send {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background-color: #0284c7;
            color: white;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .ai-chat-send:hover {
            background-color: #0369a1;
        }
        
        /* Typing Indicator CSS */
        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
        }
        
        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: #94a3b8;
            animation: typingBounce 1.4s infinite ease-in-out both;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typingBounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        /* Strong tag formatting in AI messages */
        .ai-msg strong {
            color: #38bdf8;
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);

    // 2. Build HTML Structure
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'ai-widget-container';
    widgetContainer.id = 'aiWidgetContainer';

    widgetContainer.innerHTML = `
        <button class="ai-widget-btn" id="aiWidgetBtn" aria-label="Ouvrir l'assistant IA">
            <i class="bi bi-robot"></i>
        </button>
        <div class="ai-chat-window" id="aiChatWindow">
            <div class="ai-chat-header">
                <div class="ai-chat-header-info">
                    <div class="ai-chat-header-avatar">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="ai-chat-header-title">
                        <h4>Assistant Marsa Maroc</h4>
                        <span>En ligne</span>
                    </div>
                </div>
                <button class="ai-chat-close" id="aiChatClose" aria-label="Fermer">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
            <div class="ai-chat-messages" id="aiChatMessages">
                <!-- Welcome Message will be inserted here -->
            </div>
            <div class="ai-chat-input-area">
                <input type="text" class="ai-chat-input" id="aiChatInput" placeholder="Posez une question sur le port..." autocomplete="off">
                <button class="ai-chat-send" id="aiChatSend">
                    <i class="bi bi-send-fill"></i>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(widgetContainer);

    // 3. Define Selectors & Logic
    const widgetBtn = document.getElementById('aiWidgetBtn');
    const chatWindow = document.getElementById('aiChatWindow');
    const chatClose = document.getElementById('aiChatClose');
    const chatMessages = document.getElementById('aiChatMessages');
    const chatInput = document.getElementById('aiChatInput');
    const chatSend = document.getElementById('aiChatSend');

    let initialized = false;

    // Toggle Chat Window
    widgetBtn.addEventListener('click', toggleChat);
    chatClose.addEventListener('click', toggleChat);

    function toggleChat() {
        chatWindow.classList.toggle('active');
        if (chatWindow.classList.contains('active') && !initialized) {
            sendWelcomeMessage();
            initialized = true;
        }
        if (chatWindow.classList.contains('active')) {
            chatInput.focus();
        }
    }

    // Send Welcome Message
    function sendWelcomeMessage() {
        appendMessage(
            "Bonjour ! Je suis l'assistant IA intelligent de **Marsa Maroc**.<br><br>" +
            "Je peux répondre à vos questions concernant :<br>" +
            "• Le **taux d'overstay** des conteneurs.<br>" +
            "• La **capacité du quai** et les places libres.<br>" +
            "• Les **tarifs et pénalités** de stockage.<br>" +
            "• Le **planning des navires** et des escales.",
            'received'
        );
    }

    // Input handlers
    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    });

    chatSend.addEventListener('click', handleSendMessage);

    function handleSendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Append User Message
        appendMessage(text, 'sent');
        chatInput.value = '';

        // Show typing indicator
        const typingId = appendTypingIndicator();

        const role = localStorage.getItem('user_role');
        const company = localStorage.getItem('user_company');

        const requestPayload = { message: text };
        if (role) requestPayload.role = role;
        if (company) requestPayload.company = company;

        // Send to FastAPI Backend API
        fetch('/api/ia/assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload),
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            removeTypingIndicator(typingId);
            // Append AI response
            appendMessage(formatResponse(data.response), 'received');
        })
        .catch(error => {
            console.error('Error fetching AI assistant response:', error);
            removeTypingIndicator(typingId);
            appendMessage("Désolé, une erreur est survenue lors de la communication avec le serveur IA.", 'received');
        });
    }

    // Helper to format response markdown-like tags to HTML
    function formatResponse(text) {
        // Replace **bold** with <strong>bold</strong>
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace newlines with <br>
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }

    // Append Message to list
    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-msg ai-msg-${sender === 'sent' ? 'sent' : 'received'}`;
        msgDiv.innerHTML = text;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    // Append Typing Indicator
    function appendTypingIndicator() {
        const indicatorId = 'typing-' + Date.now();
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'ai-msg ai-msg-received';
        indicatorDiv.id = indicatorId;
        indicatorDiv.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(indicatorDiv);
        scrollToBottom();
        return indicatorId;
    }

    // Remove Typing Indicator
    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
        }
    }

    // Scroll to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

})();
