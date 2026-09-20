import os
import json
import traceback
from pathlib import Path
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from geopy.geocoders import Nominatim
from kerykeion import AstrologicalSubjectFactory
from kerykeion.chart_data.factory import ChartDataFactory
from vedic_analyzer import VedicAnalyzer
from dasha_generator import DashaGenerator
from chart_visualizer import VedicGridChartVisualizer

app = Flask(__name__)

# --- SECURE FILE PATH FINDER ---
BASE_DIR = Path(__file__).resolve().parent
render_secret_path = Path("/etc/secrets/credentials.json")
local_path = BASE_DIR / "credentials.json"

if render_secret_path.exists():
    cred_path = render_secret_path
    print("[INFO] Loaded credentials from Render Secret Files.")
elif local_path.exists():
    cred_path = local_path
    print("[INFO] Loaded credentials from local file.")
else:
    print("[WARNING] credentials.json not found anywhere!")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(str(cred_path), scope)
client = gspread.authorize(creds)

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
        req_data = request.get_json() or {}
        print(f"\n[INCOMING PAYLOAD]: {req_data}")
        
        # Sabhi possible keys ko dynamically check karne ke liye
        name = None
        dob = None
        tob = None
        city = None
        
        for k, v in req_data.items():
            k_lower = k.lower()
            if 'name' in k_lower:
                name = v
            elif 'dob' in k_lower or 'birth date' in k_lower or 'date' in k_lower:
                dob = v
            elif 'tob' in k_lower or 'time' in k_lower:
                tob = v
            elif 'city' in k_lower or 'place' in k_lower or 'location' in k_lower:
                city = v
                
        # Fallbacks agar koi field na mile
        name = name if name else "Client"
        dob = dob if dob else "2004-06-15"
        tob = tob if tob else "12:00"
        city = city if city else "Delhi"
        
        print(f"\n[WEBHOOK TRIGGERED] Parsed -> Name: {name}, DOB: {dob}, Time: {tob}, City: {city}")
        
        year, month, day = 1998, 10, 15
        hour, minute = 12, 0
        
        try:
            if dob:
                parts_date = str(dob).split('-' if '-' in str(dob) else '/')
                if len(parts_date[0]) == 4:
                    year, month, day = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
                else:
                    day, month, year = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
            
            if tob and ':' in str(tob):
                parts_time = str(tob).split(':')
                hour, minute = int(parts_time[0]), int(parts_time[1])
            else:
                hour, minute = 12, 0
        except Exception as parse_err:
            print(f"[PARSING WARNING] Using defaults due to: {parse_err}")

        lat, lng = get_lat_lng(city if city else "Delhi")
        
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=str(name), year=year, month=month, day=day, hour=hour, minute=minute,
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
        
        report_filename = f"{str(name).replace(' ', '_')}_Kundali_Report.html"
        report_path = BASE_DIR / report_filename
        
        grid_visualizer.generate_html_grid_chart(filename=str(report_path))
        
        with open(report_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        return jsonify({
            "status": "success",
            "filename": report_filename,
            "html_content": html_content,
            "message": f"Report generated successfully for {name}!"
        }), 200

    except Exception as e:
        print(f"\n[CRITICAL ERROR FOUND IN WEBHOOK]")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))