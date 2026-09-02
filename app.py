import streamlit as st
import requests
import pandas as pd
import io
import json
from google import genai
from google.genai import types
# FIX: Import BaseModel directly from pydantic instead of the genai module
from pydantic import BaseModel

# 1. Initialize Gemini Client
client = genai.Client()

# 2. Hardcoded System Variables matching your exact GitHub details
GITHUB_USER = "precisco38-debug"
GITHUB_REPO = "training"
BRANCH = "main"
FOLDER_PATH = "documents"

# Define structured constraints so Gemini outputs clear columns/rows for the app table
class TableRow(BaseModel):
    column_values: list[str]

class TableStructure(BaseModel):
    headers: list[str]
    rows: list[TableRow]

@st.cache_data(ttl=15)
def get_live_file_list():
    api_url = f"https://github.com{GITHUB_USER}/{GITHUB_REPO}/contents/{FOLDER_PATH}?ref={BRANCH}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return {}
    files_json = response.json()
    valid_files = {}
    for file in files_json:
        name = file["name"]
        if name.endswith(".pdf") or name.endswith(".xlsx"):
            valid_files[name] = file["download_url"]
    return valid_files

# 3. Streamlit Interface Build
st.set_page_config(layout="centered", page_title="Universal Query System")
st.title("🔍 Multi-File Query System")

available_files = get_live_file_list()

if not available_files:
    st.warning(f"No valid .pdf or .xlsx documents found inside your `documents` folder yet. Ask your clerk to upload one.")
else:
    # Dropdown loads automatically from your repo's 'documents' folder
    selected_file_name = st.selectbox("Choose a document to query:", list(available_files.keys()))
    download_url = available_files[selected_file_name]
    
    user_query = st.text_input(f"What data would you like to extract from '{selected_file_name}' into a table?")
    
    if st.button("Generate Dynamic Table") and user_query:
        with st.spinner("Gemini AI is parsing your document formatting..."):
            file_response = requests.get(download_url)
            
            if file_response.status_code != 200:
                st.error("Failed to read file from GitHub.")
            else:
                file_bytes = file_response.content
                prompt = f"Analyze this content. Disregard layout discrepancies and map the following details into rows and columns: {user_query}"
                
                try:
                    # Case A: Handling PDF layouts
                    if selected_file_name.endswith(".pdf"):
                        res = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[
                                types.Part.from_bytes(data=file_bytes, mime_type='application/pdf'),
                                prompt
                            ],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=TableStructure,
                            ),
                        )
                    # Case B: Handling Spreadsheet layouts
                    else:
                        df = pd.read_excel(io.BytesIO(file_bytes))
                        markdown_data = df.to_markdown(index=False)
                        res = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"Spreadsheet content:\n{markdown_data}\n\nTask: {prompt}",
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=TableStructure,
                            ),
                        )
                    
                    # Reassemble structural JSON directly into interactive UI Table
                    data = json.loads(res.text)
                    table_headers = data.get("headers", [])
                    table_rows = [row["column_values"] for row in data.get("rows", [])]
                    
                    output_df = pd.DataFrame(table_rows, columns=table_headers)
                    st.dataframe(output_df, use_container_width=True)
                    
                    # Add download button for users
                    csv_data = output_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Result as CSV", data=csv_data, file_name="extracted_table.csv", mime="text/csv")
                    
                except Exception as e:
                    st.error(f"Error structuring dynamic output table: {e}")
