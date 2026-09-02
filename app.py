import streamlit as st
import pandas as pd
import io
import requests
from github import Github
import pypdf

# 1. Hardcoded System Variables matching your exact GitHub details
GITHUB_USER = "precisco38-debug"
GITHUB_REPO = "training"
BRANCH = "main"
FOLDER_PATH = "documents"

@st.cache_data(ttl=15)
def get_live_file_list_secure():
    try:
        g = Github()
        repo = g.get_repo(f"{GITHUB_USER}/{GITHUB_REPO}")
        contents = repo.get_contents(FOLDER_PATH, ref=BRANCH)
        
        valid_files = {}
        logo_url = None
        
        for file_content in contents:
            name = file_content.name
            if name.lower() == "logo.png":
                logo_url = file_content.download_url
            elif name.endswith(".pdf") or name.endswith(".xlsx"):
                valid_files[name] = file_content.download_url
                
        return valid_files, logo_url
    except Exception as e:
        st.error(f"GitHub safe bridge connection error: {e}")
        return {}, None

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
    # FIX: Explicitly passed the number 2 into columns to clear the TypeError snag
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
                    
                    # Case A: Processing Excel spreadsheet streams natively
                    if selected_file_name.endswith(".xlsx"):
                        df = pd.read_excel(io.BytesIO(file_response.content), header=0)
                        
                        # Clean column names by removing hidden spaces or un-named anomalies
                        df.columns = [str(c).strip() for c in df.columns]
                        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                        
                        if keywords:
                            # Force search capability across ALL columns (including Carrier)
                            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains('|'.join(keywords))).any(axis=1)
                            df = df[mask]
                        
                        # AUTOMATIC SMART SORT: Automatically sorts rows by lowest GP20 price rate
                        if "GP20" in df.columns:
                            # Safely convert price cells to numbers for accurate mathematical ranking
                            price_sort = pd.to_numeric(df["GP20"], errors='coerce')
                            df = df.iloc[price_sort.argsort()]
                            
                        if not df.empty:
                            st.dataframe(df, use_container_width=True, height=int(35 * len(df)) + 50 if len(df) < 50 else 600)
                        else:
                            st.warning("No rows inside this liner file matched your keywords.")
                        
                    # Case B: Processing PDF text streams natively
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
