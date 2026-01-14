import streamlit as st
import requests
import pgeocode
import pandas as pd
import math
import unicodedata
from fpdf import FPDF
from pypdf import PdfReader
from ai_agent import analyze_trial_eligibility, generate_treatment_report, compare_trials, extract_patient_data

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
    
    html, body, [class*="css"] { 
        font-family: 'Lato', sans-serif; 
    }
    
    h1, h2, h3 { 
        font-family: 'Playfair Display', serif; 
    }
    
    [data-testid="InputInstructions"] { 
        display: none !important; 
    }
    
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
    
    .distance-badge {
        background-color: rgba(96, 165, 250, 0.1); 
        color: #93C5FD; 
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid rgba(96, 165, 250, 0.3);
        margin-left: 10px;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    
    .distance-badge:hover {
        background-color: rgba(96, 165, 250, 0.25);
        color: #ffffff;
        border-color: #60A5FA;
    }
    
    .section-header {
        margin-top: 30px;
        margin-bottom: 15px;
        font-size: 1.2rem;
        font-weight: 600;
        color: #94a3b8;
        border-bottom: 1px solid #334155;
        padding-bottom: 5px;
    }
    
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        margin-top: 10px;
    }

    .footer-note {
        font-size: 0.8rem;
        color: #94a3b8;
        text-align: center;
        margin-top: 50px;
        border-top: 1px solid #334155;
        padding-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def spacer(height=20):
    st.markdown(f"<div style='height: {height}px'></div>", unsafe_allow_html=True)

def clean_text(text):
    """Aggressive ASCII cleaning to prevent PDF encoding errors."""
    if not text:
        return ""
    
    text = text.replace('\u00A0', ' ').replace('\u200B', '')
    
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2022': '-', '•': '-',
        '\u2026': '...', '–': '-'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    text = text.replace('###', '').replace('##', '').replace('#', '').replace('**', '').replace('__', '')
    
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def calculate_nearest_site(user_zip, locations):
    if not user_zip or not locations:
        return None, None, None, None, None
    try:
        dist = pgeocode.GeoDistance('us')
        min_km = float('inf')
        nearest_loc = None
        for loc in locations:
            if loc.get('country') != 'United States':
                continue
            site_zip = loc.get('zip')
            if site_zip:
                clean_zip = str(site_zip)[:5]
                d_km = dist.query_postal_code(user_zip, clean_zip)
                if d_km is not None and not pd.isna(d_km) and d_km < min_km:
                    min_km = d_km
                    nearest_loc = loc
                    
        if nearest_loc and min_km != float('inf'):
            miles = int(min_km * 0.621371)
            facility = nearest_loc.get('facility', 'Study Site')
            city = nearest_loc.get('city', '')
            state = nearest_loc.get('state', '')
            zip_code = nearest_loc.get('zip', '')
            query = f"{facility}, {city}, {state} {zip_code}".replace(" ", "+")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={query}"
            return miles, facility, city, state, maps_url
    except Exception:
        return None, None, None, None, None
    return None, None, None, None, None

def create_pdf(saved_trials, patient_info, treatment_report, comparison_report):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 10, "C-Answer", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, "Intelligent Clinical Trial & Recovery Plan", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Patient Profile Summary:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 5, clean_text(patient_info))
    pdf.ln(8)
    
    if treatment_report:
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "1. Treatment Landscape", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        for line in treatment_report.split('\n'):
            line = clean_text(line).strip()
            if not line:
                continue
            if pdf.get_y() > 265:
                pdf.add_page()
            if (len(line) < 60 and not line.endswith('.') and not line.startswith('-')):
                pdf.ln(4)
                pdf.set_font("Arial", 'B', 11)
                pdf.multi_cell(0, 6, line)
            else:
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 6, line)
        pdf.ln(10)
        
    if comparison_report:
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "2. AI Comparison of Selected Trials", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 6, clean_text(comparison_report))
        pdf.ln(10)
        
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "3. Trial Details", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    for nct_id, details in saved_trials.items():
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_text_color(0, 51, 102)
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 6, f"{clean_text(details['title'])}")
        pdf.set_text_color(100, 100, 100)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"Trial ID: {nct_id}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 5, clean_text(details['summary'][:1000]) + "...")
        pdf.ln(3)
        if details.get('match_status'):
            if pdf.get_y() > 260:
                pdf.add_page()
            pdf.set_fill_color(245, 255, 250)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, "AI Match Analysis:", ln=True, fill=True)
            pdf.set_font("Arial", '', 10)
            status_text = details['match_status'].replace("Status: ", "")
            pdf.multi_cell(0, 5, clean_text(status_text), fill=True)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

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
    except Exception:
        return {}

