"""
Flask UI for VeriRAG Healthcare.

Run:
    python app.py
Then open:
    http://localhost:5000
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request

from llm.verirag_healthcare import run_query
import config

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    query = ""
    error = None

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            error = "Please enter a question."
        else:
            try:
                response = run_query(query)
            except Exception as exc:
                error = (f"VeriRAG pipeline error: {exc}. Check that Ganache, the "
                         f"deployed contracts, the Chroma DB, and Ollama are all "
                         f"running/built (see README).")

    return render_template("index.html", query=query, response=response, error=error)


if __name__ == "__main__":
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
