import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from ai_agent import analyze_trial_eligibility, generate_treatment_report, compare_trials

# --- CONFIGURATION ---
st.set_page_config(
    page_title="C-Answer", 
    page_icon="🎗️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Playfair+Display:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Lato', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; }
    
    [data-testid="InputInstructions"] { display: none !important; }
    
    div.stExpander {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        margin-bottom: 16px;
        background-color: #1E293B !important; 
    }
    
    .status-badge {
        background-color: rgba(16, 185, 129, 0.1); 
        color: #6EE7B7; 
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    div.stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def spacer(height=20):
    st.markdown(f"<div style='height: {height}px'></div>", unsafe_allow_html=True)

def clean_text(text):
    if not text: return ""
    text = text.replace('###', '').replace('##', '').replace('#', '').replace('**', '').replace('__', '')
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-', '\u2022': '*', '\u2026': '...'}
    for char, replacement in replacements.items(): text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf(saved_trials, patient_info, treatment_report, comparison_report):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 10, "C-Answer", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, "Intelligent Clinical Trial & Recovery Plan", ln=True, align='C')
    pdf.ln(10)
    
    # Profile
    pdf.set_fill_color(240, 240, 240) 
    pdf.rect(10, pdf.get_y(), 190, 20, 'F') 
    pdf.set_xy(12, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.write(6, "Patient Profile: ")
    pdf.set_font("Arial", '', 12)
    pdf.write(6, clean_text(patient_info))
    pdf.ln(20)
    
    # 1. Landscape
    if treatment_report:
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "1. Treatment Landscape", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()) 
        pdf.ln(5)
        lines = treatment_report.split('\n')
        for line in lines:
            line = clean_text(line).strip()
            if not line: continue
            if (len(line) < 60 and not line.endswith('.') and not line.startswith('*')):
                pdf.ln(6)
                pdf.set_font("Arial", 'B', 11)
                pdf.multi_cell(0, 6, line)
            else:
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 6, line)
        pdf.ln(10)
        
    # 2. Comparison Table (Simplified for PDF)
    if comparison_report:
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "2. AI Comparison of Selected Trials", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()) 
        pdf.ln(5)
        pdf.set_font("Arial", '', 10)
        # We just dump the markdown text for now as tables in FPDF are complex
        pdf.multi_cell(0, 6, clean_text(comparison_report))
        pdf.ln(10)
        
    # 3. Trial Details
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "3. Trial Details", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) 
    pdf.ln(5)
    
    for nct_id, details in saved_trials.items():
        pdf.set_text_color(0, 51, 102) 
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 8, f"{clean_text(details['title'])}")
        pdf.set_text_color(100, 100, 100)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"Trial ID: {nct_id}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 6, clean_text(details['summary'][:1000]) + "...") 
        pdf.ln(8)
        
    return pdf.output(dest='S').encode('latin-1')

def fetch_clinical_trials(condition, status="RECRUITING"):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": 50, # Increased for better charts
        "sort": "LastUpdateSubmitDate"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}

# --- VISUAL ANALYTICS FUNCTION ---
def display_analytics(studies):
    if not studies: return

    # Extract Data for Charts
    phases = []
    sponsors = []
    
    for study in studies:
        protocol = study.get('protocolSection', {})
        design = protocol.get('designModule', {})
        ident = protocol.get('identificationModule', {})
        
        # Get Phase
        phase_list = design.get('phases', ['Not Specified'])
        phases.append(phase_list[0] if phase_list else 'Not Specified')
        
        # Get Sponsor Class
        org = ident.get('organization', {})
        sponsors.append(org.get('class', 'Unknown'))
    
    # Create DataFrames
    df_phase = pd.DataFrame(phases, columns=["Phase"])
    df_sponsor = pd.DataFrame(sponsors, columns=["Sponsor"])
    
    # Display Charts
    st.markdown("### 📊 Market Intelligence")
    c1, c2 = st.columns(2)
    
    with c1:
        st.caption("Distribution by Trial Phase")
        # Simple bar chart of counts
        st.bar_chart(df_phase['Phase'].value_counts())
        
    with c2:
        st.caption("Sponsorship (Industry vs. Public)")
        st.bar_chart(df_sponsor['Sponsor'].value_counts())
    
    spacer(20)

