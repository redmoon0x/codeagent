from flask import Flask, render_template, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
from pathlib import Path

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

SYSTEM_PROMPT = """You are a website generator that creates clean, modern, and highly functional multi-page websites using HTML, Tailwind CSS, and JavaScript. Your primary focus is on best coding practices, optimal user interface (UI), and user experience (UX). Generate all necessary files for a complete website structure.

For each page, provide the code in the following format:

PAGE: [page_name]
HTML_FILE
[Your HTML code here]
END_HTML

CSS_FILE
[Your CSS code here]
END_CSS

JS_FILE
[Your JavaScript code here]
END_JS
END_PAGE

Also provide any shared resources in this format:

SHARED_RESOURCE: [resource_name]
CONTENT
[Your code/content here]
END_CONTENT
END_SHARED_RESOURCE

Include all necessary navigation, common components, and ensure consistent styling across pages. Generate all required files for a complete website structure."""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=SYSTEM_PROMPT
)

def parse_generated_code(response_text):
    # Dictionary to store all pages and shared resources
    website_structure = {
        'pages': {},
        'shared_resources': {}
    }
    
    # Split into pages and shared resources
    components = response_text.split('PAGE: ')
    
    # Process each page
    for component in components[1:]:  # Skip first empty split
        # Split page name and content
        page_name, content = component.split('\n', 1)
        page_name = page_name.strip().lower()
        
        # Initialize page structure
        website_structure['pages'][page_name] = {
            'html': '',
            'css': '',
            'js': ''
        }
        
        # Extract HTML
        if 'HTML_FILE' in content and 'END_HTML' in content:
            html_content = content.split('HTML_FILE')[1].split('END_HTML')[0].strip()
            website_structure['pages'][page_name]['html'] = html_content
            
        # Extract CSS
        if 'CSS_FILE' in content and 'END_CSS' in content:
            css_content = content.split('CSS_FILE')[1].split('END_CSS')[0].strip()
            website_structure['pages'][page_name]['css'] = css_content
            
        # Extract JavaScript
        if 'JS_FILE' in content and 'END_JS' in content:
            js_content = content.split('JS_FILE')[1].split('END_JS')[0].strip()
            website_structure['pages'][page_name]['js'] = js_content
    
    # Extract shared resources
    shared_parts = response_text.split('SHARED_RESOURCE: ')
    for shared in shared_parts[1:]:  # Skip first empty split
        resource_name, content = shared.split('\n', 1)
        resource_name = resource_name.strip().lower()
        if 'CONTENT' in content and 'END_CONTENT' in content:
            resource_content = content.split('CONTENT')[1].split('END_CONTENT')[0].strip()
            website_structure['shared_resources'][resource_name] = resource_content
    
    return website_structure

def generate_preview_html(page_data, shared_resources):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            {page_data['css']}
            {shared_resources.get('common_styles', '')}
        </style>
    </head>
    <body>
        {page_data['html']}
        {shared_resources.get('common_components', '')}
        <script>
            {shared_resources.get('common_scripts', '')}
            {page_data['js']}
        </script>
    </body>
    </html>
    """

def save_generated_files(website_structure, output_dir):
    base_dir = Path(output_dir)
    
    # Create directory structure
    base_dir.mkdir(exist_ok=True)
    (base_dir / 'css').mkdir(exist_ok=True)
    (base_dir / 'js').mkdir(exist_ok=True)
    (base_dir / 'shared').mkdir(exist_ok=True)
    
    # Save pages
    for page_name, page_data in website_structure['pages'].items():
        # Save HTML
        with open(base_dir / f'{page_name}.html', 'w') as f:
            f.write(generate_preview_html(page_data, website_structure['shared_resources']))
        
        # Save CSS
        if page_data['css']:
            with open(base_dir / 'css' / f'{page_name}.css', 'w') as f:
                f.write(page_data['css'])
        
        # Save JavaScript
        if page_data['js']:
            with open(base_dir / 'js' / f'{page_name}.js', 'w') as f:
                f.write(page_data['js'])
    
    # Save shared resources
    for resource_name, content in website_structure['shared_resources'].items():
        with open(base_dir / 'shared' / f'{resource_name}.txt', 'w') as f:
            f.write(content)

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
        website_structure = parse_generated_code(response.text)
        
        # Create output directory for generated files
        output_dir = 'generated_website'
        save_generated_files(website_structure, output_dir)
        
        # Generate previews for all pages
        previews = {}
        for page_name, page_data in website_structure['pages'].items():
            previews[page_name] = generate_preview_html(
                page_data, 
                website_structure['shared_resources']
            )
        
        return jsonify({
            "website_structure": website_structure,
            "previews": previews,
            "output_directory": output_dir
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)