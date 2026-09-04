import streamlit as st
import pandas as pd
import io
import os
import pypdf
import datetime
from email import message_from_file
from bs4 import BeautifulSoup

# 1. Local Hard Drive Folder Path Configuration
LOCAL_FOLDER_PATH = "documents"
logo_path = os.path.join(LOCAL_FOLDER_PATH, "logo.png")

def get_live_file_list_local():
    valid_files = []
    try:
        if os.path.exists(LOCAL_FOLDER_PATH):
            for name in os.listdir(LOCAL_FOLDER_PATH):
                # Extended support to catch Email files (.eml) alongside PDFs and Excels
                if name.endswith(".pdf") or name.endswith(".xlsx") or name.endswith(".eml"):
                    valid_files.append(name)
    except Exception:
        pass
    return sorted(valid_files)

def get_file_timestamp(file_path):
    """Retrieves localized last modification time for record validation."""
    try:
        timestamp = os.path.getmtime(file_path)
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Unknown Time"

def evaluate_logic_query(text_to_check, raw_query_string):
    """
    Evaluates text targeting smart logic expressions (AND, OR, NOT, or commas).
    Falls back to original standard matching if no special operators are present.
    """
    text_clean = text_to_check.lower()
    q_upper = raw_query_string.strip().upper()
    
    # Context Processing: Handle advanced expressions safely
    if " AND " in q_upper or " OR " in q_upper or " NOT " in q_upper:
        # Standardize evaluation spaces using python boolean operators
        eval_string = raw_query_string.lower()
        # Protect logic structures from string mutations by evaluating isolated parts
        import re
        tokens = re.findall(r'\b\w+\b', eval_string)
        # Unique filter words excluding operational syntax commands
        keywords = [t for t in tokens if t not in ["and", "or", "not"]]
        
        for kw in keywords:
            has_word = str(kw in text_clean).lower()
            # Replace complete token word boundary to prevent breaking words containing 'and' / 'or'
            eval_string = re.sub(rf'\b{kw}\b', has_word, eval_string)
            
        try:
            # Safely evaluate calculated boolean string mapping
            return eval(eval_string, {"__builtins__": None}, {})
        except Exception:
            return False
            
    else:
        # Fallback Engine: Preserve your exact comma-separated text matching rule
        keywords = [k.strip().lower() for k in raw_query_string.split(",") if k.strip()]
        if not keywords:
            return True
        return any(kw in text_clean for kw in keywords)

# 3. Page Configurations
st.set_page_config(
    layout="centered", 
    page_title="Precisco Query Portal",
    initial_sidebar_state="collapsed"
)

# 4. SECURE GATEKEEPER LOGIN SCREEN
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
    # 5. LOGGED IN BRANDED DASHBOARD
    col1, col2 = st.columns()
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with col2:
        st.title("Precisco Query System")
        st.caption("Precision in Supply Chain Management")

    st.write("---")

    available_files = get_live_file_list_local()

    if not available_files:
        st.error("⚠️ No files found! Please upload `.xlsx`, `.pdf`, or `.eml` files to the local `documents` folder.")
    else:
        st.info("💡 **Instructions:** Use logic statements like `ANL AND Yantian`, `ANL OR BENLINE`, or standard commas to search globally.")
        user_query = st.text_input("Enter search query or keywords:", placeholder="e.g., Singapore AND ANL")
        
        # Build document export payload data structure
        compiled_download_text = []
        compiled_download_text.append("# Precisco Advanced Search Export Summary\n")
        compiled_download_text.append(f"**Query Logic Applied:** {user_query if user_query else 'ALL (No Filter)'}\n")
        compiled_download_text.append("---\n")
        
        total_matches_found = 0
        
        with st.spinner("Processing global supply chain matrices..."):
            for current_file in available_files:
                target_file_path = os.path.join(LOCAL_FOLDER_PATH, current_file)
                file_time = get_file_timestamp(target_file_path)
                
                if not os.path.exists(target_file_path):
                    st.error(f"File {current_file} missing during live retrieval cycle.")
                    continue
                
                # PROCESSING ENGINE A: EXCEL SPREADSHEETS
                if current_file.endswith(".xlsx"):
                    try:
                        xl = pd.ExcelFile(target_file_path, engine='openpyxl')
                        for sheet in xl.sheet_names:
                            df = pd.read_excel(target_file_path, sheet_name=sheet, dtype=str)
                            
                            if user_query.strip():
                                # Evaluate rows individually using dynamic logical operator sets
                                mask = df.astype(str).apply(
                                    lambda row: evaluate_logic_query(" ".join(row.values), user_query), axis=1
                                )
                                df_filtered = df[mask]
                            else:
                                df_filtered = df
                                
                            if not df_filtered.empty:
                                total_matches_found += len(df_filtered)
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.caption(f"🕒 **Last Updated:** {file_time} | **Type:** Excel Spreadsheet")
                                st.markdown(f"**📑 Sheet Name Target:** `{sheet}`")
                                st.metric(f"Rows Found in '{sheet}'", len(df_filtered))
                                st.dataframe(df_filtered, use_container_width=True, hide_index=False)
                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file} (Modified: {file_time})")
                                compiled_download_text.append(f"### 📑 Sheet: {sheet}\n")
                                compiled_download_text.append(df_filtered.to_markdown(index=False))
                                compiled_download_text.append("\n\n---\n")
                                
                    except Exception as sheet_ex:
                        st.warning(f"⚠️ Skipped Excel sheet parsing error on `{current_file}`: {sheet_ex}")

                # PROCESSING ENGINE B: PDF DOCUMENTS
                elif current_file.endswith(".pdf"):
                    try:
                        extracted_rows = []
                        with open(target_file_path, "rb") as f:
                            reader = pypdf.PdfReader(f)
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    for line in text.split("\n"):
                                        clean_line = line.strip()
                                        if not clean_line:
                                            continue
                                        
                                        if user_query.strip():
                                            matches = evaluate_logic_query(clean_line, user_query)
                                        else:
                                            matches = True
                                            
                                        if matches:
                                            parts = [p.strip() for p in clean_line.split("  ") if p.strip()]
                                            if parts:
                                                extracted_rows.append(parts)
                        
                        if extracted_rows:
                            total_matches_found += len(extracted_rows)
                            max_cols = max(len(r) for r in extracted_rows)
                            headers = [f"Column {i+1}" for i in range(max_cols)]
                            padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                            output_df = pd.DataFrame(padded_rows, columns=headers)
                            
                            st.markdown(f"### 📄 Source: `{current_file}`")
                            st.caption(f"🕒 **Last Updated:** {file_time} | **Type:** PDF Document")
                            st.metric("Lines Found in PDF", len(extracted_rows))
                            st.dataframe(output_df, use_container_width=True, hide_index=True)
                            st.write("---")
                            
                            compiled_download_text.append(f"## 📄 Source: {current_file} (Modified: {file_time})\n")