def render_trial_card(trial):
    protocol = trial.get('protocolSection', {})
    id_mod = protocol.get('identificationModule', {})
    desc_mod = protocol.get('descriptionModule', {})
    elig_mod = protocol.get('eligibilityModule', {})
    nct_id = id_mod.get('nctId', 'N/A')
    title = id_mod.get('briefTitle', 'No Title')
    summary = desc_mod.get('briefSummary', 'No summary.')
    criteria = elig_mod.get('eligibilityCriteria', 'Not listed.')
    dist_data = trial.get('_dist_data')
    if dist_data:
        fac_name = dist_data['facility'][:30]
        dist_str = f"<a href='{dist_data['url']}' target='_blank' class='distance-badge'>📍 {fac_name}... ({dist_data['miles']} mi)</a>"
    else:
        dist_str = ""
    with st.expander(f"{title}"):
        st.markdown(f"""
            <div style='margin-bottom: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px;'>
                <span class='status-badge'>Recruiting</span> 
                <span style='color:#94a3b8; font-family: monospace;'>{nct_id}</span>
                {dist_str}
            </div>
            """, unsafe_allow_html=True)
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
                if "Status: Match" in existing_res: 
                    st.success(existing_res)
                elif "Status: No Match" in existing_res: 
                    st.error(existing_res)
                else: 
                    st.warning(existing_res)
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
                            "title": title, "summary": summary, "match_status": st.session_state.analysis_results.get(nct_id, "Not Analyzed")
                        }
                        st.rerun()

# --- INITIALIZATION ---
if 'studies' not in st.session_state:
    st.session_state.studies = []
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'saved_trials' not in st.session_state:
    st.session_state.saved_trials = {}
if 'treatment_report' not in st.session_state:
    st.session_state.treatment_report = ""
if 'comparison_report' not in st.session_state:
    st.session_state.comparison_report = ""
if 'patient_profile_str' not in st.session_state:
    st.session_state.patient_profile_str = ""
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'user_zip' not in st.session_state:
    st.session_state.user_zip = ""
if 'form_diagnosis' not in st.session_state:
    st.session_state.form_diagnosis = ""
if 'form_metastasis' not in st.session_state:
    st.session_state.form_metastasis = ""
if 'form_age' not in st.session_state:
    st.session_state.form_age = None
if 'form_sex' not in st.session_state:
    st.session_state.form_sex = "Select..."
if 'form_kras' not in st.session_state:
    st.session_state.form_kras = False
if 'form_ecog' not in st.session_state:
    st.session_state.form_ecog = "0 - Fully Active"
if 'form_lines' not in st.session_state:
    st.session_state.form_lines = "None (1st Line)"
if 'form_msi' not in st.session_state:
    st.session_state.form_msi = "Unknown"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ℹ️ Application Context")
    st.markdown("""
        **C-Answer v1.0**
        
        **AI Engine:** Llama 3.3 (Groq API).
        
        **Data Source:** ClinicalTrials.gov Modernized REST API.
        """)

# --- MAIN HEADER ---
st.markdown("<div style='display: flex; align-items: center; margin-bottom: 20px;'><div style='font-size: 4rem; margin-right: 20px; line-height: 1;'>🎗️</div><div><h1 style='margin: 0; padding: 0; font-size: 3.5rem; line-height: 1.2;'>C-Answer</h1><p style='margin: 5px 0 0 0; opacity: 0.8; font-size: 1.1rem;'>Intelligent Clinical Trial Matching & Recovery Planning</p></div></div>", unsafe_allow_html=True)

tab_search, tab_insights, tab_saved, tab_roadmap = st.tabs(["🔍 Trial Search", "📊 Treatment Landscape", "📁 Saved Report", "🚀 Future Roadmap"])

