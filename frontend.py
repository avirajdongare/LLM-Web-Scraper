from flask import Flask, request, render_template
import asyncio
from scraperai import scrape_url, extract_text_by_query, smart_extract
#flask
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        url = request.form.get("url")
        tool = request.form.get("tool")
        instruction = request.form.get("instruction", "")
        query = request.form.get("query", "")

        try:
            if tool == "scrape":
                result = asyncio.run(scrape_url(url))
            elif tool == "query":
                result = asyncio.run(extract_text_by_query(url, query))
            elif tool == "smart":
                result = asyncio.run(smart_extract(url, instruction))
            else:
                result = "Invalid tool selected."
        except Exception as e:
            result = f"[ERROR] {str(e)}"

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
