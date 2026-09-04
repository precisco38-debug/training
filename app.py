import streamlit as st
import pandas as pd
import io
import os
import pdfplumber  # Clean table extraction library

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
        
        keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
        
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
                            df = pd.read_excel(target_file_path, sheet_name=sheet, dtype=str)
                            
                            if keywords:
                                pattern = '|'.join(keywords)
                                mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any(axis=1)
                                df_filtered = df[mask]
                            else:
                                df_filtered = df
                                
                            if not df_filtered.empty:
                                total_matches_found += len(df_filtered)
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.markdown(f"**📑 Sheet:** {sheet}")
                                st.metric(f"Rows Found in '{sheet}'", len(df_filtered))
                                st.dataframe(df_filtered, use_container_width=True, hide_index=False)
                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file}")
                                compiled_download_text.append(f"### 📑 Sheet: {sheet}\n")
                                compiled_download_text.append(df_filtered.to_markdown(index=False))
                                compiled_download_text.append("\n\n---\n")
                                
                    except Exception as sheet_ex:
                        st.warning(f"⚠️ Skipped processing Excel sheet parsing error on `{current_file}`: {sheet_ex}")

                # PROCESSING ENGINE B: PDF DOCUMENTS (FIXED TO PARSE TABLES)
                elif current_file.endswith(".pdf"):
                    try:
                        all_pdf_dataframes = []
                        
                        with pdfplumber.open(target_file_path) as pdf:
                            for page_num, page in enumerate(pdf.pages, start=1):
                                # 1. Try to extract visual tables natively first
                                tables = page.extract_tables()
                                
                                for table in tables:
                                    if not table:
                                        continue
                                    
                                    # Formulate a baseline dataframe out of the extracted list matrix
                                    df_page = pd.DataFrame(table)
                                    
                                    # Set the first row as headers if available
                                    if not df_page.empty:
                                        df_page.columns = [f"Col {i+1}" if val is None or str(val).strip() == "" else str(val).strip() for i, val in enumerate(df_page.iloc[0])]
                                        df_page = df_page.drop(df_page.index[0]).reset_index(drop=True)
                                        all_pdf_dataframes.append(df_page)
                                
                                # 2. Fallback: If no geometric tables detected, extract text lines smarter
                                if not tables:
                                    text = page.extract_text()
                                    if text:
                                        fallback_rows = []
                                        for line in text.split("\n"):
                                            if line.strip():
                                                # Split by multiple spaces or tabs dynamically
                                                parts = [p.strip() for p in line.split("   ") if p.strip()]
                                                if not parts or len(parts) <= 1:
                                                    parts = [p.strip() for p in line.split("  ") if p.strip()]
                                                if parts:
                                                    fallback_rows.append(parts)
                                        if fallback_rows:
                                            max_cols = max(len(r) for r in fallback_rows)
                                            headers = [f"Column {i+1}" for i in range(max_cols)]
                                            padded_rows = [r + [""] * (max_cols - len(r)) for r in fallback_rows]
                                            all_pdf_dataframes.append(pd.DataFrame(padded_rows, columns=headers))
                        
                        # Apply unified keyword filtration process across parsed tables
                        if all_pdf_dataframes:
                            master_pdf_df = pd.concat(all_pdf_dataframes, ignore_index=True).astype(str)
                            
                            if keywords:
                                pattern = '|'.join(keywords)
                                mask = master_pdf_df.apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any(axis=1)
                                df_pdf_filtered = master_pdf_df[mask]
                            else:
                                df_pdf_filtered = master_pdf_df
                                
                            if not df_pdf_filtered.empty:
                                total_matches_found += len(df_pdf_filtered)
                                
                                # Render visual dataframe layout with headers intact
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.metric("Lines Found in PDF", len(df_pdf_filtered))
                                st.dataframe(df_pdf_filtered, use_container_width=True, hide_index=True)
                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file}\n")
                                compiled_download_text.append(df_pdf_filtered.to_markdown(index=False))
                                compiled_download_text.append("\n\n---\n")
                                
                    except Exception as pdf_ex:
                        st.warning(f"⚠️ Skipped processing PDF text extraction fault on `{current_file}`: {pdf_ex}")

