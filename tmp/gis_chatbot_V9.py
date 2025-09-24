from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import requests
import re
import os
import webbrowser
from dotenv import load_dotenv
from typing import Dict, List, Union, Optional
import json
import datetime

# Load environment variables from .env file
load_dotenv()

# Set up Google API Key (DO NOT MODIFY)
API_KEY = "Key"

# Debugging: Ensure API key is correctly retrieved
if not API_KEY:
    print("ERROR: GOOGLE_API_KEY is missing. Set it as an environment variable or in a .env file.")
    raise ValueError("Google API key is missing.")
else:
    print(f"DEBUG: Google API Key loaded successfully: {API_KEY[:5]}******")

# Configure Google Generative AI
genai.configure(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash-002"

app = Flask(__name__)
CORS(app)

class GISDataAnalyzer:
    def __init__(self):
        self.cached_metadata = {}

    def get_service_info(self, url: str) -> Dict:
        """Fetch and analyze service-level metadata."""
        try:
            response = requests.get(f"{url}?f=json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch service info: {str(e)}"}

    def analyze_layer_schema(self, layer_url: str) -> Dict:
        """Analyze the schema of a specific layer."""
        try:
            response = requests.get(f"{layer_url}?f=json")
            response.raise_for_status()
            data = response.json()
            
            fields = data.get("fields", [])
            field_info = {
                field["name"]: {
                    "type": field["type"],
                    "alias": field.get("alias", field["name"]),
                    "domain": field.get("domain")
                } for field in fields
            }
            
            return {
                "name": data.get("name", "Unknown Layer"),
                "description": data.get("description", "No description available"),
                "geometryType": data.get("geometryType", "Unknown"),
                "fields": field_info,
                "capabilities": data.get("capabilities", [])
            }
        except Exception as e:
            return {"error": f"Failed to analyze layer schema: {str(e)}"}

    def query_layer_statistics(self, layer_url: str, field_name: str) -> Dict:
        """Get statistical information about a specific field."""
        params = {
            "f": "json",
            "statisticType": "min,max,avg,stddev,count",
            "onStatisticField": field_name,
            "outStatistics": json.dumps([
                {"statisticType": "min", "onStatisticField": field_name, "outStatisticFieldName": "min_value"},
                {"statisticType": "max", "onStatisticField": field_name, "outStatisticFieldName": "max_value"},
                {"statisticType": "avg", "onStatisticField": field_name, "outStatisticFieldName": "avg_value"},
                {"statisticType": "stddev", "onStatisticField": field_name, "outStatisticFieldName": "stddev_value"},
                {"statisticType": "count", "onStatisticField": field_name, "outStatisticFieldName": "count_value"}
            ])
        }
        
        try:
            response = requests.get(f"{layer_url}/query", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}

    def get_layer_sample_data(self, layer_url: str, limit: int = 5) -> Dict:
        """Fetch a sample of records from the layer."""
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": limit,
            "f": "json"
        }
        
        try:
            response = requests.get(f"{layer_url}/query", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to get sample data: {str(e)}"}

def extract_url(text: str) -> Optional[str]:
    """Extracts the first URL from the input text."""
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def generate_map(gis_url: str):
    """Creates an enhanced HTML file with an embedded map, metadata display, and query interface."""
    map_viewer_url = f"https://www.arcgis.com/apps/mapviewer/index.html?url={gis_url}&source=sd"
    
    # Fetch metadata for the service
    analyzer = GISDataAnalyzer()
    service_info = analyzer.get_service_info(gis_url)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xentity GIS Data Explorer</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #1a1a1a;
                color: #00ffff;
            }}
            .container {{
                display: grid;
                grid-template-columns: 300px 1fr;
                height: 100vh;
            }}
            .sidebar {{
                background-color: #2a2a2a;
                padding: 20px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }}
            .main-content {{
                padding: 20px;
                display: flex;
                flex-direction: column;
            }}
            .header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }}
            #logo {{
                height: 40px;
            }}
            .map-container {{
                flex-grow: 1;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
            .metadata {{
                margin-top: 20px;
                flex-grow: 1;
                overflow-y: auto;
            }}
            .metadata h3 {{
                color: #00cccc;
            }}
            .metadata-item {{
                margin: 10px 0;
                padding: 10px;
                background-color: #333;
                border-radius: 5px;
            }}
            .query-interface {{
                background-color: #333;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .query-box {{
                width: 100%;
                padding: 10px;
                margin-bottom: 10px;
                background-color: #1a1a1a;
                border: 1px solid #00ffff;
                border-radius: 4px;
                color: #00ffff;
                resize: vertical;
                min-height: 60px;
            }}
            .query-button {{
                background-color: #00cccc;
                color: #1a1a1a;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
            }}
            .query-button:hover {{
                background-color: #00ffff;
            }}
            .response-area {{
                margin-top: 15px;
                padding: 15px;
                background-color: #1a1a1a;
                border-radius: 4px;
                min-height: 100px;
                max-height: 200px;
                overflow-y: auto;
                display: none;
            }}
            #suggestions {{
                margin-top: 10px;
                font-size: 0.9em;
            }}
            .suggestion {{
                cursor: pointer;
                padding: 5px;
                margin: 2px 0;
                color: #00cccc;
            }}
            .suggestion:hover {{
                color: #00ffff;
                text-decoration: underline;
            }}
        </style>
        <script>
            async function submitQuery() {{
                const queryText = document.getElementById('queryInput').value;
                const responseArea = document.getElementById('responseArea');
                const gisUrl = "{gis_url}";
                
                if (!queryText.trim()) return;
                
                responseArea.style.display = 'block';
                responseArea.innerHTML = 'Processing query...';
                
                try {{
                    const response = await fetch('http:/192.168.1.2:5000/chat', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            query: queryText,
                            url: gisUrl
                        }})
                    }});
                    
                    const data = await response.json();
                    
                    let responseHtml = '<strong>Response:</strong><br>';
                    if (data.answer) {{
                        responseHtml += data.answer + '<br><br>';
                    }}
                    if (data.ai_interpretation) {{
                        responseHtml += '<strong>AI Interpretation:</strong><br>' + data.ai_interpretation;
                    }}
                    
                    responseArea.innerHTML = responseHtml;
                }} catch (error) {{
                    responseArea.innerHTML = `Error: ${{error.message}}`;
                }}
            }}

            function useExample(text) {{
                document.getElementById('queryInput').value = text;
                submitQuery();
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="sidebar">
                <div class="header">
                    <img id="logo" src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiRjRWWhjqWGw2jaHGQjUi9WQy03xo2TALpV26EyhnpNqr95Ze9Di1sLKVK_GqddpNnu_5HywtdmmYQ6WCfyXPnCL42pNcBtMotfOqvg3uGno2A2cyJ8C44ICHGHEcYiRVfv6YuuQVETbo1HPJ2pWW3PF-ZsDKdOPolRPD9MfvGDyIYFJ8tRkOHlxz-JTbt/s320/Xentity-Logo.png" alt="Xentity Logo">
                </div>
                
                <div class="query-interface">
                    <h3>Ask About This GIS Data</h3>
                    <textarea id="queryInput" class="query-box" 
                        placeholder="Ask a question about this GIS data..."></textarea>
                    <button onclick="submitQuery()" class="query-button">Submit Query</button>
                    <div id="suggestions">
                        <p><strong>Try these examples:</strong></p>
                        <div class="suggestion" onclick="useExample('What fields are available in this dataset?')">
                            • What fields are available in this dataset?
                        </div>
                        <div class="suggestion" onclick="useExample('Show me some statistical summaries of the numeric fields.')">
                            • Show me statistical summaries of the numeric fields.
                        </div>
                        <div class="suggestion" onclick="useExample('Can you give me a sample of 5 records?')">
                            • Can you give me a sample of 5 records?
                        </div>
                    </div>
                    <div id="responseArea" class="response-area"></div>
                </div>

                <div class="metadata">
                    <h3>Service Information</h3>
                    <div class="metadata-item">
                        <strong>Name:</strong> {service_info.get('serviceName', 'N/A')}<br>
                        <strong>Type:</strong> {service_info.get('type', 'N/A')}<br>
                        <strong>Version:</strong> {service_info.get('currentVersion', 'N/A')}
                    </div>
                    <div class="metadata-item">
                        <strong>Description:</strong><br>
                        {service_info.get('description', 'No description available')}
                    </div>
                </div>
            </div>
            <div class="main-content">
                <div class="map-container">
                    <iframe src="{map_viewer_url}" allowfullscreen></iframe>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    file_name = "gis_explorer.html"
    with open(file_name, "w") as file:
        file.write(html_content)

    webbrowser.open(file_name)

def process_gis_query(query: str, url: str) -> Dict:
    """Process GIS-specific queries using the ArcGIS REST API."""
    analyzer = GISDataAnalyzer()
    
    # Initialize response structure
    response = {
        "answer": "",
        "metadata": {},
        "sample_data": None,
        "statistics": None
    }
    
    # Analyze the query intent
    query_lower = query.lower()
    
    if "schema" in query_lower or "fields" in query_lower:
        layer_info = analyzer.analyze_layer_schema(url)
        response["metadata"] = layer_info
        response["answer"] = f"The layer '{layer_info['name']}' contains {len(layer_info['fields'])} fields. "
        response["answer"] += f"The geometry type is {layer_info['geometryType']}. "
        
    elif "statistics" in query_lower or "numbers" in query_lower:
        layer_info = analyzer.analyze_layer_schema(url)
        numeric_fields = [name for name, info in layer_info["fields"].items() 
                         if info["type"] in ["esriFieldTypeDouble", "esriFieldTypeInteger"]]
        
        if numeric_fields:
            field_stats = analyzer.query_layer_statistics(url, numeric_fields[0])
            response["statistics"] = field_stats
            response["answer"] = f"Here are the statistics for the field '{numeric_fields[0]}': {json.dumps(field_stats, indent=2)}"
            
    elif "sample" in query_lower or "examples" in query_lower:
        sample_data = analyzer.get_layer_sample_data(url)
        response["sample_data"] = sample_data
        response["answer"] = f"Here's a sample of {len(sample_data.get('features', []))} records from the layer."
        
    else:
        # Default to providing general information
        service_info = analyzer.get_service_info(url)
        response["metadata"] = service_info
        response["answer"] = f"This is a {service_info.get('type', 'GIS')} service. "
        response["answer"] += f"It contains {len(service_info.get('layers', []))} layers. "
    
    return response

def get_response(prompt: str) -> Dict:
    """Enhanced response handler that integrates GIS and AI capabilities."""
    feature_url_pattern = r"https?://\S+/FeatureServer(?:/\d+)?"
    match = re.search(feature_url_pattern, prompt)

    if match:
        feature_url = match.group(0)
        
        # Process GIS-specific query
        gis_response = process_gis_query(prompt, feature_url)
        
        # Enhance response with AI interpretation
        try:
            model = genai.GenerativeModel(Model)
            ai_context = f"""
            GIS Data Context:
            URL: {feature_url}
            Metadata: {json.dumps(gis_response['metadata'], indent=2)}
            Query: {prompt}
            
            Please provide a natural language interpretation of this GIS data and answer the user's query.
            """
            ai_response = model.generate_content(ai_context)
            gis_response["ai_interpretation"] = ai_response.text if ai_response else "No AI interpretation available."
            
            return gis_response
            
        except Exception as e:
            gis_response["ai_interpretation"] = f"AI interpretation failed: {str(e)}"
            return gis_response
    
    # If no GIS URL found, process as regular query using Google AI
    try:
        model = genai.GenerativeModel(Model)
        response = model.generate_content(prompt)
        return {"response": response.text if response else "No response."}
    except Exception as e:
        return {"error": f"Chatbot error: {str(e)}"}

@app.route("/chat", methods=["POST"])
def chat():
    """Enhanced chat endpoint with better error handling and response structure."""
    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Invalid request. Include 'query' field."}), 400
        
        query = data["query"].strip()
        
        # Extract URL and trigger map generation if present
        url = extract_url(query)
        if url:
            print(f"Detected GIS URL: {url}")
            generate_map(url)
        
        response = get_response(query)
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "status": "error",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
