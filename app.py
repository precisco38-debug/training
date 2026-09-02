import streamlit as st
import pandas as pd
import io
import os
import pypdf

# 1. Local Hard Drive Folder Path
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
        
    if not valid_files:
        valid_files = ["2026-09-Precisco.xlsx"]
        
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

    selected_file_name = st.selectbox("Choose a freight liner database document:", available_files)
    target_file_path = os.path.join(LOCAL_FOLDER_PATH, selected_file_name)
    
    st.info("💡 Instructions: Clear the box below to see ALL rows. Or search any keyword (e.g., 'Asia', 'Singapore', 'HPL') to filter your data table instantly.")
    user_query = st.text_input("Enter search keywords:")
    
    if st.button("Extract Data Table"):
        with st.spinner("Reading file from local disk (Instant)..."):
            try:
                if not os.path.exists(target_file_path):
                    st.error(f"File {selected_file_name} was not found on the local disk path.")
                else:
                    keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                    
                    # Case A: Handle Excel Spreadsheet Files locally
                    if selected_file_name.endswith(".xlsx"):
                        # Read the full raw sheet to locate data positions safely
                        raw_df = pd.read_excel(target_file_path, header=None, dtype=str)
                        
                        # DYNAMIC HEADER DETECTOR: Find the row containing "CARRIER", "PORT", or "REGION"
                        header_row_index = 0
                        for idx, row in raw_df.iterrows():
                            row_text = " ".join([str(val).lower() for val in row.values if pd.notna(val)])
                            if "carrier" in row_text or "port" in row_text or "region" in row_text:
                                header_row_index = idx
                                break
                        
                        # Reload the data frame starting precisely from that identified row layer
                        df = pd.read_excel(target_file_path, skiprows=header_row_index, dtype=str)
                        
                        # Clean column headers and enforce explicit upper-case names
                        df.columns = [str(c).strip().upper() for c in df.columns]
                        
                        # PRESERVE CARRIER FEATURE CRITICAL FIX:
                        # Re-verify if any first column got truncated or masked by unnamed artifacts
                        if len(df.columns) > 0 and df.columns[0].startswith("UNNAMED"):
                            df.rename(columns={df.columns[0]: "CARRIER"}, inplace=True)
                        
                        df = df.dropna(how='all')
                        # Filter out secondary structural trailing unnamed anomalies, preserving CARRIER
                        df = df.loc[:, ~df.columns.str.contains('^UNNAMED:_[1-9]|^NAN|^NONE')]
                        
                        if keywords:
                            # Filter across all available matrix cell blocks
                            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains('|'.join(keywords))).any(axis=1)
                            df = df[mask]
                        
                        if "GP20" in df.columns:
                            price_sort = pd.to_numeric(df["GP20"], errors='coerce')
                            df = df.iloc[price_sort.argsort()]
                            
                        if not df.empty:
                            st.dataframe(df, use_container_width=True, height=int(35 * len(df)) + 50 if len(df) < 50 else 600)
                        else:
                            st.warning("No rows inside this liner file matched your keywords.")
                            
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
                            max_cols = max(len(r) for r in extracted_rows)
                            headers = [f"Column {i+1}" for i in range(max_cols)]
                            padded_rows = [r + [""] * (max_cols - len(r)) for r in extracted_rows]
                            
                            output_df = pd.DataFrame(padded_rows, columns=headers)
                            st.dataframe(output_df, use_container_width=True, height=int(35 * len(output_df)) + 50 if len(output_df) < 50 else 600)
                        else:
                            st.warning("No data points found matching those keywords in this PDF.")
            except Exception as e:
                st.error(f"Local storage read error: {e}")