# --- STATE MANAGEMENT ---
if 'studies' not in st.session_state: st.session_state.studies = []
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = {}
if 'saved_trials' not in st.session_state: st.session_state.saved_trials = {}
if 'treatment_report' not in st.session_state: st.session_state.treatment_report = ""
if 'comparison_report' not in st.session_state: st.session_state.comparison_report = ""
if 'patient_profile_str' not in st.session_state: st.session_state.patient_profile_str = ""
if 'search_performed' not in st.session_state: st.session_state.search_performed = False

# --- HEADER ---
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 20px;">
    <div style="font-size: 4rem; margin-right: 20px; line-height: 1;">🎗️</div>
    <div>
        <h1 style="margin: 0; padding: 0; font-size: 3.5rem; line-height: 1.2;">C-Answer</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 1.1rem;">Intelligent Clinical Trial Matching & Recovery Planning</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- TABS LAYOUT ---
tab_search, tab_insights, tab_saved = st.tabs(["🔍 Trial Search", "📊 Treatment Landscape", "📁 Saved Report"])

# ==========================================
# TAB 1: SEARCH
# ==========================================
with tab_search:
    is_expanded = not st.session_state.search_performed
    with st.expander("Configure Patient Profile", expanded=is_expanded):
        with st.form("patient_form"):
            diagnosis = st.text_input("Primary Condition", value="", placeholder="e.g. Colorectal Cancer")
            metastasis = st.text_input("Metastasis Location", value="", placeholder="e.g. Liver, Lung")
            
            c1, c2 = st.columns(2)
            with c1: age = st.number_input("Age", value=None, placeholder="e.g. 35", step=1)
            with c2: sex = st.selectbox("Sex", ["Select...", "Male", "Female"])
            
            st.write("**Biomarkers & Filters**")
            c3, c4 = st.columns(2)
            with c3: kras = st.checkbox("KRAS Wild-type", value=False)
            with c4: phase1 = st.checkbox("Exclude Phase 1", value=False)
            
            spacer(10)
            submitted = st.form_submit_button("Find Matching Trials", type="primary")

    if submitted:
        if not diagnosis.strip():
            st.warning("⚠️ Please enter a diagnosis.")
        else:
            st.session_state.search_performed = True
            st.session_state.analysis_results = {}
            st.session_state.comparison_report = "" # Reset comparison
            
            age_s = str(age) if age else "Unknown"
            sex_s = sex if sex != "Select..." else "Unknown"
            st.session_state.patient_profile_str = f"{age_s}, {sex_s}, {diagnosis}, Mets: {metastasis}"
            
            search_term = f"{diagnosis} {metastasis}" if metastasis.strip() else diagnosis
            
            with st.spinner(f"Scanning ClinicalTrials.gov for '{search_term}'..."):
                data = fetch_clinical_trials(search_term)
                st.session_state.studies = data.get('studies', [])
                
                biomarkers = "KRAS Wild-type" if kras else "None specified"
                st.session_state.treatment_report = generate_treatment_report(diagnosis, metastasis, biomarkers)
            
            st.rerun()

    # ANALYTICS & RESULTS
    trials = st.session_state.studies
    if trials:
        # SHOW CHARTS
        display_analytics(trials)
        
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"**Found {len(trials)} recruiting trials**")
        
        for trial in trials:
            protocol = trial.get('protocolSection', {})
            id_mod = protocol.get('identificationModule', {})
            desc_mod = protocol.get('descriptionModule', {})
            elig_mod = protocol.get('eligibilityModule', {})
            
            nct_id = id_mod.get('nctId', 'N/A')
            title = id_mod.get('briefTitle', 'No Title')
            summary = desc_mod.get('briefSummary', 'No summary.')
            criteria = elig_mod.get('eligibilityCriteria', 'Not listed.')
            
            with st.expander(f"{title}"):
                st.markdown(f"<span class='status-badge'>Recruiting</span> <span style='color:#94a3b8; margin-left:10px;'>{nct_id}</span>", unsafe_allow_html=True)
                st.write(summary)
                st.markdown("---")
                
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.caption("Eligibility Criteria")
                    st.text_area("Raw Data", criteria, height=150, disabled=True, key=f"crit_{nct_id}")
                with c2:
                    st.markdown("#### 🧠 AI Analysis")
                    existing_res = st.session_state.analysis_results.get(nct_id)
                    if existing_res:
                        if "Status: Match" in existing_res: st.success(existing_res)
                        elif "Status: No Match" in existing_res: st.error(existing_res)
                        else: st.warning(existing_res)
                    else:
                        st.info("Ready to analyze.")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Analyze", key=f"btn_{nct_id}"):
                            with st.spinner("Analyzing..."):
                                res = analyze_trial_eligibility(criteria, st.session_state.patient_profile_str)
                                st.session_state.analysis_results[nct_id] = res
                                st.rerun()
                    with b2:
                        if nct_id in st.session_state.saved_trials:
                            st.button("Saved ✅", disabled=True, key=f"save_{nct_id}")
                        else:
                            if st.button("Save ⭐", key=f"save_{nct_id}"):
                                st.session_state.saved_trials[nct_id] = {
                                    "title": title,
                                    "summary": summary,
                                    "match_status": st.session_state.analysis_results.get(nct_id, "Not Analyzed")
                                }
                                st.rerun()

