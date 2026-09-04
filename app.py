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

def extract_excel_data_and_notes(df):
    """
    Separates main tabular data from trailing quotation notes/footnotes in an Excel DataFrame.
    Returns a tuple of (clean_df, list_of_notes).
    """
    if df.empty:
        return df, []

    note_indicators = (
        "note", "notes", "term", "terms", "remark", "remarks", 
        "nb:", "n.b.", "*", "disclaimer", "validity", "condition", 
        "conditions", "subject to", "special note"
    )
    
    data_indices = []
    notes = []
    in_notes_section = False

    for idx, row in df.iterrows():
        # Get non-empty cell values for the current row
        row_values = [str(val).strip() for val in row if pd.notna(val) and str(val).strip() != ""]
        if not row_values:
            continue
            
        full_row_text = " ".join(row_values)
        first_cell_lower = row_values[0].lower()
        
        # Check if current row starts a notes block or is a single-cell/trailing note row
        is_note = (
            in_notes_section or
            any(first_cell_lower.startswith(prefix) for prefix in note_indicators) or
            (len(row_values) == 1 and len(df.columns) > 2 and any(kw in full_row_text.lower() for kw in note_indicators))
        )
        
        if is_note:
            in_notes_section = True
            notes.append(full_row_text)
        else:
            data_indices.append(idx)

    clean_df = df.loc[data_indices].reset_index(drop=True) if data_indices else pd.DataFrame(columns=df.columns)
    return clean_df, notes

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
                            raw_df = pd.read_excel(target_file_path, sheet_name=sheet)
                            raw_df = raw_df.fillna("")
                            
                            # Separate table data from trailing quotation notes
                            clean_df, sheet_notes = extract_excel_data_and_notes(raw_df)
                            
                            if keywords:
                                pattern = '|'.join(keywords)
                                mask = clean_df.astype(str).apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any(axis=1)
                                df_filtered = clean_df[mask]
                            else:
                                df_filtered = clean_df
                                
                            if not df_filtered.empty or (sheet_notes and not keywords):
                                total_matches_found += len(df_filtered)
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.markdown(f"**📑 Sheet:** {sheet}")
                                st.metric(f"Rows Found in '{sheet}'", len(df_filtered))
                                st.dataframe(df_filtered, use_container_width=True, hide_index=True)
                                
                                # Render extracted notes under the data table
                                if sheet_notes:
                                    st.markdown("##### 📌 **Quotation Notes & Terms:**")
                                    for note in sheet_notes:
                                        st.info(f"• {note}")
                                
                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file}")
                                compiled_download_text.append(f"### 📑 Sheet: {sheet}\n")
                                compiled_download_text.append(df_filtered.to_markdown(index=False))
                                if sheet_notes:
                                    compiled_download_text.append("\n\n**📌 Notes & Terms:**\n")
                                    for note in sheet_notes:
                                        compiled_download_text.append(f"- {note}\n")
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
                            pdf_notes = []
                            note_prefixes = ("note:", "notes:", "terms:", "remark:", "remarks:", "*", "nb:", "disclaimer:")
                            
                            for line in all_lines[1:]:
                                line_lower = line.lower()
                                # Check if line is a footnote / quotation note
                                if any(line_lower.startswith(prefix) for prefix in note_prefixes):
                                    pdf_notes.append(line)
                                    continue

                                if keywords:
                                    matches = any(kw in line_lower for kw in keywords)
                                else:
                                    matches = True
                                if matches:
                                    parts = [p.strip() for p in line.split("  ") if p.strip()]
                                    if parts:
                                        extracted_rows.append(parts)
                            
                            if extracted_rows or pdf_notes:
                                total_matches_found += len(extracted_rows)
                                
                                max_cols = max(max((len(r) for r in extracted_rows), default=1), len(detected_headers))
                                final_headers = detected_headers + [f"Column {i+1}" for i in range(len(detected_headers), max_cols)]
                                padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                                
                                output_df = pd.DataFrame(padded_rows, columns=final_headers[:max_cols])
                                
                                st.markdown(f"### 📄 Source: `{current_file}`")
                                st.metric("Lines Found in PDF", len(extracted_rows))
                                if not output_df.empty:
                                    st.dataframe(output_df, use_container_width=True, hide_index=True)
                                
                                # Render extracted PDF notes
                                if pdf_notes:
                                    st.markdown("##### 📌 **Quotation Notes & Terms:**")
                                    for note in pdf_notes:
                                        st.info(f"• {note}")

                                st.write("---")
                                
                                compiled_download_text.append(f"## 📄 Source: {current_file}\n")
                                compiled_download_text.append(output_df.to_markdown(index=False))
                                if pdf_notes:
                                    compiled_download_text.append("\n\n**📌 Notes & Terms:**\n")
                                    for note in pdf_notes:
                                        compiled_download_text.append(f"- {note}\n")
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
            st.warning("🔍 No active match metrics detected inside data arrays. Try expanding keywords.")
