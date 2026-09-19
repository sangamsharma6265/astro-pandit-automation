import os
import json
from pathlib import Path
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from geopy.geocoders import Nominatim
from kerykeion import AstrologicalSubjectFactory
from kerykeion.chart_data.factory import ChartDataFactory
from vedic_analyzer import VedicAnalyzer
from dasha_generator import DashaGenerator
from chart_visualizer import VedicGridChartVisualizer

app = Flask(__name__)

# --- RENDER/CLOUD CREDENTIALS FIX (Yeh naya joda hai) ---
CREDENTIALS_DATA = os.environ.get("CREDENTIALS_JSON")
if CREDENTIALS_DATA:
    with open("credentials.json", "w") as f:
        f.write(CREDENTIALS_DATA)
# ---------------------------------------------------------

# 1. Secure Absolute Path & Setup
BASE_DIR = Path(__file__).resolve().parent
cred_path = BASE_DIR / "credentials.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(str(cred_path), scope)
client = gspread.authorize(creds)

# Google Drive API Client Setup
drive_service = build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, file_name):
    try:
        file_metadata = {'name': file_name}
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id'
        ).execute()
        print(f"[DRIVE] File successfully uploaded to Google Drive! File ID: {file.get('id')}")
    except Exception as e:
        print(f"[DRIVE ERROR] Failed to upload: {e}")

geolocator = Nominatim(user_agent="astro_pandit_worker")

def get_lat_lng(city_name):
    try:
        loc = geolocator.geocode(city_name)
        if loc:
            return loc.latitude, loc.longitude
    except Exception:
        pass
    return 28.6139, 77.2090  # Default Delhi fallback

@app.route('/')
def home():
    return "Astro Pandit Instant Webhook Server is Running! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Google Sheet se latest row data fetch karenge
        sheet = client.open("AstroPandit").sheet1
        rows = sheet.get_all_values()
        
        if len(rows) < 2:
            return jsonify({"status": "error", "message": "No data found in sheet"}), 400
        
        # Sabse aakhri (latest) row uthayenge jo form se aayi hai
        latest_row = rows[-1]
        
        if len(latest_row) < 5:
            return jsonify({"status": "error", "message": "Invalid row data"}), 400
        
        timestamp = latest_row[0]
        name = latest_row[1]
        dob = latest_row[2]
        tob = latest_row[3]
        city = latest_row[4]
        
        print(f"\n[WEBHOOK TRIGGERED] New entry -> Name: {name}, DOB: {dob}, Time: {tob}, City: {city}")
        
        # Smart Date & Time Parsing
        try:
            parts_date = dob.split('-' if '-' in dob else '/')
            if len(parts_date[0]) == 4:
                year, month, day = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
            else:
                day, month, year = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
            
            parts_time = tob.split(':')
            hour, minute = int(parts_time[0]), int(parts_time[1])
        except Exception:
            year, month, day, hour, minute = 1998, 10, 15, 14, 30

        lat, lng = get_lat_lng(city if city else "Delhi")
        
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=name, year=year, month=month, day=day, hour=hour, minute=minute,
            lng=lng, lat=lat, tz_str="Asia/Kolkata", online=False,
            zodiac_type="Sidereal", sidereal_mode="LAHIRI"
        )
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        
        analyzer = VedicAnalyzer(subject, chart_data)
        vedic_results = analyzer.analyze_all()
        
        dasha_gen = DashaGenerator(subject)
        dasha_table_str = dasha_gen.generate_100_year_table()
        
        def get_planets_text(vis):
            p_list = []
            seen = set()
            for p in vis.planets:
                p_name = getattr(p, 'name', 'Planet').capitalize()
                if p_name in seen: continue
                seen.add(p_name)
                sign = getattr(p, 'sign', 'N/A')
                h_raw = getattr(p, 'house', 'N/A')
                h_clean = str(h_raw).replace('_', ' ').replace('House', '').strip()
                p_list.append(f"- {p_name}: Placed in {sign}, House {h_clean}")
            return "\n".join(p_list)
        
        temp_vis = VedicGridChartVisualizer(subject=subject, chart_data=chart_data)
        planets_text = get_planets_text(temp_vis)
        yogas_text = "".join([f"- {k.replace('_', ' ').title()}: {v['status']} ({v['impact']})\n" for k, v in vedic_results.items()])
        
        ai_prompt_text = f"""Act as a friendly, expert Vedic Astrologer. Analyze this birth chart for client {subject.name} (Born: {subject.year}-{subject.month:02d}-{subject.day:02d}, {city}):
Planetary Positions:
{planets_text}
Yogas:
{yogas_text}
Instructions: Explain in simple Hinglish (conversational Hindi in English letters). Cover 1st, 7th, and 10th houses simply."""

        custom_prompt_text = f"Act as an expert Vedic Astrologer for client {subject.name}. Positions:\n{planets_text}\nExplain user's specific house inquiry in simple Hinglish."

        grid_visualizer = VedicGridChartVisualizer(
            subject=subject, chart_data=chart_data, vedic_results=vedic_results,
            dasha_table_str=dasha_table_str, ai_prompt_text=ai_prompt_text, custom_prompt_text=custom_prompt_text
        )
        
        report_filename = f"{name.replace(' ', '_')}_Kundali_Report.html"
        grid_visualizer.generate_html_grid_chart(filename=report_filename)
        
        # Google Drive par upload
        upload_to_drive(report_filename, report_filename)
        
        return jsonify({"status": "success", "message": f"Report generated and uploaded for {name}!"}), 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))