from flask import Flask, render_template, request, jsonify
import os
import json
import logging
from groq import Groq

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Memory storage
memory = {
    "conversation_history": [],
    "important_memories": {
        "memory1": None,
        "memory2": None,
        "memory3": None
    }
}

def load_config():
    with open('config.json') as config_file:
        return json.load(config_file)

config = load_config()
GROQ_API_KEY = config.get("GROQ_API_KEY")

# Initialize the Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_input = data.get("message")
    if not user_input:
        return jsonify({"response": "I didn't hear anything."})

    # Store conversation history
    memory["conversation_history"].append({"user": user_input})

    # Construct the prompt with entire conversation history and important memories
    conversation_context = "\n".join(
        [f"User: {entry['user']}\nAssistant: {entry.get('assistant', '')}" for entry in memory["conversation_history"]]
    )
    
    # Include important memories in the context
    important_memories_context = "\n".join(
        [f"{key}: {value}" for key, value in memory["important_memories"].items() if value is not None]
    )
    
    prompt = f"{important_memories_context}\n{conversation_context}\nUser: {user_input}\nAssistant:"
    
    response_text = ask_groq(prompt)
    memory["conversation_history"][-1]["assistant"] = response_text  # Update the last entry with the assistant's response

    return jsonify({"response": response_text})
def ask():
    data = request.get_json()
    user_input = data.get("message")
    if not user_input:
        return jsonify({"response": "I didn't hear anything."})

    # Store conversation history
    memory["conversation_history"].append(user_input)

    # Construct the prompt with memories
    memories = " ".join([f"{key}: {value}" for key, value in memory["important_memories"].items() if value])
    prompt = f"{memories}\nUser: {user_input}\nAssistant:"
    
    response_text = ask_groq(prompt)
    memory["conversation_history"].append(response_text)

    return jsonify({"response": response_text})
def ask():
    data = request.get_json()
    user_input = data.get("message")
    if not user_input:
        return jsonify({"response": "I didn't hear anything."})

    # Store conversation history
    memory["conversation_history"].append(user_input)

    response_text = ask_groq(user_input)
    memory["conversation_history"].append(response_text)

    return jsonify({"response": response_text})

@app.route("/set_memory", methods=["POST"])
def set_memory():
    data = request.get_json()
    memory_key = data.get("key")
    memory_value = data.get("value")
    
    if memory_key in memory["important_memories"]:
        memory["important_memories"][memory_key] = memory_value
        return jsonify({"response": f"Memory '{memory_key}' set."})
    return jsonify({"response": "Invalid memory key."})

@app.route("/reset", methods=["POST"])
def reset():
    memory["conversation_history"] = []
    # memory["important_memories"] = {key: None for key in memory["important_memories"]}
    return jsonify({"response": "Memory and conversation reset."})

def ask_groq(prompt):
    try:
        chat_completion = groq_client.chat.completions.create(
            model="compound-beta",
            messages=[
                {"role": "system", "content": "You are a helpful voice assistant named Jarvis."},
                {"role": "user", "content": prompt}
            ]
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Error while calling Groq: {str(e)}")
        return f"Sorry, I couldn't get a response from Groq. Error: {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