with tab_search:
    is_expanded = not st.session_state.search_performed
    with st.expander("📄 Auto-Fill from Medical Records (Optional)", expanded=is_expanded):
        uploaded_files = st.file_uploader("Upload Pathology Reports (PDF)", type="pdf", accept_multiple_files=True)
        if uploaded_files and st.button("🚀 Extract Data from Files"):
            with st.spinner("Extracting patient data..."):
                try:
                    all_text = ""
                    for pdf_file in uploaded_files:
                        reader = PdfReader(pdf_file)
                        for page in reader.pages:
                            all_text += page.extract_text() + "\n"
                    ext = extract_patient_data(all_text)
                    if ext:
                        st.session_state.form_diagnosis = ext.get("diagnosis", "")
                        st.session_state.form_metastasis = ext.get("metastasis", "")
                        e_age = ext.get("age", None)
                        st.session_state.form_age = int(e_age) if e_age and str(e_age).isdigit() else None
                        st.session_state.form_sex = ext.get("sex", "Select...")
                        st.session_state.form_kras = ext.get("kras_wild_type", False)
                        st.session_state.form_ecog = ext.get("ecog", "0 - Fully Active")
                        st.session_state.form_lines = ext.get("prior_lines", "None (1st Line)")
                        st.session_state.form_msi = ext.get("msi", "Unknown")
                        st.success(f"✅ Extracted profile data from documents!")
                        st.rerun()
                except Exception as e: 
                    st.error(f"Error processing records: {e}")

    with st.expander("Configure Patient Profile", expanded=is_expanded):
        with st.form("patient_form"):
            diagnosis = st.text_input("Primary Condition", value=st.session_state.form_diagnosis, placeholder="e.g. Colorectal Cancer")
            metastasis = st.text_input("Metastasis Location", value=st.session_state.form_metastasis, placeholder="e.g. Liver, Lung")
            c1, c2, c3 = st.columns(3)
            with c1: 
                age = st.number_input("Age", value=st.session_state.form_age, placeholder="e.g. 35", step=1)
            with c2: 
                sex = st.selectbox("Sex", ["Select...", "Male", "Female"], index=0 if st.session_state.form_sex == "Select..." else (1 if st.session_state.form_sex=="Male" else 2))
            with c3: 
                zip_input = st.text_input("Zip Code (Optional)", max_chars=5, placeholder="e.g. 90210", value=st.session_state.user_zip)
            st.write("**Clinical Details**")
            c4, c5, c6 = st.columns(3)
            with c4: 
                ecog = st.selectbox("ECOG Performance", ["0 - Fully Active", "1 - Restricted", "2 - Ambulatory", "3 - Limited", "4 - Bedridden"], index=0)
            with c5: 
                lines = st.selectbox("Prior Lines of Therapy", ["None (1st Line)", "1 Prior Line", "2 Prior Lines", "3+ Prior Lines"], index=0)
            with c6: 
                msi = st.selectbox("MSI/MMR Status", ["Unknown", "MSS (Stable)", "MSI-High (Instable)"], index=0)
            st.write("**Biomarkers & Filters**")
            c7, c8, _ = st.columns([1, 1, 2])
            with c7: 
                kras = st.checkbox("KRAS Wild-type", value=st.session_state.form_kras)
            with c8: 
                phase1 = st.checkbox("Exclude Phase 1", value=False)
            spacer(20)
            submitted = st.form_submit_button("Find Matching Trials", type="primary")

    if submitted:
        if not diagnosis.strip(): 
            st.warning("⚠️ Please enter a diagnosis.")
        else:
            st.session_state.search_performed = True
            st.session_state.analysis_results = {}
            st.session_state.comparison_report = ""
            st.session_state.user_zip = zip_input
            st.session_state.form_diagnosis = diagnosis
            st.session_state.form_metastasis = metastasis
            st.session_state.form_age = age
            st.session_state.form_sex = sex
            st.session_state.form_kras = kras
            st.session_state.form_ecog = ecog
            st.session_state.form_lines = lines
            st.session_state.form_msi = msi
            
            p_age = age or "Unknown"
            p_sex = sex if sex != "Select..." else "Unknown"
            p_zip = zip_input or "N/A"
            st.session_state.patient_profile_str = f"Age: {p_age}, Sex: {p_sex}, Zip: {p_zip}\nDiagnosis: {diagnosis}\nMetastasis: {metastasis}\nPerformance: {ecog}\nPrior Therapy: {lines}\nMSI: {msi}\nKRAS: {'Wild-type' if kras else 'Unknown/Mutant'}"
            
            with st.spinner("Scanning ClinicalTrials.gov..."):
                search_q = f"{diagnosis} {metastasis}" if metastasis.strip() else diagnosis
                raw = fetch_clinical_trials(search_q).get('studies', [])
                processed = []
                for s in raw:
                    dm, dd = float('inf'), None
                    if zip_input:
                        locs = s.get('protocolSection', {}).get('contactsLocationsModule', {}).get('locations', [])
                        miles, fac, city, state, url = calculate_nearest_site(zip_input, locs)
                        if miles is not None: 
                            dm, dd = miles, {"miles": miles, "facility": fac, "city": city, "state": state, "url": url}
                    s['_sort_distance'], s['_dist_data'] = dm, dd
                    processed.append(s)
                if zip_input: 
                    processed.sort(key=lambda x: x['_sort_distance'])
                st.session_state.studies = processed
                st.session_state.treatment_report = generate_treatment_report(st.session_state.patient_profile_str)
            st.rerun()

    if st.session_state.studies:
        trials = st.session_state.studies
        if st.session_state.user_zip:
            scored = [t for t in trials if t['_sort_distance'] != float('inf')]
            unscored = [t for t in trials if t['_sort_distance'] == float('inf')]
            if scored:
                st.markdown(f"<div class='section-header'>📍 Nearest to You ({len(scored)})</div>", unsafe_allow_html=True)
                for t in scored: 
                    render_trial_card(t)
            if unscored:
                st.markdown(f"<div class='section-header'>🌎 Other Recruiting Trials ({len(unscored)})</div>", unsafe_allow_html=True)
                for t in unscored: 
                    render_trial_card(t)
        else:
            st.markdown(f"**Found {len(trials)} recruiting trials**")
            for t in trials: 
                render_trial_card(t)

