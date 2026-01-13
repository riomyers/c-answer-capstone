import streamlit as st
from groq import Groq

def analyze_trial_eligibility(criteria_text, patient_profile):
	"""
	Sends trial criteria and patient data to Llama 3 (via Groq) 
	to determine if it is a match.
	"""
	if not criteria_text or len(criteria_text) < 10:
		return "N/A - No criteria provided"

	# --- SECURITY CHECK ---
	# We attempt to load the key from Streamlit Secrets.
	# If it fails, we return a clear error instead of crashing or leaking keys.
	try:
		api_key = st.secrets["GROQ_API_KEY"]
	except Exception:
		return "Configuration Error: GROQ_API_KEY not found in Streamlit Secrets."

	try:
		client = Groq(api_key=api_key)

		system_prompt = """
		You are an expert oncologist assistant. Compare the patient's profile 
		against the clinical trial's eligibility criteria.
		
		Rules:
		1. Output strictly in this format: "Status: [Match/No Match/Maybe] - [Reason]"
		2. Be conservative. If a criterion excludes the patient, mark "No Match".
		3. Keep the reason short (1 sentence).
		"""

		user_message = f"""
		PATIENT PROFILE:
		{patient_profile}

		TRIAL ELIGIBILITY CRITERIA:
		{criteria_text}
		"""

		completion = client.chat.completions.create(
			model="llama-3.3-70b-versatile", 
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_message}
			],
			temperature=0, 
			max_tokens=150
		)
		
		return completion.choices[0].message.content
		
	except Exception as e:
		return f"Error: AI Analysis failed ({str(e)})"