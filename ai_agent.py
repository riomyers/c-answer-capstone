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
    Includes specific logic hints to improve AI extraction accuracy.
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"REPORT TEXT:\n{medical_text[:6000]}"}
            ],
            temperature=0, 
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception:
        return None

def analyze_trial_eligibility(criteria_text, patient_profile):
    """Matches a patient profile against clinical trial inclusion/exclusion criteria."""
    client = get_groq_client()
    if not client: 
        return "Error: API Key missing."

    try:
        system_prompt = "You are an oncologist assistant. Compare the patient profile against eligibility criteria. Output format: 'Status: [Match/No Match] - [Reason]'."
        user_message = f"PATIENT:\n{patient_profile}\n\nCRITERIA:\n{criteria_text}"

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=0, 
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def generate_treatment_report(patient_profile):
    """Generates a structured treatment landscape report personalized to the patient."""
    client = get_groq_client()
    if not client: 
        return "Error: API Key missing."

    system_prompt = """
    You are a senior research oncologist. Generate a summary of the Treatment Landscape for this patient.
    
    STRICT STRUCTURE REQUIRED:
    Output using exactly these three Markdown headers:
    1. **Standard First-Line Treatments** (or Next-Line if prior therapy exists)
    2. **Targeted Therapies** (Reference mutations like KRAS/BRAF if present)
    3. **Emerging Approaches** (Trials, Immunotherapy, Vaccines)
    
    CONTENT RULES:
    - Personalize based on the Patient Profile (Age, ECOG, MSI Status).
    - If MSI-High, heavily emphasize Immunotherapy.
    - Keep it concise, hopeful, and medically precise.
    - Use standard hyphens (-) for all bullet points to ensure PDF compatibility.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"PATIENT PROFILE:\n{patient_profile}"}],
            temperature=0.3, 
            max_tokens=700
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def compare_trials(saved_trials_dict):
    """
    Generates a high-quality, spaced-out comparison of trials.
    Restored icons and bolding for professional presentation.
    """
    client = get_groq_client()
    if not client: 
        return "Error: API Key missing."
    
    trials_text = ""
    for nct_id, details in saved_trials_dict.items():
        trials_text += f"\n--- TRIAL {nct_id} ---\nTitle: {details['title']}\nSummary: {details['summary'][:500]}...\n"

    system_prompt = """
    You are an oncologist helping a patient decide between clinical trials.
    Compare the provided trials in a clean, spaced-out format.
    
    For EACH trial, output a block exactly like this:
    
    ---
    ### 🔬 [Trial ID]
    * **Intervention**: [Type of Drug/Therapy]
    * **Phase**: [Phase 1/2/3]
    * **Key Benefit**: [1 sentence on why this is good]
    * **Patient Burden**: [Low/Med/High] (e.g. oral pill vs weekly IV)
    * **My Verdict**: [1 clear sentence recommendation]
    
    (Use only standard hyphens (-) or asterisks (*) for bullets. Ensure a '---' separator exists between trials).
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": trials_text}],
            temperature=0.2, 
            max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
