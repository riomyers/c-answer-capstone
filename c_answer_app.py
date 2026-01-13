import streamlit as st
import requests
from ai_agent import analyze_trial_eligibility 

# --- CONFIGURATION ---
st.set_page_config(
    page_title="C-Answer", 
    page_icon="🎗️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ELEGANT DESIGN SYSTEM (CSS) ---
st.markdown("""
<style>
    /* 1. IMPORT FONTS: Playfair Display (Headers) & Lato (Body) */
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Playfair+Display:wght@400;600;700&display=swap');
    
    /* 2. APPLY FONTS */
    html, body, [class*="css"] {
        font-family: 'Lato', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* 3. CLEAN UP UI ELEMENTS */
    [data-testid="InputInstructions"] { display: none !important; }
    
    /* 4. CARD STYLING (The "Glass" Look) */
    div.stExpander {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        margin-bottom: 16px;
        background-color: #1E293B !important; /* Dark Slate Base */
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    div[data-testid="stExpander"] > details {
        background-color: #1E293B !important;
        border-radius: 12px;
    }
    
    /* 5. ELEGANT BADGES */
    .status-badge {
        background-color: rgba(16, 185, 129, 0.1); /* Subtle Emerald */
        color: #6EE7B7; /* Bright Emerald Text */
        padding: 6px 16px;
        border-radius: 99px;
        font-family: 'Lato', sans-serif;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    /* 6. PRIMARY BUTTON (Gradient) */
    div.stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); /* Indigo Gradient */
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-family: 'Lato', sans-serif;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        width: 100%;
        margin-top: 10px;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6);
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        color: white;
    }
    
    /* 7. TEXT INPUTS (Clean & Spacious) */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px;
        padding-top: 10px;
        padding-bottom: 10px;
    }

</style>
""", unsafe_allow_html=True)

# --- HELPER: VERTICAL SPACER ---
def spacer(height=20):
    st.markdown(f"<div style='height: {height}px'></div>", unsafe_allow_html=True)

# --- API FUNCTION ---
def fetch_clinical_trials(condition, status="RECRUITING"):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": 50,
        "sort": "LastUpdateSubmitDate"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return {}

# --- STATE INITIALIZATION ---
if 'studies' not in st.session_state:
    st.session_state.studies = []
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'active_nct_id' not in st.session_state:
    st.session_state.active_nct_id = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

# --- HEADER SECTION (With Restored Ribbon) ---
col_logo, col_title = st.columns([1, 8])

with col_logo:
    # Large Elegant Ribbon
    st.markdown("<div style='font-size: 3.5rem; line-height: 1; text-align: center;'>🎗️</div>", unsafe_allow_html=True)

with col_title:
    st.markdown("""
    <h1 style='margin-bottom: 0px; font-size: 3rem;'>C-Answer</h1>
    <p style='font-size: 1.1rem; opacity: 0.8; margin-top: 5px; font-family: "Lato", sans-serif;'>
        Intelligent Clinical Trial Matching & Recovery Planning
    </p>
    """, unsafe_allow_html=True)

spacer(20)

# --- SMART SEARCH PANEL ---
is_expanded = not st.session_state.search_performed

with st.expander("🔍  Search Settings & Patient Profile", expanded=is_expanded):
    st.markdown("Configure your parameters below to find active trials.")
    
    with st.form("patient_form"):
        st.write("**1. Diagnosis**")
        diagnosis = st.text_input("Primary Condition", value="", placeholder="e.g. Colorectal Cancer")
        spacer(10)
        
        st.write("**2. Metastasis**")
        metastasis = st.text_input("Metastasis Location", value="", placeholder="e.g. Liver, Lung")
        spacer(10)
        
        st.write("**3. Demographics**")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", value=None, placeholder="e.g. 35", step=1)
        with col2:
            sex = st.selectbox("Sex", ["Select...", "Male", "Female"])
        spacer(15)
            
        st.write("**Advanced Filters**")
        c1, c2 = st.columns(2)
        with c1:
            kras = st.checkbox("KRAS Wild-type", value=False)
        with c2:
            phase1 = st.checkbox("Exclude Phase 1", value=False)
        
        spacer(20)
        submitted = st.form_submit_button("Find Matching Trials", type="primary")

# --- SEARCH LOGIC ---
if submitted:
    if not diagnosis.strip():
        st.warning("⚠️ Please enter a diagnosis to start your search.")
    else:
        st.session_state.search_performed = True
        st.session_state.analysis_results = {}
        st.session_state.active_nct_id = None
        
        if metastasis.strip():
            search_term = f"{diagnosis} {metastasis}"
        else:
            search_term = diagnosis

        with st.spinner(f"Connecting to ClinicalTrials.gov for '{search_term}'..."):
            data = fetch_clinical_trials(search_term)
            st.session_state.studies = data.get('studies', [])
            
        st.rerun()

# --- RESULTS DISPLAY ---
trials = st.session_state.studies

if not trials:
    if st.session_state.search_performed:
        st.warning("No recruiting trials found. Try broadening your search.")
    else:
        st.info("👆 Expand the search panel above to begin.")

else:
    # Stats Bar with Elegant Styling
    col1, col2, col3 = st.columns(3)
    col1.metric("Trials Found", len(trials))
    col2.metric("Status", "Recruiting")
    col3.metric("Source", "ClinicalTrials.gov")
    
    spacer(20)
    
    # Results Loop
    for trial in trials:
        protocol = trial.get('protocolSection', {})
        id_module = protocol.get('identificationModule', {})
        summary_module = protocol.get('descriptionModule', {})
        eligibility_module = protocol.get('eligibilityModule', {})
        
        nct_id = id_module.get('nctId', 'N/A')
        title = id_module.get('briefTitle', 'No Title')
        summary = summary_module.get('briefSummary', 'No summary available')
        criteria = eligibility_module.get('eligibilityCriteria', 'Criteria not listed.')

        should_be_expanded = (nct_id == st.session_state.active_nct_id)

        with st.expander(f"{title}", expanded=should_be_expanded):
            # Header Row inside Card
            st.markdown(f"""
            <div style="margin-bottom: 15px; display: flex; align-items: center;">
                <span class="status-badge">Recruiting</span> 
                <span style="margin-left: 15px; color: #94a3b8; font-family: monospace; font-size: 0.9em;">{nct_id}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### Study Summary")
            st.write(summary)
            
            spacer(10)
            st.markdown("---")
            spacer(10)
            
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("#### ⚠️ Eligibility Criteria")
                st.text_area("Raw Data", criteria, height=200, disabled=True, key=f"crit_{nct_id}")
            
            with c2:
                st.markdown("#### 🤖 AI Analysis")
                
                existing_result = st.session_state.analysis_results.get(nct_id)
                
                if existing_result:
                    if "Status: Match" in existing_result:
                        st.success(existing_result)
                    elif "Status: No Match" in existing_result:
                        st.error(existing_result)
                    else:
                        st.warning(existing_result)
                else:
                    st.info("AI Analysis ready. Click to verify eligibility.")
                
                if st.button(f"Analyze Match for {nct_id}", key=f"btn_{nct_id}"):
                    
                    age_str = str(age) if age else "Unknown"
                    sex_str = sex if sex != "Select..." else "Unknown"
                    
                    profile_str = f"Age: {age_str}, Sex: {sex_str}, Diagnosis: {diagnosis}, Metastasis: {metastasis}"
                    if kras: profile_str += ", KRAS Wild-type"
                    
                    with st.spinner("Analyzing criteria against your profile..."):
                        ai_result = analyze_trial_eligibility(criteria, profile_str)
                    
                    st.session_state.analysis_results[nct_id] = ai_result
                    st.session_state.active_nct_id = nct_id 
                    st.rerun()
                
                st.markdown(f"<div style='margin-top: 15px; text-align: right;'><a href='https://clinicaltrials.gov/study/{nct_id}' target='_blank' style='color: #818cf8; text-decoration: none; font-weight: 600;'>View Official Record ↗</a></div>", unsafe_allow_html=True)
