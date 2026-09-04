import streamlit as st
import pandas as pd
import io
import os
import pypdf
import email
from email import policy

# 1. Local Hard Drive Folder Path Configuration
LOCAL_FOLDER_PATH = "documents"
logo_path = os.path.join(LOCAL_FOLDER_PATH, "logo.png")

def get_live_file_list_local():
    valid_files = []
    try:
        if os.path.exists(LOCAL_FOLDER_PATH):
            for name in os.listdir(LOCAL_FOLDER_PATH):
                if name.endswith(".pdf") or name.endswith(".xlsx") or name.endswith(".eml"):
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
        st.error("⚠️ No files found! Please ask the clerk to upload `.xlsx`, `.pdf`, or `.eml` files to the local `documents` folder.")
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
                                        if keywords:
                                            matches = any(kw in clean_line.lower() for kw in keywords)
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
                            st.metric("Lines Found in PDF", len(extracted_rows))
                            st.dataframe(output_df, use_container_width=True, hide_index=True)
                            st.write("---")
                            
                            compiled_download_text.append(f"## 📄 Source: {current_file}\n")
                            compiled_download_text.append(output_df.to_markdown(index=False))
                            compiled_download_text.append("\n\n---\n")
                            
                    except Exception as pdf_ex:
                        st.warning(f"⚠️ Skipped processing PDF text extraction fault on `{current_file}`: {pdf_ex}")

                # PROCESSING ENGINE C: EML DOCUMENTS (EMAILS)
                elif current_file.endswith(".eml"):
                    try:
                        with open(target_file_path, "rb") as f:
                            msg = email.message_from_binary_file(f, policy=policy.default)
                        
                        subject = str(msg.get('subject', '(No Subject)'))
                        from_ptr = str(msg.get('from', '(No Sender)'))
                        to_ptr = str(msg.get('to', '(No Recipient)'))
                        date_ptr = str(msg.get('date', '(No Date)'))
                        
                        body_parts = []
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    try:
                                        payload = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                                        body_parts.append(payload)
                                    except Exception:
                                        pass
                        else:
                            try:
                                payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                                body_parts.append(payload)
                            except Exception:
                                pass
                                
                        body_text = "\n".join(body_parts).strip()
                        
                        if not body_text:
                            try:
                                fallback_body = msg.get_body(preferencelist=('plain', 'html'))
                                if fallback_body:
                                    body_text = fallback_body.get_content()
