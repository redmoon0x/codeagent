from flask import Flask, render_template, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

SYSTEM_PROMPT = """You are a website generator that creates clean, modern websites using HTML, Tailwind CSS, and JavaScript.
Always structure your response in the following format:

HTML_FILE
[Your HTML code here]
END_HTML

CSS_FILE
[Your CSS code here]
END_CSS

JS_FILE
[Your JavaScript code here]
END_JS

Do not include any explanatory text, only output the code between the markers."""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=SYSTEM_PROMPT
)

def parse_generated_code(response_text):
    files = {
        'html': '',
        'css': '',
        'js': ''
    }
    
    # Extract HTML
    if 'HTML_FILE' in response_text and 'END_HTML' in response_text:
        html_content = response_text.split('HTML_FILE')[1].split('END_HTML')[0].strip()
        files['html'] = html_content
    
    # Extract CSS
    if 'CSS_FILE' in response_text and 'END_CSS' in response_text:
        css_content = response_text.split('CSS_FILE')[1].split('END_CSS')[0].strip()
        files['css'] = css_content
    
    # Extract JavaScript
    if 'JS_FILE' in response_text and 'END_JS' in response_text:
        js_content = response_text.split('JS_FILE')[1].split('END_JS')[0].strip()
        files['js'] = js_content
    
    return files

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_website():
    try:
        data = request.json
        user_input = data.get('prompt', '')
        
        # Start chat session with Gemini
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(user_input)
        
        # Parse the generated code from response
        files = parse_generated_code(response.text)
        
        # Create combined preview HTML
        preview_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>{files['css']}</style>
</head>
<body>
{files['html']}
<script>{files['js']}</script>
</body>
</html>
"""
        
        return jsonify({
            "files": files,
            "preview_html": preview_html
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)