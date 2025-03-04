// API endpoints
const API_URL = 'http://localhost:5000/api';

// Basic event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log("Script loaded successfully!");
    
    // Get DOM elements
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const profileButton = document.getElementById('profile-btn');
    const authModal = document.getElementById('auth-modal');
    const closeModalButton = document.querySelector('.close');
    
    // Debug which elements are found
    console.log("chatContainer found:", !!chatContainer);
    console.log("userInput found:", !!userInput);
    console.log("sendButton found:", !!sendButton);
    
    // Simple message sending
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            if (userInput && userInput.value.trim()) {
                sendMessage();
            }
        });
    }
    
    // Handle Enter key in input
    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Handle profile button
    if (profileButton) {
        profileButton.addEventListener('click', function() {
            if (authModal) authModal.style.display = 'block';
        });
    }
    
    // Close modal
    if (closeModalButton) {
        closeModalButton.addEventListener('click', function() {
            if (authModal) authModal.style.display = 'none';
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === authModal) {
            authModal.style.display = 'none';
        }
    });
});

// Send a message function
function sendMessage() {
    const userInput = document.getElementById('user-input');
    if (!userInput || !userInput.value.trim()) return;
    
    // Get the message
    const message = userInput.value.trim();
    
    // Add user message to UI
    addMessage('You', message, true);
    
    // Clear input
    userInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to server
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator();
        
        // Display AI response
        if (data.error) {
            console.error("Error:", data.error);
            addMessage('StudyAI', 'Sorry, there was an error. Please try again.', false);
        } else {
            addMessage('StudyAI', data.content, false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessage('StudyAI', 'Sorry, there was an error. Please try again.', false);
    });
}

// Add message to chat
function addMessage(sender, text, isUser) {
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(isUser ? 'user-message' : 'ai-message');
    
    const now = new Date();
    const timeString = now.getHours() + ':' + now.getMinutes().toString().padStart(2, '0');
    
    messageElement.innerHTML = `
        <div class="message-content">
            <div class="sender">${sender}</div>
            <div class="text">${text}</div>
        </div>
        <div class="timestamp">${timeString}</div>
    `;
    
    chatContainer.appendChild(messageElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;
    
    const typingElement = document.createElement('div');
    typingElement.classList.add('message', 'ai-message', 'typing-indicator');
    typingElement.innerHTML = `
        <div class="message-content">
            <div class="sender">StudyAI</div>
            <div class="text">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(typingElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Add CSS for typing indicator
const style = document.createElement('style');
style.textContent = `
    .typing-indicator .text {
        display: flex;
        gap: 4px;
    }
    
    .typing-indicator .dot {
        height: 8px;
        width: 8px;
        background-color: #adb5bd;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 1.4s infinite ease-in-out;
    }
    
    .typing-indicator .dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-indicator .dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes pulse {
        0%, 60%, 100% { transform: scale(1); opacity: 1; }
        30% { transform: scale(1.2); opacity: 0.8; }
    }
`;
document.head.appendChild(style);