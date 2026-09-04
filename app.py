import streamlit as st
import pandas as pd
import io
import os
import pdfplumber  # Upgraded from pypdf to handle structured tables and borderless layouts

# 1. Local Hard Drive Folder Path Configuration
LOCAL_FOLDER_PATH = "documents"
logo_path = os.path.join(LOCAL_FOLDER_PATH, "logo.png")

def get_live_file_list_local():
    valid_files = []
    try:
        if os.path.exists(LOCAL_FOLDER_PATH):
            for name in os.listdir(LOCAL_FOLDER_PATH):
                if name.endswith(".pdf") or name.endswith(".xlsx"):
                    valid_files.append(name)
    except Exception:
        pass
    return sorted(valid_files)

# 2. Page Configurations
st.set_page_config(
    layout="centered", 
    page_title="Precisco Query Portal",
    initial_sidebar_state="collapsed"
)

# 3. SECURE GATEKEEPER LOGIN SCREEN
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # Center container container for clean rendering across mobile screens
    with st.container():
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        st.title("🔒 Precisco Supply Chain Portal")
        st.subheader("Login required to access secure rate databases")
        
        input_password = st.text_input("Enter System Password:", type="password")
        
        if st.button("Access Dashboard", use_container_width=True):
            if input_password == "Precisco2026":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password credentials. Please try again.")
            
else:
    # 4. LOGGED IN BRANDED DASHBOARD
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with col2:
        st.title("Precisco Query System")
        st.caption("Precision in Supply Chain Management")

    st.write("---")

    available_files = get_live_file_list_local()

    if not available_files:
        st.error("⚠️ No files found! Please ask the clerk to upload `.xlsx` or `.pdf` files to the local `documents` folder.")
    else:
        st.info("💡 Instructions: Clear the box below to see ALL rows across ALL files. Or search any keyword (e.g., 'ANL', 'BENLINE', 'Yantian') to filter your data networks instantly.")
        user_query = st.text_input("Enter search keywords:", placeholder="e.g. ANL, Yantian")
        
        # Parse search keys using original working logic
        keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
        
        # Structures to keep track of compiled data for downloading
        compiled_download_text = []
        compiled_download_text.append("# Precisco Search Export Summary\n")
        compiled_download_text.append(f"**Search Query Applied:** {user_query if user_query else 'ALL (No Filter)'}\n")
        compiled_download_text.append("---\n")
        
        total_matches_found = 0
        
        with st.spinner("Processing global supply chain matrices..."):
            for current_file in available_files:
                target_file_path = os.path.join(LOCAL_FOLDER_PATH, current_file)
                
                if not os.path.exists(target_file_path):
                    st.error(f"File {current_file} missing during live retrieval cycle.")
                    continue
                
                # PROCESSING ENGINE A: EXCEL SPREADSHEETS
                if current_file.endswith(".xlsx"):
                    try:
                        xl = pd.ExcelFile(target_file_path, engine='openpyxl')
                        sheet_names = xl.sheet_names
                        
                        for sheet in sheet_names:
                            # Read file natively as is without structural mutations
                            df = pd.read_excel(target_file_path, sheet_name=sheet, dtype=str)
                            
                            if keywords:
                                pattern = '|'.join(keywords)
                                mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any(axis=1)
                                df_filtered = df[mask]
                            else:
                                df_filtered = df
                                
                            if not df_filtered.empty:
                                total_matches_found += len(df_filtered)
                                
                                # Render Headers Visually
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.markdown(f"**📑 Sheet:** {sheet}")
                                st.metric(f"Rows Found in '{sheet}'", len(df_filtered))
                                st.dataframe(df_filtered, use_container_width=True, hide_index=False)
                                st.write("---")
                                
                                # Convert to text representation for the unified download download package
                                compiled_download_text.append(f"## 📄 Source: {current_file}")
                                compiled_download_text.append(f"### 📑 Sheet: {sheet}\n")
                                compiled_download_text.append(df_filtered.to_markdown(index=False))
                                compiled_download_text.append("\n\n---\n")
                                
                    except Exception as sheet_ex:
                        st.warning(f"⚠️ Skipped processing Excel sheet parsing error on `{current_file}`: {sheet_ex}")

                # PROCESSING ENGINE B: PDF DOCUMENTS (WITH TEXT-LAYOUT STRATEGY FALLBACK)
                elif current_file.endswith(".pdf"):
                    try:
                        with pdfplumber.open(target_file_path) as pdf:
                            for page_num, page in enumerate(pdf.pages, start=1):
                                # 1. Try extracting explicit tables first (Bordered/Grid layout)
                                tables = page.extract_tables()
                                
                                # 2. If no tables or empty data found, switch to Text Layout Analysis (Borderless fallback)
                                if not tables or len(tables) == 0 or (len(tables) == 1 and not tables[0]):
                                    # Fallback: Capture text using layout=True to preserve column spatial alignments
                                    text_layout = page.extract_text(layout=True)
                                    if text_layout:
                                        text_rows = []
                                        for line in text_layout.split("\n"):
                                            clean_line = line.strip()
                                            if not clean_line:
                                                continue
                                            # Split by two or more spaces to preserve structured fields
                                            parts = [p.strip() for p in clean_line.split("  ") if p.strip()]
                                            if parts:
                                                text_rows.append(parts)
                                        
                                        if text_rows:
                                            # Use the first row found as headers
                                            raw_headers = text_rows[0]
                                            headers = [str(h).strip() if h else f"Column {i+1}" for i, h in enumerate(raw_headers)]
                                            data_rows = text_rows[1:] if len(text_rows) > 1 else text_rows
                                            tables = [[headers] + data_rows]
                                
                                # Process discovered data matrices
                                if tables:
                                    for table_idx, table in enumerate(tables):
                                        if not table or len(table) < 1:
                                            continue
                                        
                                        # Formulate Header Index
                                        raw_headers = table[0]
                                        headers = [str(h).strip() if h else f"Column {i+1}" for i, h in enumerate(raw_headers)]
                                        
                                        # Build clean DataFrames
                                        data_rows = table[1:]
                                        df = pd.DataFrame(data_rows)
                                        
                                        if df.empty:
                                            continue
                                            
                                        # Conform dataframe shape to header length dynamically
                                        if len(df.columns) < len(headers):
                                            headers = headers[:len(df.columns)]
                                        elif len(df.columns) > len(headers):
                                            for i in range(len(headers), len(df.columns)):
                                                headers.append(f"Column {i+1}")
                                                
                                        df.columns = headers
                                        df = df.fillna("")
                                        
                                        # Apply Keyword Search Filter
                                        if keywords:
                                            pattern = '|'.join(keywords)
