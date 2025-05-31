from flask import Flask, render_template, request, jsonify
import os
import json
import logging
from groq import Groq  # Import the Groq client

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

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

    response_text = ask_groq(user_input)
    return jsonify({"response": response_text})

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
