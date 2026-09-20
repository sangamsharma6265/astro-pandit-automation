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
        
        # 1. Direct standard 7 planets grab
        standard_attrs = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn']
        for attr in standard_attrs:
            if hasattr(subject, attr):
                p_obj = getattr(subject, attr)
                if p_obj:
                    self.planets.append(p_obj)

        # 2. Explicitly grab and rename Rahu (North Node)
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

        # 3. Explicitly grab Ketu using correct Kerykeion names (true_south_node / mean_south_node)
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
            # Fallback: Clone Rahu and shift by 180 degrees / 6 houses if south node attr is missing
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

        # 4. Fallback safeguard loop for any missed elements
        if len(self.planets) < 9:
            for attr in dir(subject):
                if not attr.startswith('_') and attr not in ['model_fields', 'model_computed_fields']:
                    try:
                        val = getattr(subject, attr)
                        if hasattr(val, 'name') and hasattr(val, 'sign'):
                            name_lower = str(val.name).lower()
                            if ('north' in name_lower or 'true' in name_lower or 'mean' in name_lower or 'rahu' in name_lower) and 'south' not in name_lower:
                                val.name = 'Rahu'
                                if val not in self.planets: self.planets.append(val)
                            elif 'south' in name_lower or 'ketu' in name_lower:
                                val.name = 'Ketu'
                                if val not in self.planets: self.planets.append(val)
                    except Exception:
                        continue

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
        
        # Exact geometric center coordinates (X, Y) for North Indian houses 1 to 12
        house_coords = {
            1:  (250, 130),
            2:  (360, 95),
            3:  (405, 140),
            4:  (370, 250),
            5:  (405, 360),
            6:  (360, 405),
            7:  (250, 370),
            8:  (140, 405),
            9:  (95,  360),
            10: (130, 250),
            11: (95,  140),
            12: (140, 95)
        }

        def render_house_planets(h_num):
            p_list = hp.get(h_num, [])
            if not p_list: return ""
            cx, cy = house_coords[h_num]
            svg_tags = ""
            start_y = cy - ((len(p_list) - 1) * 9)
            for idx, p_code in enumerate(p_list):
                curr_y = start_y + (idx * 18)
                svg_tags += f'<tspan x="{cx}" y="{curr_y}" fill="#fde047" font-weight="bold">{p_code}</tspan>'
            return svg_tags

        # Extract unique planets for details table
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
            house_clean = house_raw.replace('_', ' ').replace('House', '').strip() if house_raw else 'N/A'
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

        # Build Yogas & Doshas cards
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
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0b0f19;
                    color: #f8fafc;
                    margin: 0;
                    padding: 40px 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                .report-container {{
                    width: 100%;
                    max-width: 850px;
                    background: #111827;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.8);
                    border: 2px solid #fbbf24;
                }}
                header {{
                    text-align: center;
                    border-bottom: 2px solid #374151;
                    padding-bottom: 25px;
                    margin-bottom: 30px;
                }}
                header h1 {{ color: #fbbf24; margin: 0 0 10px 0; font-size: 28px; letter-spacing: 1.5px; }}
                header p {{ color: #94a3b8; margin: 5px 0; font-size: 15px; }}
                
                .section-title {{
                    color: #38bdf8;
                    border-left: 4px solid #38bdf8;
                    padding-left: 12px;
                    margin-top: 40px;
                    margin-bottom: 20px;
                    font-size: 20px;
                    letter-spacing: 0.5px;
                }}
                
                .chart-section {{
                    text-align: center;
                    background: #0f172a;
                    padding: 25px;
                    border-radius: 12px;
                    border: 1px solid #374151;
                    margin-bottom: 30px;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: #0f172a;
                    border-radius: 8px;
                    overflow: hidden;
                    margin-bottom: 30px;
                    border: 1px solid #374151;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #1e293b;
                }}
                th {{
                    background: #1e293b;
                    color: #fbbf24;
                    font-weight: 600;
                }}
                td {{ color: #e2e8f0; font-size: 14px; }}
                tr:hover {{ background: #1a2234; }}
                
                .yoga-card {{
                    background: #0f172a;
                    border: 1px solid #374151;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 15px;
                }}
                .yoga-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .yoga-header h3 {{ margin: 0; color: #fbbf24; font-size: 17px; }}
                .status-badge {{
                    padding: 4px 10px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #fff;
                }}
                .yoga-card p {{ margin: 6px 0; color: #94a3b8; font-size: 14px; line-height: 1.5; }}
                .yoga-card b {{ color: #e2e8f0; }}
                
                .dasha-box, .prompt-box {{
                    background: #0f172a;
                    border: 1px solid #374151;
                    border-radius: 10px;
                    padding: 15px;
                    overflow-x: auto;
                    font-family: monospace;
                    color: #cbd5e1;
                    font-size: 13px;
                    white-space: pre-wrap;
                }}
                .prompt-box {{
                    border: 1px dashed #38bdf8;
                    color: #38bdf8;
                    margin-bottom: 15px;
                }}
                
                footer {{
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #374151;
                    color: #64748b;
                    font-size: 13px;
                }}
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

                        <!-- Anticlockwise House/Rashi Numbers (North Indian Standard: Top Diamond is 1, then counter-clockwise) -->
                        <text x="250" y="75" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">1</text>
                        <text x="140" y="55" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">2</text>
                        <text x="75" y="115" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">3</text>
                        <text x="130" y="210" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">4</text>
                        <text x="75" y="310" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">5</text>
                        <text x="140" y="385" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">6</text>
                        <text x="250" y="330" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">7</text>
                        <text x="360" y="385" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">8</text>
                        <text x="425" y="310" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">9</text>
                        <text x="370" y="210" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">10</text>
                        <text x="425" y="115" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">11</text>
                        <text x="360" y="55" fill="#38bdf8" font-size="13" font-weight="bold" text-anchor="middle">12</text>

                        <!-- Planets -->
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(1)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(2)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(3)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(4)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(5)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(6)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(7)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(8)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(9)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(10)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(11)}</text>
                        <text font-size="12" font-family="monospace" text-anchor="middle">{render_house_planets(12)}</text>
                    </svg>
                </div>

                <div class="section-title">Planetary Positions & House Placements</div>
                <table>
                    <thead>
                        <tr>
                            <th>Planet</th>
                            <th>Zodiac Sign</th>
                            <th>Degree</th>
                            <th>House</th>
                        </tr>
                    </thead>
                    <tbody>
                        {planets_table_rows}
                    </tbody>
                </table>

                <div class="section-title">Detailed Dosh & Yoga Analysis</div>
                {yogas_html}

                <div class="section-title">Vimshottari Mahadasha & Antardasha Timeline (100-Year)</div>
                <div class="dasha-box">
                    {self.dasha_table_str}
                </div>

                <div class="section-title">1. Master Core Consultation Prompt (Hinglish & Simple)</div>
                <div class="prompt-box">
                    {self.ai_prompt_text}
                </div>

                <div class="section-title">2. Custom House Inquiry Prompt (For any other house)</div>
                <div class="prompt-box">
                    {self.custom_prompt_text}
                </div>

                <footer>
                    Astro Pandit Automated Report Factory &bull; Powered by Lahiri Sidereal Engine
                </footer>
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