import streamlit as st
import pandas as pd
import io
import requests
from github import Github
import pypdf

# 1. Hardcoded System Variables matching your exact GitHub details
GITHUB_USER = "precisco38-debug"
GITHUB_REPO = "training"
BRANCH = "main"
FOLDER_PATH = "documents"

@st.cache_data(ttl=15)
def get_live_file_list_secure():
    try:
        g = Github()
        repo = g.get_repo(f"{GITHUB_USER}/{GITHUB_REPO}")
        contents = repo.get_contents(FOLDER_PATH, ref=BRANCH)
        
        valid_files = {}
        for file_content in contents:
            name = file_content.name
            if name.endswith(".pdf") or name.endswith(".xlsx"):
                valid_files[name] = file_content.download_url
        return valid_files
    except Exception as e:
        st.error(f"GitHub safe bridge connection error: {e}")
        return {}

# 2. Streamlit Interface Build
st.set_page_config(layout="centered", page_title="Universal Query System")
st.title("⚡ Enterprise Fast Query System (POC)")

available_files = get_live_file_list_secure()

if not available_files:
    st.warning(f"No valid .pdf or .xlsx documents found inside your `documents` folder yet.")
else:
    selected_file_name = st.selectbox("Choose a document to query:", list(available_files.keys()))
    download_url = available_files[selected_file_name]
    
    st.info("💡 Instructions: Clear the box below and click the button to see ALL rows. Or type specific keywords separated by commas (e.g., 'Asia, Singapore, Durban') to filter rows instantly.")
    user_query = st.text_input("Enter search keywords:")
    
    if st.button("Extract Data Table"):
        with st.spinner("Processing file locally (Instant)..."):
            file_response = requests.get(download_url)
            
            if file_response.status_code != 200:
                st.error("Failed to download the document data stream.")
            else:
                # Clean up user keywords
                keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                
                # Case A: Handling Excel Spreadsheet files natively
                if selected_file_name.endswith(".xlsx"):
                    df = pd.read_excel(io.BytesIO(file_response.content))
                    
                    if keywords:
                        # Find rows that contain ANY of the typed keywords
                        mask = df.astype(str).apply(lambda x: x.str.lower().str.contains('|'.join(keywords))).any(axis=1)
                        df = df[mask]
                        
                    if not df.empty:
                        # Renders interactive UI table tall enough to view up to 50 rows at once without scrollbars
                        st.dataframe(df, use_container_width=True, height=int(35 * len(df)) + 50 if len(df) < 50 else 600)
                    else:
                        st.warning("No rows matched your keywords in this spreadsheet.")
                    
                # Case B: Handling PDF text files natively
                elif selected_file_name.endswith(".pdf"):
                    pdf_file = io.BytesIO(file_response.content)
                    reader = pypdf.PdfReader(pdf_file)
                    
                    extracted_rows = []
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            for line in text.split("\n"):
                                clean_line = line.strip()
                                if not clean_line:
                                    continue
                                    
                                # Check if line matches any keywords
                                if keywords:
                                    matches = any(kw in clean_line.lower() for kw in keywords)
                                else:
                                    matches = True
                                    
                                if matches:
                                    parts = [p.strip() for p in clean_line.split("  ") if p.strip()]
                                    if parts:
                                        extracted_rows.append(parts)
                    
                    if extracted_rows:
                        max_cols = max(len(r) for r in extracted_rows)
                        headers = [f"Column {i+1}" for i in range(max_cols)]
                        padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                        
                        output_df = pd.DataFrame(padded_rows, columns=headers)
                        st.dataframe(output_df, use_container_width=True, height=int(35 * len(output_df)) + 50 if len(output_df) < 50 else 600)
                    else:
                        st.warning("No matching lines found inside this PDF document.")
