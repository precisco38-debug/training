import streamlit as st
import pandas as pd
import io
import os
import pypdf

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
        st.error("⚠️ No files found! Please upload files like precisco.xlsx to the local documents folder.")
    else:
        st.info("💡 Select a Country or Port, or enter keywords manually. Changing one field will automatically clear the others.")
        
        # --- DYNAMIC DROPDOWN EXTRACTION ---
        @st.cache_data(show_spinner=False)
        def extract_dropdown_options(file_list):
            countries = set()
            ports = set()
            for current_file in file_list:
                if current_file.endswith(".xlsx"):
                    try:
                        target_file_path = os.path.join(LOCAL_FOLDER_PATH, current_file)
                        xl = pd.ExcelFile(target_file_path, engine='openpyxl')
                        for sheet in xl.sheet_names:
                            df = pd.read_excel(target_file_path, sheet_name=sheet)
                            df.columns = df.columns.astype(str).str.upper().str.strip()
                            
                            if 'COUNTRY' in df.columns:
                                valid_countries = df['COUNTRY'].dropna().astype(str).unique()
                                countries.update([c.strip() for c in valid_countries if c.strip()])
                                
                            if 'PORT' in df.columns:
                                valid_ports = df['PORT'].dropna().astype(str).unique()
                                ports.update([p.strip() for p in valid_ports if p.strip()])
                    except Exception:
                        pass
            
            return [""] + sorted(list(countries)), [""] + sorted(list(ports))

        # Fetch the dynamic lists for both countries and ports
        country_options, port_options = extract_dropdown_options(available_files)
        
        # --- MUTUALLY EXCLUSIVE CALLBACKS ---
        def on_country_change():
            st.session_state.port_select = ""
            st.session_state.manual_input = ""
            
        def on_port_change():
            st.session_state.country_select = ""
            st.session_state.manual_input = ""
            
        def on_manual_change():
            st.session_state.country_select = ""
            st.session_state.port_select = ""
            
        # UI for Dropdowns
        col_c, col_p = st.columns(2)
        
        with col_c:
            selected_country = st.selectbox(
                "Select Country:", 
                country_options, 
                key="country_select", 
                on_change=on_country_change
            )
            
        with col_p:
            selected_port = st.selectbox(
                "Select Port:", 
                port_options, 
                key="port_select", 
                on_change=on_port_change
            )
            
        # Text box for manual entry
        manual_entry = st.text_input(
            "Or manually enter keywords (Press Return to search):", 
            placeholder="e.g. KMTC, Shanghai", 
            key="manual_input", 
            on_change=on_manual_change
        )
        
        # Build the active keyword list based on the session state
        active_keywords = []
        if st.session_state.country_select:
            active_keywords.append(st.session_state.country_select.strip().lower())
        if st.session_state.port_select:
            active_keywords.append(st.session_state.port_select.strip().lower())
        if st.session_state.manual_input.strip():
            active_keywords.extend([k.strip().lower() for k in st.session_state.manual_input.split(",") if k.strip()])
            
        compiled_download_text = []
        compiled_download_text.append("# Precisco Search Export Summary\n")
        
        search_display = ", ".join([k.title() for k in active_keywords]) if active_keywords else "ALL (No Filter)"
        compiled_download_text.append(f"**Search Query Applied:** {search_display}\n")
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
                            df = pd.read_excel(target_file_path, sheet_name=sheet)
                            df = df.fillna("")
                            
                            df_filtered = df.copy()
                            
                            # Apply AND logic: Row must contain ALL active keywords
                            if active_keywords:
                                for kw in active_keywords:
                                    # FIXED: Added regex=False so parentheses are treated as literal text
                                    mask = df_filtered.astype(str).apply(lambda x: x.str.lower().str.contains(kw, na=False, regex=False)).any(axis=1)
                                    df_filtered = df_filtered[mask]
                                
                            if not df_filtered.empty:
                                total_matches_found += len(df_filtered)
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.markdown(f"**📑 Sheet:** {sheet}")
                                st.metric(f"Rows Found in '{sheet}'", len(df_filtered))
                                st.dataframe(df_filtered, use_container_width=True, hide_index=True)
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
                        all_lines = []
                        with open(target_file_path, "rb") as f:
                            reader = pypdf.PdfReader(f)
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    for line in text.split("\n"):
                                        if line.strip():
                                            all_lines.append(line.strip())
                        
                        if all_lines:
                            detected_headers = [p.strip() for p in all_lines[0].split("  ") if p.strip()]
                            
                            extracted_rows = []
                            for line in all_lines[1:]:
                                if active_keywords:
                                    matches = all(kw in line.lower() for kw in active_keywords)
                                else:
                                    matches = True
                                    
                                if matches:
                                    parts = [p.strip() for p in line.split("  ") if p.strip()]
                                    if parts:
                                        extracted_rows.append(parts)
                            
                            if extracted_rows:
                                total_matches_found += len(extracted_rows)
                                
                                max_cols = max(max(len(r) for r in extracted_rows), len(detected_headers))
                                final_headers = detected_headers + [f"Column {i+1}" for i in range(len(detected_headers), max_cols)]
                                padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                                
                                output_df = pd.DataFrame(padded_rows, columns=final_headers[:max_cols])
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.metric("Lines Found in PDF", len(extracted_rows))
                                st.dataframe(output_df, use_container_width=True, hide_index=True)
                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file}\n")
                                compiled_download_text.append(output_df.to_markdown(index=False))
                                compiled_download_text.append("\n\n---\n")
                                
                    except Exception as pdf_ex:
                        st.warning(f"⚠️ Skipped processing PDF parsing error on `{current_file}`: {pdf_ex}")

        # 5. DYNAMIC DOWNLOAD DRAWER EXPORT
        if total_matches_found > 0:
            st.success(f"📊 Matrix generation complete! Total matches across database ecosystem: {total_matches_found}")
            final_download_payload = "\n".join(compiled_download_text)
            st.download_button(
                label="📥 Export Filtered Datasets (.md Archive)",
                data=final_download_payload,
                file_name="precisco_search_export.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.warning("🔍 No active match metrics detected. Check your parameters or verify files like precisco.xlsx are in the directory.")
