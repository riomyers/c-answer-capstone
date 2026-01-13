import streamlit as st
import requests
from ai_agent import analyze_trial_eligibility 

# --- CONFIGURATION ---
st.set_page_config(
	page_title="C-Answer", 
	page_icon="🎗️", 
	layout="wide",
	initial_sidebar_state="expanded"
)

# --- MINIMAL CSS (Layout Only) ---
st.markdown("""
<style>
	@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
	html, body, [class*="css"] {
		font-family: 'Inter', sans-serif;
	}
	
	/* Hide the annoying 'Press Enter to Apply' text */
	[data-testid="InputInstructions"] {
		display: none !important;
	}
	
	/* Card Styling */
	div.stExpander {
		border: 1px solid #334155; 
		border-radius: 12px;
		margin-bottom: 16px;
	}
	
	/* Custom Badges */
	.status-badge {
		background-color: #064E3B; 
		color: #6EE7B7; 
		padding: 4px 12px;
		border-radius: 20px;
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		border: 1px solid #059669;
	}
	
	/* Button Styling */
	div.stButton > button {
		background: #4F46E5; 
		color: white;
		border: none;
		padding: 0.6rem 1.2rem;
		border-radius: 8px;
		font-weight: 600;
		width: 100%;
		margin-top: 10px;
	}
	div.stButton > button:hover {
		background-color: #4338ca;
		color: white;
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

# --- SIDEBAR ---
with st.sidebar:
	st.title("🎗️ C-Answer")
	st.markdown("### Patient Profile")
	st.markdown("Customize parameters to filter active trials.")
	
	with st.form("patient_form"):
		spacer(10)
		
		st.write("**1. Diagnosis**")
		diagnosis = st.text_input("Primary Condition", value="", placeholder="e.g. Colorectal Cancer")
		spacer(15) 
		
		st.write("**2. Metastasis**")
		metastasis = st.text_input("Metastasis Location", value="", placeholder="e.g. Liver, Lung")
		spacer(15) 
		
		st.write("**3. Demographics**")
		col1, col2 = st.columns(2)
		with col1:
			age = st.number_input("Age", value=35, step=1)
		with col2:
			sex = st.selectbox("Sex", ["Male", "Female"])
		spacer(20) 
			
		st.markdown("---")
		st.write("**Advanced Filters**")
		kras = st.checkbox("KRAS Wild-type Only", value=False)
		phase1 = st.checkbox("Exclude Phase 1 Trials", value=False)
		
		spacer(30) 
		submitted = st.form_submit_button("🔍 Find Matching Trials", type="primary")

# --- MAIN CONTENT ---

st.title("C-Answer")
st.markdown("### Intelligent Clinical Trial Matching & Recovery Planning")

spacer(20)

# --- SESSION STATE INITIALIZATION ---
if 'studies' not in st.session_state:
	st.session_state.studies = []
if 'analysis_results' not in st.session_state:
	st.session_state.analysis_results = {}
if 'active_nct_id' not in st.session_state:
	st.session_state.active_nct_id = None

# --- SEARCH LOGIC ---
if submitted:
	if not diagnosis.strip():
		st.warning("⚠️ Please enter a diagnosis to start your search.")
	else:
		# Reset previous analyses on new search
		st.session_state.analysis_results = {}
		st.session_state.active_nct_id = None
		
		if metastasis.strip():
			search_term = f"{diagnosis} {metastasis}"
		else:
			search_term = diagnosis

		with st.spinner(f"Connecting to ClinicalTrials.gov for '{search_term}'..."):
			data = fetch_clinical_trials(search_term)
			st.session_state.studies = data.get('studies', [])

# --- DISPLAY LOGIC ---
trials = st.session_state.studies

if not trials:
	if not submitted:
		st.info("👈 Use the sidebar to enter your diagnosis and start the search.")
	elif submitted and diagnosis.strip():
		st.warning("No recruiting trials found for that specific query.")

else:
	col1, col2, col3 = st.columns(3)
	col1.metric("Trials Found", len(trials))
	col2.metric("Status", "Recruiting")
	col3.metric("Source", "ClinicalTrials.gov")
	
	spacer(30)
	
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

		# Check if this card should be forced open (because user just clicked analyze)
		should_be_expanded = (nct_id == st.session_state.active_nct_id)

		with st.expander(f"{title}", expanded=should_be_expanded):
			st.markdown(f"""
			<div style="margin-bottom: 15px;">
				<span class="status-badge">Recruiting</span> 
				<span style="margin-left: 10px; color: #94a3b8; font-family: monospace;">{nct_id}</span>
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
				
				# Check for existing results in memory
				existing_result = st.session_state.analysis_results.get(nct_id)
				
				if existing_result:
					if "Status: Match" in existing_result:
						st.success(existing_result)
					elif "Status: No Match" in existing_result:
						st.error(existing_result)
					else:
						st.warning(existing_result)
				else:
					st.info("Click the button below to check if you qualify.")
				
				# THE ANALYZE BUTTON
				if st.button(f"Analyze Match for {nct_id}", key=f"btn_{nct_id}"):
					
					profile_str = f"Age: {age}, Sex: {sex}, Diagnosis: {diagnosis}, Metastasis: {metastasis}"
					if kras: profile_str += ", KRAS Wild-type"
					
					with st.spinner("Consulting AI Agent..."):
						ai_result = analyze_trial_eligibility(criteria, profile_str)
					
					# Save result and force reload
					st.session_state.analysis_results[nct_id] = ai_result
					st.session_state.active_nct_id = nct_id 
					st.rerun()
				
				st.markdown(f"[View Official Record ↗](https://clinicaltrials.gov/study/{nct_id})")