import time
from pathlib import Path
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

# 1. Secure Absolute Path
BASE_DIR = Path(__file__).resolve().parent
cred_path = BASE_DIR / "credentials.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(str(cred_path), scope)
client = gspread.authorize(creds)

# Google Drive API Client Setup
drive_service = build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, file_name):
    """Generated file ko Google Drive par upload karne ka function"""
    try:
        file_metadata = {'name': file_name}
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id'
        ).execute()
        print(f"[DRIVE] File successfully uploaded to Google Drive! File ID: {file.get('id')}")
    except Exception as e:
        print(f"[DRIVE ERROR] Failed to upload: {e}")

# Google Sheet ka exact naam "AstroPandit" set hai
sheet = client.open("AstroPandit").sheet1 

# 2. Geocoding helper function
geolocator = Nominatim(user_agent="astro_pandit_worker")

def get_lat_lng(city_name):
    try:
        loc = geolocator.geocode(city_name)
        if loc:
            return loc.latitude, loc.longitude
    except Exception:
        pass
    return 28.6139, 77.2090  # Default Delhi fallback

print("[INFO] 🤖 Astro Pandit Automation Worker with Google Drive Sync is running...")

# 3. Main processing loop
processed_rows = set()

while True:
    try:
        rows = sheet.get_all_values()
        
        for idx, row in enumerate(rows[1:], start=2):
            if idx in processed_rows:
                continue
            
            if len(row) < 5:
                continue
            
            timestamp = row[0]
            name = row[1]
            dob = row[2]
            tob = row[3]
            city = row[4]
            
            if not name or not dob:
                continue
            
            print(f"\n[PROCESSING] New client detected -> Name: {name}, DOB: {dob}, Time: {tob}, City: {city}")
            
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
            
            print(f"[SUCCESS] Report generated locally for {name}!")
            
            # Google Drive par upload karna
            upload_to_drive(report_filename, report_filename)
            
            processed_rows.add(idx)
            
    except Exception as e:
        print(f"[ERROR] {e}")
        
    time.sleep(10)