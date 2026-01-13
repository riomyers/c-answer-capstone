import streamlit as st
from groq import Groq

def get_groq_client():
	"""Securely get the Groq client."""
	try:
		api_key = st.secrets["GROQ_API_KEY"]
		return Groq(api_key=api_key)
	except Exception:
		return None

def analyze_trial_eligibility(criteria_text, patient_profile):
	"""(Existing function) Checks match status."""
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
	"""
	(NEW) Generates a summary of current successful treatments 
	and standard of care for the specific condition.
	"""
	client = get_groq_client()
	if not client: return "Error: API Key missing."

	system_prompt = """
	You are a senior research oncologist. 
	Generate a high-level summary of the CURRENT Standard of Care and Emerging Therapies 
	that are showing success for the specific diagnosis provided.
	
	Structure the response in Markdown with these headers:
	1. **Standard First-Line Treatments** (Proven options)
	2. **Targeted Therapies** (Based on biomarkers like KRAS/BRAF)
	3. **Emerging Approaches** (Immunotherapy, etc.)
	
	Keep it hopeful but medically accurate. 
	"""
	
	user_message = f"""
	Diagnosis: {diagnosis}
	Metastasis: {metastasis}
	Biomarkers/Notes: {biomarkers}
	"""

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
		return f"Error generating report: {str(e)}"
