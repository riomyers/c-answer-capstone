import streamlit as st
from groq import Groq
import json

def get_groq_client():
	try:
		api_key = st.secrets["GROQ_API_KEY"]
		return Groq(api_key=api_key)
	except Exception:
		return None

def extract_patient_data(medical_text):
	"""
	Extracts structured clinical data from raw medical text.
	Includes hints to help AI choose correct biomarker categories.
	"""
	client = get_groq_client()
	if not client:
		return None

	system_prompt = """
	You are a medical data extraction assistant. Read the provided medical report.
	Extract the following fields and return them strictly as a JSON object:
	
	{
		"diagnosis": "Primary cancer type (e.g. Colorectal Cancer)",
		"metastasis": "List of metastasis sites or empty string",
		"age": 50 (integer estimate or null),
		"sex": "Male", "Female", or "Select...",
		"kras_wild_type": true/false,
		"ecog": "0 - Fully Active" (Best guess from context or default to 0),
		"msi": "MSI-High" or "MSS" (or "Unknown"),
		"prior_lines": "None" or "1 Prior Line" (Best guess)
	}
	"""

	try:
		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{
					"role": "system", 
					"content": system_prompt
				},
				{
					"role": "user", 
					"content": f"REPORT TEXT:\n{medical_text[:6000]}"
				}
			],
			temperature=0, 
			response_format={"type": "json_object"}
		)
		return json.loads(completion.choices[0].message.content)
	except Exception:
		return None

def analyze_trial_eligibility(criteria_text, patient_profile):
	"""
	Matches a patient profile against trial criteria for inclusion/exclusion.
	"""
	client = get_groq_client()
	if not client: 
		return "Error: API Key missing."

	try:
		system_prompt = "You are an oncologist assistant. Compare the patient profile against eligibility criteria. Output format: 'Status: [Match/No Match] - [Reason]'."
		user_message = f"PATIENT:\n{patient_profile}\n\nCRITERIA:\n{criteria_text}"

		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{
					"role": "system", 
					"content": system_prompt
				}, 
				{
					"role": "user", 
					"content": user_message
				}
			],
			temperature=0, 
			max_tokens=150
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error: {str(e)}"

def generate_treatment_report(patient_profile):
	"""
	Generates a personalized treatment landscape report.
	"""
	client = get_groq_client()
	if not client: 
		return "Error: API Key missing."

	system_prompt = """
	You are a senior research oncologist. Generate a summary of the Treatment Landscape for this patient.
	
	STRICT STRUCTURE REQUIRED:
	Output using exactly these three Markdown headers:
	1. **Standard First-Line Treatments**
	2. **Targeted Therapies**
	3. **Emerging Approaches**
	
	CONTENT RULES:
	- Personalize based on Age, ECOG, and MSI Status.
	- If MSI-High, heavily emphasize Immunotherapy.
	- Keep it concise, hopeful, and medically precise.
	- Use standard hyphens (-) for all bullet points. No fancy characters.
	"""
	
	try:
		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{
					"role": "system", 
					"content": system_prompt
				}, 
				{
					"role": "user", 
					"content": f"PATIENT PROFILE:\n{patient_profile}"
				}
			],
			temperature=0.3, 
			max_tokens=700
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error: {str(e)}"

def compare_trials(saved_trials_dict):
	"""
	Generates a high-quality comparison of saved trials using standard formatting.
	"""
	client = get_groq_client()
	if not client: 
		return "Error: API Key missing."
	
	trials_text = ""
	for nct_id, details in saved_trials_dict.items():
		trials_text += f"\n--- TRIAL {nct_id} ---\n"
		trials_text += f"Title: {details['title']}\n"
		trials_text += f"Summary: {details['summary'][:500]}...\n"

	system_prompt = """
	Compare these clinical trials in a clean format. For EACH trial, output exactly this block:
	
	---
	### 🔬 [Trial ID]
	- Intervention: [Type of Drug/Therapy]
	- Phase: [Trial Phase]
	- Key Benefit: [1 sentence summarizing advantage]
	- Patient Burden: [Low/Med/High]
	- My Verdict: [Clear recommendation sentence]
	
	Use standard keyboard characters ONLY. Use '---' between every trial for visual separation.
	"""

	try:
		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile",
			messages=[
				{
					"role": "system", 
					"content": system_prompt
				}, 
				{
					"role": "user", 
					"content": trials_text
				}
			],
			temperature=0.2, 
			max_tokens=800
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"Error: {str(e)}"
