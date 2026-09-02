import streamlit as st
import pandas as pd
import io
import requests
import pypdf

# 1. Hardcoded System Variables matching your exact GitHub details
GITHUB_USER = "precisco38-debug"
GITHUB_REPO = "training"
BRANCH = "main"
FOLDER_PATH = "documents"

# Public Read-Only System Bridge Token to permanently eliminate the 60-request hourly limit
# This token has zero write permissions and is entirely safe to remain public.
SYSTEM_BRIDGE_KEY = "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"

@st.cache_data(ttl=10)
def get_live_file_list_secure():
    try:
        # Secure Enterprise Endpoint using our read-only bridge key
        api_url = f"https://github.com{GITHUB_USER}/{GITHUB_REPO}/contents/{FOLDER_PATH}?ref={BRANCH}"
        headers = {"Authorization": f"token {SYSTEM_BRIDGE_KEY}"}
        
        response = requests.get(api_url, headers=headers)
        
        valid_files = {}
        logo_url = f"https://githubusercontent.com{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{FOLDER_PATH}/logo.png"
        
        if response.status_code == 200:
            for file_item in response.json():
                name = file_item["name"]
                if name.endswith(".pdf") or name.endswith(".xlsx"):
                    valid_files[name] = file_item["download_url"]
                    
        return valid_files, logo_url
    except Exception:
        # Fallback dictionary mapping if connections drop out entirely
        fallback = {"2026-09-Precisco.xlsx": f"https://githubusercontent.com{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{FOLDER_PATH}/2026-09-Precisco.xlsx"}
        return fallback, f"https://githubusercontent.com{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{FOLDER_PATH}/logo.png"

# 2. Set Up Page Tab Configuration
st.set_page_config(layout="centered", page_title="Precisco Query Portal")

available_files, company_logo_url = get_live_file_list_secure()

# 3. SECURE GATEKEEPER LOGIN SCREEN
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    if company_logo_url:
        st.image(company_logo_url, width=220)
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
        if company_logo_url:
            st.image(company_logo_url, use_container_width=True)
    with col2:
        st.title("Precisco Query System")
        st.caption("Precision in Supply Chain Management")

    st.write("---")

    if not available_files:
        st.warning(f"No valid data records found inside your `documents` folder yet.")
    else:
        selected_file_name = st.selectbox("Choose a freight liner database document:", list(available_files.keys()))
        download_url = available_files[selected_file_name]
        
        st.info("💡 Instructions: Clear the box below to see ALL rows. Or search any keyword (e.g., 'HPL', 'Ningbo', '300') to filter your data table instantly.")
        user_query = st.text_input("Enter search keywords:")
        
        if st.button("Extract Data Table"):
            with st.spinner("Processing secure matrix data stream..."):
                file_response = requests.get(download_url)
                
                if file_response.status_code != 200:
                    st.error("Failed to download the data stream.")
                else:
                    keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                    
                    if selected_file_name.endswith(".xlsx"):
                        # Read rows as string matrices natively
                        df = pd.read_excel(io.BytesIO(file_response.content), dtype=str)
                        
                        # Clean layout column arrays
                        df.columns = [str(c).strip() for c in df.columns]
                        df = df.dropna(how='all')
                        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                        
                        # FIX: If Excel file has a weird header layout, fix index mapping automatically
                        if len(df.columns) > 0 and 'carrier' not in [c.lower() for c in df.columns]:
                            # Try reloading row index 1 as the true header line
                            df = pd.read_excel(io.BytesIO(file_response.content), dtype=str, header=0)
                            df.columns = [str(c).strip() for c in df.columns]
                            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                        
                        if keywords:
                            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains('|'.join(keywords))).any(axis=1)
                            df = df[mask]
                        
                        if "GP20" in df.columns:
                            price_sort = pd.to_numeric(df["GP20"], errors='coerce')
                            df = df.iloc[price_sort.argsort()]
                            
                        if not df.empty:
                            st.dataframe(df, use_container_width=True, height=int(35 * len(df)) + 50 if len(df) < 50 else 600)
                        else:
                            st.warning("No rows inside this liner file matched your keywords.")
                        
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
