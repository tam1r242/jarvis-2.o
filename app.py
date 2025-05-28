from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

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
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "You are a helpful voice assistant named Jarvis."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Sorry, I couldn't get a response from Groq."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