# ==========================================
# TAB 2: TREATMENT LANDSCAPE
# ==========================================
with tab_insights:
    if st.session_state.treatment_report:
        st.info(f"🧠 AI-Generated Landscape for: **{st.session_state.patient_profile_str}**")
        st.markdown(st.session_state.treatment_report)
        st.caption("Source: AI Synthesis of General Medical Knowledge (Llama 3.3). Verify with NCCN Guidelines.")
    else:
        st.write("👈 Perform a search in the 'Trial Search' tab to generate a treatment landscape report.")

# ==========================================
# TAB 3: SAVED REPORT & COMPARATOR
# ==========================================
with tab_saved:
    saved = st.session_state.saved_trials
    
    st.markdown("### 📁 Saved Trials Report")

    if saved:
        st.success(f"You have saved {len(saved)} trials.")
        
        # COMPARATOR BUTTON
        if len(saved) > 1:
            if st.button("⚖️ Compare Selected Trials (AI)", type="primary"):
                with st.spinner("Generating comparison matrix..."):
                    st.session_state.comparison_report = compare_trials(saved)
        
        # DISPLAY COMPARISON IF EXISTS
        if st.session_state.comparison_report:
            st.markdown("---")
            st.markdown("#### ⚖️ AI Comparison Matrix")
            st.markdown(st.session_state.comparison_report)
            st.markdown("---")

        # PDF DOWNLOAD
        pdf_bytes = create_pdf(
            saved, 
            st.session_state.patient_profile_str, 
            st.session_state.treatment_report,
            st.session_state.comparison_report
        )
        
        st.download_button(
            label="📄 Download PDF Report for Doctor",
            data=pdf_bytes,
            file_name="C-Answer_Report.pdf",
            mime="application/pdf"
        )
        
        st.markdown("---")
        for nid, det in saved.items():
            st.markdown(f"**{det['title']}**")
            st.caption(f"ID: {nid} | Status: {det['match_status']}")
            if st.button(f"Remove {nid}", key=f"rem_{nid}"):
                del st.session_state.saved_trials[nid]
                st.rerun()
    else:
        st.info("Your shortlist is currently empty.")
        st.markdown("""
        #### How to create your report:
        1. Go to the **🔍 Trial Search** tab.
        2. Run a search for your condition.
        3. Click the **Save ⭐** button on any trial.
        4. Return here to compare them side-by-side.
        """)
