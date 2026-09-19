from datetime import datetime, timedelta

class DashaGenerator:
    DASHA_YEARS = {
        "Ketu": 7,
        "Venus": 20,
        "Sun": 6,
        "Moon": 10,
        "Mars": 7,
        "Rahu": 18,
        "Jupiter": 16,
        "Saturn": 19,
        "Mercury": 17
    }
    
    LORDS_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    
    NAKSHATRA_LORDS = [
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
    ]

    def __init__(self, subject):
        self.subject = subject
        self.birth_year = subject.year
        self.birth_month = subject.month
        self.birth_day = subject.day
        self.moon = getattr(subject, 'moon', None)

    def format_date(self, dt):
        """Dates ko '20 Oct 2004' format mein convert karta hai"""
        return dt.strftime("%d %b %Y")

    def get_birth_dasha_info(self):
        if not self.moon:
            return "Ketu", 7.0, 0.0
        
        abs_pos = getattr(self.moon, 'abs_pos', 0.0)
        nakshatra_span = 360.0 / 27.0
        
        nak_index = int(abs_pos / nakshatra_span)
        if nak_index > 26: nak_index = 26
        
        elapsed_in_nak = abs_pos % nakshatra_span
        remaining_fraction = (nakshatra_span - elapsed_in_nak) / nakshatra_span
        
        lord = self.NAKSHATRA_LORDS[nak_index]
        total_years = self.DASHA_YEARS[lord]
        balance_years = total_years * remaining_fraction
        
        return lord, total_years, balance_years

    def generate_100_year_table(self):
        start_lord, total_y, balance_y = self.get_birth_dasha_info()
        start_idx = self.LORDS_SEQUENCE.index(start_lord)
        
        current_date = datetime(self.birth_year, self.birth_month, self.birth_day)
        
        table_lines = []
        table_lines.append(f"{'MAHADASHA / ANTARDASHA':<30} | {'START DATE':<12} | {'END DATE':<12}")
        table_lines.append("-" * 60)
        
        years_covered = 0.0
        curr_maha_idx = start_idx
        
        # Pehli dasha ke liye balance handling ya full loop 100 saal tak
        # Hum 100 saal tak mahadasha aur uske andar ki antardasha generate karenge
        while years_covered < 100:
            maha_lord = self.LORDS_SEQUENCE[curr_maha_idx]
            maha_total_years = self.DASHA_YEARS[maha_lord]
            
            # Agar pehli dasha hai toh balance years lenge, warna poore saal
            if years_covered == 0.0:
                maha_span = balance_y
                # Antardasha start index ko adjust karne ke liye calculation
                # (Balance ke hisaab se antardasha beech se shuru ho sakti hai, par simplicity ke liye maha start se map karenge)
            else:
                maha_span = maha_total_years
                
            maha_start_date = current_date
            maha_end_date = maha_start_date + timedelta(days=int(maha_span * 365.25))
            
            # Mahadasha header line
            table_lines.append(f"► {maha_lord} Mahadasha ({maha_span:4.1f} Yrs)          | {self.format_date(maha_start_date):<12} | {self.format_date(maha_end_date):<12}")
            
            # Sub-loop for Antardashas inside this Mahadasha
            # Antardasha proportional duration = (Maha_Years * Anta_Years) / 120
            antardasha_start = maha_start_date
            
            # Antardasha sequence starts from Mahadasha lord itself in Vedic rules
            anta_idx = self.LORDS_SEQUENCE.index(maha_lord)
            
            for _ in range(9):
                anta_lord = self.LORDS_SEQUENCE[anta_idx]
                anta_duration_years = (maha_total_years * self.DASHA_YEARS[anta_lord]) / 120.0
                anta_end = antardasha_start + timedelta(days=int(anta_duration_years * 365.25))
                
                # Agar antardasha 100 saal ke limit se bahar ja rahi hai ya maha end se cross ho rahi hai toh clamp kar sakte hain
                table_lines.append(f"    • {maha_lord} -> {anta_lord} Antardasha    | {self.format_date(antardasha_start):<12} | {self.format_date(anta_end):<12}")
                
                antardasha_start = anta_end
                anta_idx = (anta_idx + 1) % len(self.LORDS_SEQUENCE)
            
            table_lines.append("-" * 60)
            
            current_date = maha_end_date
            years_covered += maha_span
            curr_maha_idx = (curr_maha_idx + 1) % len(self.LORDS_SEQUENCE)
            
        return "\n".join(table_lines)