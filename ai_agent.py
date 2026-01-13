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
    client = get_groq_client()
    if not client: return None

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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"REPORT TEXT:\n{medical_text[:6000]}"}
            ],
            temperature=0, 
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return None

def analyze_trial_eligibility(criteria_text, patient_profile):
    client = get_groq_client()
    if not client: return "Error: API Key missing."

    try:
        system_prompt = "You are an oncologist assistant. Compare the patient profile against eligibility criteria. Output format: 'Status: [Match/No Match] - [Reason]'."
        user_message = f"PATIENT:\n{patient_profile}\n\nCRITERIA:\n{criteria_text}"

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=0, max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def generate_treatment_report(patient_profile):
    """
    (CRITICAL FIX) Accepts a single 'patient_profile' string argument.
    """
    client = get_groq_client()
    if not client: return "Error: API Key missing."

    system_prompt = """
    You are a senior research oncologist. 
    Generate a HIGHLY PERSONALIZED summary of the Standard of Care and Emerging Therapies 
    specifically for this patient's unique profile (Age, ECOG, Prior Lines, MSI Status, Mutations).
    
    Rules:
    1. If they are MSI-High, emphasize Immunotherapy (Keytruda/Opdivo).
    2. If they are BRAF/KRAS mutant, mention targeted therapies.
    3. If they are 2nd/3rd line, focus on refractory options (TAS-102, Regorafenib, Trials).
    4. Use Markdown headers. Keep it hopeful but medically precise.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"PATIENT PROFILE:\n{patient_profile}"}],
            temperature=0.3, max_tokens=700
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def compare_trials(saved_trials_dict):
    client = get_groq_client()
    if not client: return "Error: API Key missing."
    
    trials_text = ""
    for nct_id, details in saved_trials_dict.items():
        trials_text += f"\n--- TRIAL {nct_id} ---\nTitle: {details['title']}\nSummary: {details['summary'][:500]}...\n"

    system_prompt = """
    Compare these trials in a list format (NO TABLES).
    For each, output: [Trial ID], * Intervention, * Phase, * Benefit, * Burden, * Verdict.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": trials_text}],
            temperature=0.2, max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
