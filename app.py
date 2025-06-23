from flask import Flask, render_template, request, jsonify
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from queue import Queue
from threading import Lock
from groq import Groq
from src.config import config

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MemoryManager:
    MAX_HISTORY_SIZE = 50  # Limit conversation history
    MAX_MEMORY_AGE = 3600  # Clear memories older than 1 hour

    def __init__(self):
        self.lock = Lock()
        self.conversation_history: List[Dict[str, str]] = []
        self.important_memories: Dict[str, Dict[str, Any]] = {
            f"memory{i}": {"value": None, "timestamp": None} 
            for i in range(1, 4)
        }

    def add_to_history(self, entry: Dict[str, str]) -> None:
        """Add entry to conversation history with size limit."""
        with self.lock:
            if len(self.conversation_history) >= self.MAX_HISTORY_SIZE:
                self.conversation_history.pop(0)
            self.conversation_history.append(entry)

    def store_memory(self, value: str) -> Optional[str]:
        """Store a memory in the first available slot."""
        current_time = time.time()
        with self.lock:
            # Clear old memories
            for key, data in self.important_memories.items():
                if data["timestamp"] and current_time - data["timestamp"] > self.MAX_MEMORY_AGE:
                    data["value"] = None
                    data["timestamp"] = None

            # Find first empty slot
            for key, data in self.important_memories.items():
                if data["value"] is None:
                    data["value"] = value
                    data["timestamp"] = current_time
                    return key
        return None

    def get_memories(self) -> List[str]:
        """Get all active memories."""
        current_time = time.time()
        with self.lock:
            return [
                data["value"] for data in self.important_memories.values()
                if data["value"] and data["timestamp"] 
                and current_time - data["timestamp"] <= self.MAX_MEMORY_AGE
            ]

    def clear_history(self) -> None:
        """Clear conversation history."""
        with self.lock:
            self.conversation_history.clear()

# Initialize memory manager
memory_manager = MemoryManager()

# Initialize Groq client with retry mechanism
class GroqClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def __init__(self):
        groq_config = config.get('groq')
        self.api_key = groq_config['api_key']
        self.client = Groq(api_key=self.api_key)
        self.lock = Lock()
        
    def create_chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Create chat completion with retry logic."""
        with self.lock:
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model="compound-beta",
                        messages=messages
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    if attempt == self.MAX_RETRIES - 1:
                        logger.error(f"Failed to get Groq response after {self.MAX_RETRIES} attempts: {str(e)}")
                        raise
                    time.sleep(self.RETRY_DELAY)

# Initialize Groq client
groq_client = GroqClient()

@app.route("/")
def index() -> str:
    """Render the main page."""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return "Error loading page", 500

@app.route("/ask", methods=["POST"])
def ask() -> tuple[Any, int]:
    """Handle user questions and generate responses."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_input = data.get("message", "").strip()
        if not user_input:
            return jsonify({"response": "I didn't hear anything."}), 400

        # Handle memory storage requests
        if user_input.lower().startswith("remember: "):
            memory_string = user_input[9:].strip('"')
            if memory_key := memory_manager.store_memory(memory_string):
                return jsonify({"response": f"I'll remember that in {memory_key}."}), 200
            return jsonify({"response": "Sorry, my memory is full right now."}), 200

        # Create conversation entry
        conversation_entry = {"user": user_input}
        memory_manager.add_to_history(conversation_entry)

        try:
            # Construct the prompt
            active_memories = memory_manager.get_memories()
            memories_context = "\n".join(f"Memory: {mem}" for mem in active_memories) if active_memories else ""
            
            conversation_context = "\n".join(
                f"User: {entry['user']}\nAssistant: {entry.get('assistant', '')}"
                for entry in memory_manager.conversation_history[-5:]  # Only use last 5 exchanges for context
            )
            
            prompt = f"{memories_context}\n{conversation_context}\nUser: {user_input}\nAssistant:"
            
            # Get response from Groq
            messages = [
                {
                    "role": "system", 
                    "content": "You are a helpful voice assistant named Jarvis. Your responses should NEVER include any references to previous conversations or questions, even if they are provided in the context. Focus solely on answering the current question directly."
                },
                {"role": "user", "content": prompt}
            ]
            
            response_text = groq_client.create_chat_completion(messages)
            
            # Update conversation history with response
            conversation_entry["assistant"] = response_text
            return jsonify({"response": response_text}), 200
            
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return jsonify({"error": "Failed to get AI response"}), 500

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/set_memory", methods=["POST"])
def set_memory() -> tuple[Any, int]:
    """Set a specific memory slot."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        memory_key = data.get("key")
        memory_value = data.get("value")
        
        if not memory_key or not memory_value:
            return jsonify({"error": "Missing key or value"}), 400
            
        if memory_key in memory_manager.important_memories:
            memory_manager.important_memories[memory_key]["value"] = memory_value
            memory_manager.important_memories[memory_key]["timestamp"] = time.time()
            return jsonify({"response": f"Memory '{memory_key}' set."}), 200
            
        return jsonify({"response": "Invalid memory key."}), 400
        
    except Exception as e:
        logger.error(f"Error setting memory: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/reset", methods=["POST"])
def reset() -> tuple[Any, int]:
    """Reset conversation history."""
    try:
        memory_manager.clear_history()
        return jsonify({"response": "Conversation history reset."}), 200
    except Exception as e:
        logger.error(f"Error resetting memory: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_error(error: Exception) -> tuple[Any, int]:
    """Global error handler."""
    logger.error(f"Unhandled error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Get web config
    web_config = config.get('web')
    
    # Run with error handling
    try:
        app.run(
            host=web_config['host'],
            port=web_config['port'],
            debug=False  # Disable debug mode in production
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        sys.exit(1)
