import os
import copy

class VedicGridChartVisualizer:
    def __init__(self, subject, chart_data, vedic_results=None, dasha_table_str=None, ai_prompt_text=None, custom_prompt_text=None):
        self.subject = subject
        self.chart_data = chart_data
        self.vedic_results = vedic_results or {}
        self.dasha_table_str = dasha_table_str or ""
        self.ai_prompt_text = ai_prompt_text or ""
        self.custom_prompt_text = custom_prompt_text or ""
        self.planets = []
        
        standard_attrs = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn']
        for attr in standard_attrs:
            if hasattr(subject, attr):
                p_obj = getattr(subject, attr)
                if p_obj:
                    self.planets.append(p_obj)

        rahu_obj = None
        for r_attr in ['true_node', 'mean_node', 'north_node', 'rahu']:
            if hasattr(subject, r_attr):
                val = getattr(subject, r_attr)
                if val:
                    rahu_obj = val
                    break
        if rahu_obj:
            rahu_obj.name = 'Rahu'
            self.planets.append(rahu_obj)

        ketu_obj = None
        for k_attr in ['true_south_node', 'mean_south_node', 'south_node', 'ketu']:
            if hasattr(subject, k_attr):
                val = getattr(subject, k_attr)
                if val:
                    ketu_obj = val
                    break
        
        if ketu_obj:
            ketu_obj.name = 'Ketu'
            self.planets.append(ketu_obj)
        elif rahu_obj:
            ketu_obj = copy.deepcopy(rahu_obj)
            ketu_obj.name = 'Ketu'
            rahu_house_raw = getattr(rahu_obj, 'house', 'First')
            rahu_h_num = self._extract_house_num(rahu_house_raw)
            if rahu_h_num > 0:
                ketu_h_num = ((rahu_h_num + 5) % 12) + 1
                house_mapping_inv = {
                    1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth',
                    5: 'Fifth', 6: 'Sixth', 7: 'Seventh', 8: 'Eighth',
                    9: 'Ninth', 10: 'Tenth', 11: 'Eleventh', 12: 'Twelfth'
                }
                ketu_obj.house = house_mapping_inv.get(ketu_h_num, 'First')
            curr_pos = getattr(rahu_obj, 'position', 0.0)
            ketu_obj.position = (curr_pos + 180.0) % 360.0
            self.planets.append(ketu_obj)

    def get_lagna_sign_number(self):
        sign_map = {
            'aries': 1, 'taurus': 2, 'gemini': 3, 'cancer': 4,
            'leo': 5, 'virgo': 6, 'libra': 7, 'scorpio': 8,
            'sagittarius': 9, 'capricorn': 10, 'aquarius': 11, 'pisces': 12
        }
        asc = getattr(self.subject, 'ascendant', None)
        if asc:
            sign_name = str(getattr(asc, 'sign', asc)).lower()
            for k, v in sign_map.items():
                if k in sign_name:
                    return v
        return 1

    def get_house_rashi_map(self):
        lagna_num = self.get_lagna_sign_number()
        house_rashi = {}
        for h in range(1, 13):
            # Anticlockwise rashi assignment based on Lagna sign
            r_num = ((lagna_num + h - 2) % 12) + 1
            house_rashi[h] = r_num
        return house_rashi

    def get_house_planets_map(self):
        house_planets = {i: [] for i in range(1, 13)}
        seen = set()
        for p in self.planets:
            p_name = getattr(p, 'name', 'Planet').capitalize()
            if p_name in seen: continue
            seen.add(p_name)
            
            house_raw = getattr(p, 'house', '')
            h_num = self._extract_house_num(house_raw)
            if 1 <= h_num <= 12:
                house_planets[h_num].append(p_name[:3].upper())
        return house_planets

    def generate_html_grid_chart(self, filename="AstroPandit_Kundali_Report.html"):
        hp = self.get_house_planets_map()
        hr = self.get_house_rashi_map()
        
        house_coords = {
            1:  (250, 140), 2:  (160, 90),  3:  (100, 140), 4:  (140, 250),
            5:  (100, 360), 6:  (160, 410), 7:  (250, 360), 8:  (340, 410),
            9:  (400, 360), 10: (360, 250), 11: (400, 140), 12: (340, 90)
        }

        rashi_coords = {
            1:  (250, 90),   
            2:  (115, 75),   
            3:  (75,  115),   
            4:  (95,  250),  
            5:  (75,  385),  
            6:  (115, 425),  
            7:  (250, 410),  
            8:  (385, 425),  
            9:  (425, 385),  
            10: (405, 250), 
            11: (425, 115), 
            12: (385, 75)   
        }

        def render_house_content(h_num):
            r_num = hr.get(h_num, h_num)
            p_list = hp.get(h_num, [])
            cx, cy = house_coords[h_num]
            rx, ry = rashi_coords[h_num]
            
            svg_tags = f'<text x="{rx}" y="{ry}" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">{r_num}</text>'
            
            if p_list:
                start_y = cy - ((len(p_list) - 1) * 10)
                for idx, p_code in enumerate(p_list):
                    curr_y = start_y + (idx * 18)
                    svg_tags += f'<text x="{cx}" y="{curr_y}" fill="#fde047" font-size="12" font-weight="bold" text-anchor="middle">{p_code}</text>'
            return svg_tags

        unique_planets = []
        seen_p = set()
        for p in self.planets:
            p_name = getattr(p, 'name', 'Planet').capitalize()
            if p_name not in seen_p and p_name in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']:
                seen_p.add(p_name)
                unique_planets.append(p)

        planets_table_rows = ""
        for p in unique_planets:
            house_raw = getattr(p, 'house', 'N/A')
            house_clean = str(house_raw).replace('_', ' ').replace('House', '').strip() if house_raw else 'N/A'
            p_name = getattr(p, 'name', 'Planet').capitalize()
            sign = getattr(p, 'sign', 'N/A')
            pos = getattr(p, 'position', 0.0)
            planets_table_rows += f"""
                <tr>
                    <td><b>{p_name}</b></td>
                    <td>{sign}</td>
                    <td>{pos:.2f}°</td>
                    <td>House {house_clean}</td>
                </tr>
            """

        yogas_html = ""
        for yog_key, data in self.vedic_results.items():
            formatted_name = yog_key.replace('_', ' ').title()
            status_color = "#22c55e" if "Present" in str(data['status']) or "Yes" in str(data['status']) else "#ef4444"
            yogas_html += f"""
                <div class="yoga-card">
                    <div class="yoga-header">
                        <h3>{formatted_name}</h3>
                        <span class="status-badge" style="background: {status_color};">{data['status']}</span>
                    </div>
                    <p><b>Rule:</b> {data['rule']}</p>
                    <p><b>Reason:</b> {data['reason']}</p>
                    <p><b>Impact:</b> {data['impact']}</p>
                </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Astro Pandit - Professional Vedic Kundali Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0f19; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; flex-direction: column; align-items: center; }}
                .report-container {{ width: 100%; max-width: 850px; background: #111827; padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.8); border: 2px solid #fbbf24; }}
                header {{ text-align: center; border-bottom: 2px solid #374151; padding-bottom: 25px; margin-bottom: 30px; }}
                header h1 {{ color: #fbbf24; margin: 0 0 10px 0; font-size: 28px; letter-spacing: 1.5px; }}
                header p {{ color: #94a3b8; margin: 5px 0; font-size: 15px; }}
                .section-title {{ color: #38bdf8; border-left: 4px solid #38bdf8; padding-left: 12px; margin-top: 40px; margin-bottom: 20px; font-size: 20px; }}
                .chart-section {{ text-align: center; background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #374151; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 8px; overflow: hidden; margin-bottom: 30px; border: 1px solid #374151; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #1e293b; }}
                th {{ background: #1e293b; color: #fbbf24; font-weight: 600; }}
                td {{ color: #e2e8f0; font-size: 14px; }}
                .yoga-card {{ background: #0f172a; border: 1px solid #374151; border-radius: 10px; padding: 20px; margin-bottom: 15px; }}
                .yoga-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
                .yoga-header h3 {{ margin: 0; color: #fbbf24; font-size: 17px; }}
                .status-badge {{ padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; color: #fff; }}
                .yoga-card p {{ margin: 6px 0; color: #94a3b8; font-size: 14px; line-height: 1.5; }}
                .dasha-box, .prompt-box {{ background: #0f172a; border: 1px solid #374151; border-radius: 10px; padding: 15px; overflow-x: auto; font-family: monospace; color: #cbd5e1; font-size: 13px; white-space: pre-wrap; }}
                .prompt-box {{ border: 1px dashed #38bdf8; color: #38bdf8; margin-bottom: 15px; }}
                footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #374151; color: #64748b; font-size: 13px; }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <header>
                    <h1>🔮 ASTRO PANDIT - PROFESSIONAL KUNDALI REPORT 🔮</h1>
                    <p>Client Name: <b>{self.subject.name}</b> | Birth: {self.subject.year}-{self.subject.month:02d}-{self.subject.day:02d} {self.subject.hour:02d}:{self.subject.minute:02d}</p>
                    <p>Location: <b>Delhi</b> | Zodiac Mode: <b>Vedic Sidereal (Lahiri Ayanamsa)</b></p>
                </header>

                <div class="section-title">Vedic Planetary House Diagram (North Indian Chart)</div>
                <div class="chart-section">
                    <svg width="450" height="450" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
                        <rect width="500" height="500" fill="#0f172a" rx="10"/>
                        <rect x="50" y="50" width="400" height="400" fill="none" stroke="#fbbf24" stroke-width="3"/>
                        <line x1="50" y1="50" x2="450" y2="450" stroke="#fbbf24" stroke-width="2"/>
                        <line x1="450" y1="50" x2="50" y2="450" stroke="#fbbf24" stroke-width="2"/>
                        <line x1="250" y1="50" x2="450" y2="250" stroke="#fbbf24" stroke-width="2"/>
                        <line x1="450" y1="250" x2="250" y2="450" stroke="#fbbf24" stroke-width="2"/>
                        <line x1="250" y1="450" x2="50" y2="250" stroke="#fbbf24" stroke-width="2"/>
                        <line x1="50" y1="250" x2="250" y2="50" stroke="#fbbf24" stroke-width="2"/>

                        {render_house_content(1)}
                        {render_house_content(2)}
                        {render_house_content(3)}
                        {render_house_content(4)}
                        {render_house_content(5)}
                        {render_house_content(6)}
                        {render_house_content(7)}
                        {render_house_content(8)}
                        {render_house_content(9)}
                        {render_house_content(10)}
                        {render_house_content(11)}
                        {render_house_content(12)}
                    </svg>
                </div>

                <div class="section-title">Planetary Positions & House Placements</div>
                <table>
                    <thead><tr><th>Planet</th><th>Zodiac Sign</th><th>Degree</th><th>House</th></tr></thead>
                    <tbody>{planets_table_rows}</tbody>
                </table>

                <div class="section-title">Detailed Dosh & Yoga Analysis</div>
                {yogas_html}

                <div class="section-title">Vimshottari Mahadasha & Antardasha Timeline (100-Year)</div>
                <div class="dasha-box">{self.dasha_table_str}</div>

                <div class="section-title">1. Master Core Consultation Prompt</div>
                <div class="prompt-box">{self.ai_prompt_text}</div>

                <div class="section-title">2. Custom House Inquiry Prompt</div>
                <div class="prompt-box">{self.custom_prompt_text}</div>

                <footer>Astro Pandit Automated Report Factory &bull; Powered by Lahiri Sidereal Engine</footer>
            </div>
        </body>
        </html>
        """
        
        output_dir = "charts_output"
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return file_path

    def _extract_house_num(self, house_str):
        mapping = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4,
            'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8,
            'ninth': 9, 'tenth': 10, 'eleventh': 11, 'twelfth': 12
        }
        for key, val in mapping.items():
            if key in str(house_str).lower():
                return val
        return 0