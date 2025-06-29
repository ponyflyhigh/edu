// static/js/chat.js
document.addEventListener("DOMContentLoaded", function () {
    const socket = io("http://localhost:5000");

    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message');
    const chatMessages = document.getElementById('chat-messages');

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        if (isUser) {
            messageDiv.innerHTML = `<span>你：</span><p>${content}</p>`;
        } else {
            messageDiv.innerHTML = `<span>LLM助手：</span><p>${content}</p>`;
        }
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            addMessage(message, true);
            socket.emit('llm-request', { message });
            messageInput.value = '';
        }
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendButton.click();
    });

    socket.on('llm-response', (data) => addMessage(data.message));
    socket.on('llm-error', (data) => addMessage(`错误: ${data.error}`));

    console.log("chat.js loaded");
});