function handleUserInput() {
    const userInput = document.getElementById("userInput");
    const message = userInput.value;
    if (!message) return;
    const chatbox = document.getElementById("chatbox");
    chatbox.innerHTML += `<div><b>You:</b> ${message}</div>`;
    userInput.value = "";
    
    fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
    })
    .then((res) => res.json())
    .then((data) => {
        chatbox.innerHTML += `<div><b>Jarvis:</b> ${data.response}</div>`;
        if (message.startsWith("remember: ")) {
            chatbox.innerHTML += `<div><b>System:</b> Memory stored: ${message.slice(9).trim('"')}</div>`;
        }
        chatbox.scrollTop = chatbox.scrollHeight;
    });
}

function resetMemory() {
    fetch("/reset", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    })
    .then((res) => res.json())
    .then((data) => {
        const chatbox = document.getElementById("chatbox");
        chatbox.innerHTML += `<div><b>System:</b> ${data.response}</div>`;
        chatbox.scrollTop = chatbox.scrollHeight;
    });
}

// Add event listeners
document.getElementById('userInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        handleUserInput();
    }
});

document.getElementById('resetButton').addEventListener('click', function() {
    document.getElementById('chatbox').innerHTML = ''; // Clear the chatbox
    resetMemory(); // Also reset the backend memory
});
