
import os
import sys
from sources.scrapers.utils.intelligence import IntelligenceEngine

def verify_gazette():
    file_path = "/home/sidhant/Desktop/sourcegov/government-announcements/data/raw/dist-20-bokaro-coll/931e4690a3ead78e.pdf"
    
    if not os.path.exists(file_path):
        print("File not found.")
        return

    print(f"Analyzing {file_path}...")
    engine = IntelligenceEngine()
    
    prompt = """
    Analyze this document. 
    1. Is this the "District Gazette of Reservation and Allotment (Form-3) of Territorial Constituencies (Places) of Phusro Nagar Parishad (Class-B) for the Municipal General Election, 2026"?
    2. Does it contain ward-wise reservation details (SC/ST/Women/General)?
    3. Is it valid?
    
    Answer concisely.
    """
    
    summary = engine.summarize_pdfs([file_path], prompt)
    print("\nanalysis_result:")
    print(summary)

if __name__ == "__main__":
    verify_gazette()
