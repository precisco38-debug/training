import streamlit as st
import pandas as pd
import io
import requests
import pypdf

# 1. HARDCODED BASE SYSTEM VALUES (Completely separated to guarantee zero typos)
DOMAIN = "https://githubusercontent.com"
USER = "precisco38-debug"
REPO = "training"
BRANCH = "main"
FOLDER = "documents"

# Clean, pre-built static link paths
RAW_FOLDER_URL = f"{DOMAIN}/{USER}/{REPO}/{BRANCH}/{FOLDER}"
company_logo_url = f"{RAW_FOLDER_URL}/logo.png"

# 2. FILE SELECTION MAP (Zero-Maintenance File Syncing)
# When your clerk adds a new file to GitHub, simply add a new row to this list!
available_files = {
    "2026-09-Precisco.xlsx": f"{RAW_FOLDER_URL}/2026-09-Precisco.xlsx",
    # "2026-10-Precisco.xlsx": f"{RAW_FOLDER_URL}/2026-10-Precisco.xlsx",
}

# 3. Set Up Page Tab Configuration
st.set_page_config(layout="centered", page_title="Precisco Query Portal")

# 4. SECURE GATEKEEPER LOGIN SCREEN
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
    # 5. LOGGED IN BRANDED DASHBOARD
    col1, col2 = st.columns(2)
    with col1:
        if company_logo_url:
            st.image(company_logo_url, use_container_width=True)
    with col2:
        st.title("Precisco Query System")
        st.caption("Precision in Supply Chain Management")

    st.write("---")

    selected_file_name = st.selectbox("Choose a freight liner database document:", list(available_files.keys()))
    download_url = available_files[selected_file_name]
    
    st.info("💡 Instructions: Clear the box below to see ALL rows. Or search any keyword (e.g., 'HPL', 'Ningbo', '300') to filter your data table instantly.")
    user_query = st.text_input("Enter search keywords:")
    
    if st.button("Extract Data Table"):
        with st.spinner("Processing secure matrix data stream..."):
            file_response = requests.get(download_url, timeout=15)
            
            if file_response.status_code != 200:
                st.error("Failed to stream data from secure file path storage.")
            else:
                keywords = [k.strip().lower() for k in user_query.split(",") if k.strip()]
                
                if selected_file_name.endswith(".xlsx"):
                    # FIX: Force Python to read row 0 natively as headers to capture all header variants
                    df = pd.read_excel(io.BytesIO(file_response.content), header=None, dtype=str)
                    
                    # Force row 0 to act as our explicit headers to expose the CARRIER column
                    df.columns = [str(c).strip().upper() for c in df.iloc[0]]
                    df = df[1:]  # Shift data frame down by 1 row to separate the payload rows
                    
                    # Clear away unassigned or blank layout columns
                    df = df.dropna(how='all')
                    df = df.loc[:, ~df.columns.str.contains('^UNNAMED|^NAN|^NONE')]
                    
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
