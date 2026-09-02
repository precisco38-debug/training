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
        selected_file_name = st.selectbox("Choose a freight liner database document:", available_files)
        target_file_path = os.path.join(LOCAL_FOLDER_PATH, selected_file_name)
        
        selected_sheet = None
        
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
        
        if not os.path.exists(target_file_path):
            st.error(f"File {selected_file_name} was not found on the local disk path.")
        else:
            with st.spinner("Processing data matrix view..."):
                try:
                    keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                    
                    if selected_file_name.endswith(".xlsx"):
                        # Read file natively as is without structural mutations
                        df = pd.read_excel(target_file_path, sheet_name=selected_sheet, dtype=str)
                        
                        # Filter rows using text criteria if keywords are supplied
                        if keywords:
                            pattern = '|'.join(keywords)
                            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any(axis=1)
                            df = df[mask]
                            
                        if not df.empty:
                            st.metric(f"Total Rows Found in '{selected_sheet}'", len(df))
                            st.dataframe(df, use_container_width=True, hide_index=False) 
                        else:
                            st.warning(f"No rows inside tab '{selected_sheet}' matched your keywords.")
                            
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
                            st.dataframe(output_df, use_container_width=True, hide_index=True)
                        else:
                            st.warning("No data points found matching those keywords in this PDF.")
                except Exception as ex:
                    st.error(f"An unexpected data processing error occurred: {ex}")
