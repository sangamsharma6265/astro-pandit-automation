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
elif local_path.exists():
    cred_path = local_path

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
    return 28.6139, 77.2090

@app.route('/')
def home():
    return "Astro Pandit Instant Webhook Server is Running! 🚀"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    try:
        req_data = request.get_json(silent=True) or request.form.to_dict() or request.args.to_dict() or {}
        print(f"\n[INCOMING PAYLOAD]: {req_data}")
        
        # Fallbacks
        name = "Rahul"
        dob = "1998-10-15"
        tob = "14:30"
        city = "Delhi"
        
        # Flexible key matching for Google Forms / Sheets Webhook
        for k, v in req_data.items():
            k_clean = str(k).strip().lower()
            val_clean = str(v[0] if isinstance(v, list) else v).strip()
            
            if not val_clean or val_clean.lower() == 'none':
                continue
                
            if any(term in k_clean for term in ['name', 'client']):
                name = val_clean
            elif any(term in k_clean for term in ['dob', 'birth date', 'date of birth', 'date']):
                dob = val_clean
            elif any(term in k_clean for term in ['tob', 'birth time', 'time of birth', 'time']):
                tob = val_clean
            elif any(term in k_clean for term in ['city', 'location', 'place', 'birth place']):
                city = val_clean
                
        print(f"\n[PARSED DATA] Name: {name}, DOB: {dob}, Time: {tob}, City: {city}")
        
        year, month, day = 1998, 10, 15
        hour, minute = 14, 30
        
        try:
            if dob:
                dob_str = str(dob).strip().split('T')[0] # handle ISO date formats if any
                parts_date = dob_str.split('-' if '-' in dob_str else '/')
                if len(parts_date) >= 3:
                    if len(parts_date[0]) == 4:
                        year, month, day = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
                    else:
                        day, month, year = int(parts_date[0]), int(parts_date[1]), int(parts_date[2])
            
            if tob:
                tob_str = str(tob).strip().upper()
                is_pm = 'PM' in tob_str
                is_am = 'AM' in tob_str
                time_clean = tob_str.replace('AM', '').replace('PM', '').strip()
                parts_time = time_clean.split(':')
                if len(parts_time) >= 2:
                    hour, minute = int(parts_time[0]), int(parts_time[1])
                    if is_pm and hour < 12:
                        hour += 12
                    elif is_am and hour == 12:
                        hour = 0
        except Exception as parse_err:
            print(f"[PARSING WARNING]: {parse_err}")

        lat, lng = get_lat_lng(city)
        
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