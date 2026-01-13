import streamlit as st
from groq import Groq

def get_groq_client():
	try:
		api_key = st.secrets["GROQ_API_KEY"]
		return Groq(api_key=api_key)
	except Exception:
		return None

def analyze_trial_eligibility(criteria_text, patient_profile):
	if not criteria_text or len(criteria_text) < 10:
		return "N/A - No criteria provided"
	
	client = get_groq_client()
	if not client: return "Error: API Key missing."

	try:
		system_prompt = """
		You are an expert oncologist assistant. Compare the patient's profile 
		against the clinical trial's eligibility criteria.
		
		Rules:
		1. Output strictly in this format: "Status: [Match/No Match/Maybe] - [Reason]"
		2. Be conservative. If a criterion excludes the patient, mark "No Match".
		3. Keep the reason short (1 sentence).
		"""
		user_message = f"PATIENT PROFILE:\n{patient_profile}\n\nTRIAL CRITERIA:\n{criteria_text}"

		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_message}
			],
			temperature=0, max_tokens=150
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error: {str(e)}"

def generate_treatment_report(diagnosis, metastasis, biomarkers):
	client = get_groq_client()
	if not client: return "Error: API Key missing."

	system_prompt = """
	You are a senior research oncologist. 
	Generate a high-level summary of the CURRENT Standard of Care and Emerging Therapies 
	that are showing success for the specific diagnosis provided.
	
	Structure the response with clear headers for Standard First-Line, Targeted Therapies, and Emerging Approaches.
	Keep it hopeful but medically accurate.
	"""
	
	user_message = f"Diagnosis: {diagnosis}, Mets: {metastasis}, Biomarkers: {biomarkers}"

	try:
		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_message}
			],
			temperature=0.3, max_tokens=600
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error: {str(e)}"

def compare_trials(saved_trials_dict):
	"""
	(NEW) Takes a dictionary of saved trials and creates a text-based comparison.
	"""
	client = get_groq_client()
	if not client: return "Error: API Key missing."
	
	trials_text = ""
	for nct_id, details in saved_trials_dict.items():
		trials_text += f"\n--- TRIAL {nct_id} ---\nTitle: {details['title']}\nSummary: {details['summary'][:500]}...\n"

	# FIXED PROMPT: Asks for LIST format instead of TABLE
	system_prompt = """
	You are an oncologist helping a patient decide between clinical trials.
	Compare the provided trials in a clean summary format (NO TABLES).
	
	For each trial, output a block like this:
	
	[Trial ID]
	* Intervention: [Type]
	* Phase: [Phase]
	* Key Benefit: [1-3 words]
	* Burden: [Low/Med/High]
	* Verdict: [1 sentence pro/con]
	
	Do not use markdown tables or horizontal lines.
	"""

	try:
		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": trials_text}
			],
			temperature=0.2, max_tokens=800
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error comparing trials: {str(e)}"
