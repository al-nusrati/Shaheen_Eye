import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
# Ensure your .env file has: GROQ_API_KEY=gsk_...
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fbr_report(person_name, asset_details, score):
    system_prompt = """
    You are a Senior Auditor at the Federal Board of Revenue (FBR) Pakistan.
    Write a formal 3-paragraph investigation report. Use legal terminology like 'Section 111'.
    """
    user_content = f"SUBJECT: {person_name}, SCORE: {score}/100, ASSETS: {asset_details}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

if __name__ == "__main__":
    # This block runs ONLY when you execute the script directly
    print("--- Testing Groq AI Connection ---")
    report = generate_fbr_report("Muhammad Arshad", "3000cc Land Cruiser, DHA Plot", 97)
    print(report)