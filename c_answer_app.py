import streamlit as st
import requests
from fpdf import FPDF
from ai_agent import analyze_trial_eligibility, generate_treatment_report

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
	
	/* Tabs Styling */
	.stTabs [data-baseweb="tab-list"] { gap: 24px; }
	.stTabs [data-baseweb="tab"] {
		height: 50px;
		white-space: pre-wrap;
		background-color: transparent;
		border-radius: 4px 4px 0px 0px;
		gap: 1px;
		padding-top: 10px;
		padding-bottom: 10px;
		font-family: 'Lato', sans-serif;
		font-weight: 600;
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

def create_pdf(saved_trials, patient_info):
	"""Generates a PDF report of saved trials."""
	pdf = FPDF()
	pdf.add_page()
	pdf.set_font("Arial", 'B', 16)
	pdf.cell(0, 10, "C-Answer: Clinical Trial Report", ln=True, align='C')
	pdf.ln(10)
	
	pdf.set_font("Arial", 'I', 12)
	pdf.multi_cell(0, 10, f"Patient Profile: {patient_info}")
	pdf.ln(10)
	
	pdf.set_font("Arial", 'B', 14)
	pdf.cell(0, 10, "Selected Trials for Review:", ln=True)
	pdf.ln(5)
	
	for nct_id, details in saved_trials.items():
		pdf.set_font("Arial", 'B', 12)
		pdf.cell(0, 10, f"{details['title']} ({nct_id})", ln=True)
		
		pdf.set_font("Arial", '', 10)
		# Clean text to remove unicode characters that break FPDF
		clean_summary = details['summary'].encode('latin-1', 'replace').decode('latin-1')
		pdf.multi_cell(0, 6, clean_summary[:500] + "...")
		pdf.ln(5)
		
		if details.get('match_status'):
			pdf.set_font("Arial", 'B', 10)
			pdf.cell(0, 6, f"AI Analysis: {details['match_status']}", ln=True)
		
		pdf.ln(10)
		
	return pdf.output(dest='S').encode('latin-1')

def fetch_clinical_trials(condition, status="RECRUITING"):
	base_url = "https://clinicaltrials.gov/api/v2/studies"
	params = {
		"query.cond": condition,
		"filter.overallStatus": status,
		"pageSize": 40,
		"sort": "LastUpdateSubmitDate"
	}
	try:
		response = requests.get(base_url, params=params)
		response.raise_for_status()
		return response.json()
	except Exception:
		return {}

# --- STATE MANAGEMENT ---
if 'studies' not in st.session_state: st.session_state.studies = []
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = {}
if 'saved_trials' not in st.session_state: st.session_state.saved_trials = {}
if 'treatment_report' not in st.session_state: st.session_state.treatment_report = ""
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
	# SEARCH PANEL
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
			st.session_state.analysis_results = {} # Reset AI results on new search
			
			# Save profile string for report
			age_s = str(age) if age else "Unknown"
			sex_s = sex if sex != "Select..." else "Unknown"
			st.session_state.patient_profile_str = f"{age_s}, {sex_s}, {diagnosis}, Mets: {metastasis}"
			
			search_term = f"{diagnosis} {metastasis}" if metastasis.strip() else diagnosis
			
			with st.spinner(f"Scanning ClinicalTrials.gov for '{search_term}'..."):
				data = fetch_clinical_trials(search_term)
				st.session_state.studies = data.get('studies', [])
				# Also generate treatment report in background
				biomarkers = "KRAS Wild-type" if kras else "None specified"
				st.session_state.treatment_report = generate_treatment_report(diagnosis, metastasis, biomarkers)
			
			st.rerun()

	# RESULTS LIST
	trials = st.session_state.studies
	if trials:
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
					# AI ANALYSIS
					existing_res = st.session_state.analysis_results.get(nct_id)
					if existing_res:
						if "Status: Match" in existing_res: st.success(existing_res)
						elif "Status: No Match" in existing_res: st.error(existing_res)
						else: st.warning(existing_res)
					else:
						st.info("AI Analysis ready.")
					
					b1, b2 = st.columns(2)
					with b1:
						if st.button("Analyze", key=f"btn_{nct_id}"):
							with st.spinner("Analyzing..."):
								res = analyze_trial_eligibility(criteria, st.session_state.patient_profile_str)
								st.session_state.analysis_results[nct_id] = res
								st.rerun()
					with b2:
						# SAVE BUTTON
						if nct_id in st.session_state.saved_trials:
							st.button("Saved ✅", disabled=True, key=f"save_{nct_id}")
						else:
							if st.button("Save ⭐", key=f"save_{nct_id}"):
								# Save trial details to session state
								st.session_state.saved_trials[nct_id] = {
									"title": title,
									"summary": summary,
									"match_status": st.session_state.analysis_results.get(nct_id, "Not Analyzed")
								}
								st.rerun()

# ==========================================
# TAB 2: TREATMENT LANDSCAPE (Advanced Data)
# ==========================================
with tab_insights:
	if st.session_state.treatment_report:
		st.info(f"AI-Generated Landscape for: **{st.session_state.patient_profile_str}**")
		st.markdown(st.session_state.treatment_report)
		st.caption("Source: AI Synthesis of General Medical Knowledge (Llama 3.3). Verify with NCCN Guidelines.")
	else:
		st.write("👈 Perform a search in the 'Trial Search' tab to generate a treatment landscape report.")

# ==========================================
# TAB 3: SAVED REPORT
# ==========================================
with tab_saved:
	saved = st.session_state.saved_trials
	if saved:
		st.success(f"You have saved {len(saved)} trials.")
		
		# PDF DOWNLOAD
		pdf_bytes = create_pdf(saved, st.session_state.patient_profile_str)
		st.download_button(
			label="📄 Download PDF Report for Doctor",
			data=pdf_bytes,
			file_name="C-Answer_Report.pdf",
			mime="application/pdf",
			type="primary"
		)
		
		st.markdown("---")
		for nid, det in saved.items():
			st.markdown(f"**{det['title']}**")
			st.caption(f"ID: {nid} | Status: {det['match_status']}")
			if st.button(f"Remove {nid}", key=f"rem_{nid}"):
				del st.session_state.saved_trials[nid]
				st.rerun()
	else:
		st.info("You haven't saved any trials yet. Click the 'Save ⭐' button on trials in the Search tab.")
