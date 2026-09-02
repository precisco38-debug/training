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
st.set_page_config(layout="centered", page_title="Precisco Query Portal")
available_files = get_live_file_list_local()

# 3. SECURE GATEKEEPER LOGIN SCREEN
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    if os.path.exists(logo_path):
        st.image(logo_path, width=220)
    st.title("🔒 Precisco Supply Chain Portal")
    st.subheader("Login required to access secure rate databases")
    
    input_password = st.text_input("Enter System Password:", type="password")
    
    if st.button("Access Dashboard"):
        if input_password == "Precisco2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password credentials. Please try again.")
            
else:
    # 4. LOGGED IN BRANDED DASHBOARD
    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with col2:
        st.title("Precisco Query System")
        st.caption("Precision in Supply Chain Management")

    st.write("---")

    if not available_files:
        st.error("⚠️ No files found! Please ask the clerk to upload `.xlsx` or `.pdf` files to the GitHub `documents` folder.")
    else:
        # File selector dropdown
        selected_file_name = st.selectbox("Choose a freight liner database document:", available_files)
        target_file_path = os.path.join(LOCAL_FOLDER_PATH, selected_file_name)
        
        selected_sheet = None
        
        # DYNAMIC SHEET DETECTOR LAYER
        if selected_file_name.endswith(".xlsx"):
            try:
                xl = pd.ExcelFile(target_file_path, engine='openpyxl')
                sheet_names = xl.sheet_names
                
                selected_sheet = st.selectbox(
                    "Select workbook sheet/tab to query:", 
                    sheet_names,
                    key=f"sheet_select_{selected_file_name}"
                )
            except Exception as e:
                st.sidebar.error(f"Error loading workbook tabs: {e}")
        
        st.info("💡 Instructions: Clear the box below to see ALL rows. Or search any keyword (e.g., 'ANL', 'BENLINE', 'Yantian') to filter your data table instantly.")
        user_query = st.text_input("Enter search keywords:")
        
        if st.button("Extract Data Table"):
            with st.spinner("Reading file target matrix locally (Instant)..."):
                try:
                    if not os.path.exists(target_file_path):
                        st.error(f"File {selected_file_name} was not found on the local disk path.")
                    else:
                        keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                        
                        # Case A: Handle Excel Spreadsheet Files locally
                        if selected_file_name.endswith(".xlsx"):
                            raw_df = pd.read_excel(target_file_path, sheet_name=selected_sheet, header=None, dtype=str)
                            
                            # DYNAMIC HEADER LAYER LOCATOR
                            header_row_index = 0
                            for idx, row in raw_df.head(15).iterrows():
                                row_text = " ".join([str(val).lower() for val in row.values if pd.notna(val)])
                                if "carrier" in row_text or "port" in row_text or "region" in row_text or "location" in row_text or "a/c/t/d/w" in row_text:
                                    header_row_index = idx
                                    break
                            
                            header_series = raw_df.iloc[header_row_index].copy()
                            header_series = header_series.ffill()
                            
                            data_df = raw_df.iloc[header_row_index + 1:].copy()
                            data_df = data_df.reset_index(drop=True)
                            
                            clean_headers = []
                            for idx, val in enumerate(header_series):
                                val_str = str(val).strip().upper()
                                if val_str.startswith("UNNAMED") or val_str == "NAN" or not val_str:
                                    if idx == 0:
                                        clean_headers.append("CARRIER")
                                    else:
                                        clean_headers.append(f"COLUMN_{idx}")
                                else:
                                    clean_headers.append(val_str)
                                    
                            data_df.columns = clean_headers
                            data_df = data_df.dropna(how='all')
                            df = data_df.loc[:, ~data_df.columns.str.contains('^COLUMN_|^UNNAMED|^NAN|^NONE')]
                            
                            # Map alternate top table column formats to standardized names automatically
                            df.rename(columns={
                                'A/C/T/D/W': 'CARRIER', 
                                'A/C/T/W': 'CARRIER', 
                                'LOCATION': 'PORT',
                                'OVER LOCATION': 'VIA / OVER LOCATION',
                                'RATE 20': 'GP20', 
                                'RATE 40': 'GP40', 
                                'RATE 40H': 'GP40HC'
                            }, inplace=True)
                            
                            for col in df.columns:
                                df[col] = df[col].astype(str).str.strip()
                                
                            if 'CARRIER' in df.columns and selected_sheet and "26" not in str(selected_sheet):
                                mask_blank = (df['CARRIER'] == '') | (df['CARRIER'].isna()) | (df['CARRIER'].str.lower() == 'none')
                                df.loc[mask_blank, 'CARRIER'] = 'COSCO'
                                
                            if keywords:
                                mask = df.astype(str).apply(lambda x: x.str.lower().str.contains('|'.join(keywords))).any(axis=1)
                                df = df[mask]
                            
                            target_sort_col = "GP20" if "GP20" in df.columns else ("RATE 20" if "RATE 20" in df.columns else None)
                            if target_sort_col and target_sort_col in df.columns:
                                price_sort = pd.to_numeric(df[target_sort_col], errors='coerce')
                                df = df.iloc[price_sort.argsort()]
                                
                            if not df.empty:
                                st.metric(f"Total Quotes Found in '{selected_sheet}'", len(df))
                                st.dataframe(df, use_container_width=True, hide_index=True) 
                            else:
                                st.warning(f"No rows inside tab '{selected_sheet}' matched your keywords.")
                                
                        # Case B: Handle PDF Files locally
                        elif selected_file_name.endswith(".pdf"):
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
                                st.metric("Total Lines Found", len(extracted_rows))
                                max_cols = max(len(r) for r in extracted_rows)
                                headers = [f"Column {i+1}" for i in range(max_cols)]
                                padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                                
                                output_df = pd.DataFrame(padded_rows, columns=headers)
                                st.dataframe(output_df, use_container_width=True, hide_index=True, height=int(35 * len(output_df)) + 50 if len(output_df) < 50 else 600)
                            else:
