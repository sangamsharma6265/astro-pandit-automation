from pathlib import Path
from kerykeion import AstrologicalSubjectFactory
from kerykeion.chart_data.factory import ChartDataFactory
from kerykeion.charts.drawer import ChartDrawer
from vedic_analyzer import VedicAnalyzer
from dasha_generator import DashaGenerator
from chart_visualizer import VedicGridChartVisualizer

# 1. Client Details
name = "Rahul"
year = 1998
month = 10
day = 15
hour = 14
minute = 30
city = "Delhi"
lat = 28.6139
lng = 77.2090

# Vedic/Sidereal (LAHIRI Ayanamsa) Subject Creation
subject = AstrologicalSubjectFactory.from_birth_data(
    name=name,
    year=year,
    month=month,
    day=day,
    hour=hour,
    minute=minute,
    lng=lng,
    lat=lat,
    tz_str="Asia/Kolkata",
    online=False,
    zodiac_type="Sidereal",
    sidereal_mode="LAHIRI"
)

chart_data = ChartDataFactory.create_natal_chart_data(subject)

# 2. Run Analyzers & Generators
analyzer = VedicAnalyzer(subject, chart_data)
vedic_results = analyzer.analyze_all()

dasha_gen = DashaGenerator(subject)
dasha_table_str = dasha_gen.generate_100_year_table()

# 3. Dummy Visualizer instance first to extract 100% accurate & fixed planets list (including Rahu/Ketu)
temp_visualizer = VedicGridChartVisualizer(subject=subject, chart_data=chart_data)

def get_planets_text_from_visualizer(visualizer):
    planets_list = []
    seen = set()
    for p in visualizer.planets:
        p_name = getattr(p, 'name', 'Planet').capitalize()
        if p_name in seen: continue
        seen.add(p_name)
        
        sign = getattr(p, 'sign', 'N/A')
        house_raw = getattr(p, 'house', 'N/A')
        house_clean = str(house_raw).replace('_', ' ').replace('House', '').strip()
        planets_list.append(f"- {p_name}: Placed in {sign}, House {house_clean}")
    return "\n".join(planets_list)

# 4. Prompt 1: Core Consultation Prompt (Hinglish & Simple)
def generate_core_ai_prompt(subject, visualizer, vedic_results):
    planets_text = get_planets_text_from_visualizer(visualizer)
    yogas_text = "".join([f"- {k.replace('_', ' ').title()}: {v['status']} ({v['impact']})\n" for k, v in vedic_results.items()])

    return f"""Act as a friendly, expert Vedic Astrologer. Analyze this birth chart data for client {subject.name} (Born: {subject.year}-{subject.month:02d}-{subject.day:02d} at {subject.hour:02d}:{subject.minute:02d}, Delhi):

### Planetary Positions:
{planets_text}

### Yogas Found:
{yogas_text}

Instructions:
1. Explain everything in simple **Hinglish** (conversational Hindi written in English letters). 
2. Do NOT use complex English words or heavy astrological jargon. Make it sound like a friendly consultation report that a normal client can easily understand.
3. Cover strictly: 
   - 1st House (Personality & Nature)
   - 7th House (Marriage & Relationships)
   - 10th House (Career & Money)
   - Simple, practical Upays (remedies) if needed.
Do not invent any new planetary positions."""

# 5. Prompt 2: Custom House Query Prompt
def generate_custom_house_prompt(subject, visualizer):
    planets_text = get_planets_text_from_visualizer(visualizer)
    return f"""Act as a friendly, expert Vedic Astrologer. Analyze this birth chart data for client {subject.name}:

### Planetary Positions:
{planets_text}

Instructions:
- The client is asking about **House No. [INSERT HOUSE NUMBER HERE, e.g., 5th for Education/Children, 9th for Luck, etc.]**.
- Based strictly on the planets placed in that house or affecting it, explain what this house indicates for them.
- Keep the language in simple **Hinglish** (no complex English words, friendly and clear tone)."""

ai_prompt_text = generate_core_ai_prompt(subject, temp_visualizer, vedic_results)
custom_prompt_text = generate_custom_house_prompt(subject, temp_visualizer)

# 6. Initialize Final Visualizer with both Prompts
grid_visualizer = VedicGridChartVisualizer(
    subject=subject, 
    chart_data=chart_data, 
    vedic_results=vedic_results, 
    dasha_table_str=dasha_table_str,
    ai_prompt_text=ai_prompt_text,
    custom_prompt_text=custom_prompt_text
)

grid_file_path = grid_visualizer.generate_html_grid_chart(filename=f"{name}_Kundali_Report.html")

output_dir = Path("charts_output")
output_dir.mkdir(exist_ok=True)
drawer = ChartDrawer(chart_data=chart_data)
drawer.save_svg(output_path=output_dir, filename=f"{name}_kundali_chart")

print(f"\n[SUCCESS] 🌟 Comprehensive HTML Kundali Report (with Rahu, Ketu & Hinglish AI Prompts) saved in: '{grid_file_path}'")