with tab_insights:
    if st.session_state.treatment_report:
        st.info(f"🧠 AI-Generated Landscape for: **{st.session_state.form_diagnosis}** (Personalized)")
        st.warning("⚠️ **DISCLAIMER:** Educational purposes only. Not medical advice.")
        st.markdown(st.session_state.treatment_report)
    else:
        st.write("👈 Perform a search to generate report.")

with tab_saved:
    saved = st.session_state.saved_trials
    st.markdown("### 📁 Saved Trials Report")
    if saved:
        st.success(f"You have saved {len(saved)} trials.")
        if len(saved) > 1 and st.button("⚖️ Compare Selected Trials (AI)", type="primary"):
            with st.spinner("Comparing..."):
                st.session_state.comparison_report = compare_trials(saved)
                st.rerun()
        if st.session_state.comparison_report:
            st.markdown("---")
            st.markdown("#### ⚖️ AI Comparison Matrix")
            st.markdown(st.session_state.comparison_report)
            st.markdown("---")
        pdf_bytes = create_pdf(saved, st.session_state.patient_profile_str, st.session_state.treatment_report, st.session_state.comparison_report)
        st.download_button(label="📄 Download PDF Report for Doctor", data=pdf_bytes, file_name="C-Answer_Report.pdf", mime="application/pdf")
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

with tab_roadmap:
    st.markdown("### 🚀 C-Answer: Phase 2 Roadmap")
    st.write("Our current MVP focuses on intelligent search and analysis. Phase 2 will focus on deep data integration and proactive monitoring.")
    
    with st.expander("💊 Feature 1: Drug Interaction Safety Check (OpenFDA)", expanded=True):
        st.markdown("""
        **The Problem:** Patients are terrified that trial drugs will interfere with their current medications (e.g., blood pressure, diabetes meds).
        
        **The Solution:** We will connect to the **OpenFDA API**. Patients will input their current medication list, and C-Answer will automatically flag potential contraindications against the trial protocol *before* they apply.
        """)

    with st.expander("📚 Feature 2: \"True\" Live RAG Database", expanded=True):
        st.markdown("""
        **The Problem:** LLM training data cuts off. If guidelines change tomorrow, the AI might not know.
        
        **The Solution:** Instead of relying solely on the model's training, we will implement a **Vector Database (e.g., Pinecone)**. We will ingest live PDFs of NCCN guidelines daily. The AI will retrieve the exact, most current page before generating its landscape report.
        """)
        
    with st.expander("⏰ Feature 3: 24/7 \"Tireless\" Monitor & Alert System", expanded=True):
        st.markdown("""
        **The Problem:** Patients have to manually log in and search every week. Oncologists are too busy to do it for them.
        
        **The Solution:** We will transition from on-demand search to active monitoring. Cloud functions will run the patient's specific query every 24 hours and **email alert** them immediately when a new matching trial opens near their zipcode.
        """)

# --- MAIN FOOTER ---
st.markdown("<div class='footer-note'>🔒 <b>Privacy Notice:</b> C-Answer is a local-first session-based tool. No patient data or biomarker results are stored on our servers. Closing this tab permanently clears all information.</div>", unsafe_allow_html=True)
