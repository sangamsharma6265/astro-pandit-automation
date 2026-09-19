from datetime import datetime
from kerykeion import AstrologicalSubjectFactory

class VedicAnalyzer:
    def __init__(self, subject, chart_data):
        self.subject = subject
        self.chart_data = chart_data
        
        self.planets = {}
        planet_list = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']
        for p_name in planet_list:
            if hasattr(subject, p_name):
                self.planets[p_name] = getattr(subject, p_name)

    def get_house_number(self, house_str):
        if not house_str:
            return 0
        mapping = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4,
            'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8,
            'ninth': 9, 'tenth': 10, 'eleventh': 11, 'twelfth': 12
        }
        for key, val in mapping.items():
            if key in house_str.lower():
                return val
        return 0

    # 1. Manglik Dosh
    def check_manglik_dosh(self):
        mars = self.planets.get('mars')
        rule = "Mars (Mangal) placed in 1st, 4th, 7th, 8th, or 12th house from Ascendant/Moon."
        if not mars:
            return {"status": "Not Detected", "rule": rule, "reason": "Mars data unavailable.", "impact": "No Manglik impact."}
        
        h_num = self.get_house_number(getattr(mars, 'house', ''))
        if h_num in [1, 4, 7, 8, 12]:
            reason = f"Mars is physically located in House {h_num}, falling under the Manglik threshold."
            impact = "Can cause high energy, aggressiveness, or potential friction/delays in marital harmony and partnerships if remedies are ignored."
            return {"status": f"DETECTED (Mars in House {h_num})", "rule": rule, "reason": reason, "impact": impact}
        else:
            reason = f"Mars is located in House {h_num}, outside sensitive houses."
            impact = "Marital life and energy levels remain stable and balanced without malefic Manglik friction."
            return {"status": "Not Detected (Clean)", "rule": rule, "reason": reason, "impact": impact}

    # 2. Budhaditya Yog
    def check_budhaditya_yog(self):
        sun = self.planets.get('sun')
        mercury = self.planets.get('mercury')
        rule = "Sun and Mercury conjunct (placed together in the exact same house)."
        if not sun or not mercury:
            return {"status": "Not Detected", "rule": rule, "reason": "Sun or Mercury data missing.", "impact": "N/A"}
        
        s_house = getattr(sun, 'house', '')
        m_house = getattr(mercury, 'house', '')
        h_num = self.get_house_number(s_house)
        
        if s_house and s_house == m_house:
            reason = f"Both Sun and Mercury occupy House {h_num} together."
            impact = "Grants sharp intellect, excellent communication skills, strong analytical abilities, and success in business, writing, or advisory roles."
            return {"status": f"DETECTED (Conjunct in House {h_num})", "rule": rule, "reason": reason, "impact": impact}
        else:
            reason = "Sun and Mercury are placed in separate houses."
            impact = "Intellect operates independently; communication is normal without special promotional boosts."
            return {"status": "Not Detected", "rule": rule, "reason": reason, "impact": "Standard intellectual growth based on individual planetary strengths."}

    # 3. Gajakesari Yog
    def check_gajakesari_yog(self):
        moon = self.planets.get('moon')
        jupiter = self.planets.get('jupiter')
        rule = "Moon and Jupiter placed in Kendra houses (1, 4, 7, 10) relative to each other or in the same sign."
        if not moon or not jupiter:
            return {"status": "Not Detected", "rule": rule, "reason": "Moon or Jupiter data missing.", "impact": "N/A"}
        
        m_house = self.get_house_number(getattr(moon, 'house', ''))
        j_house = self.get_house_number(getattr(jupiter, 'house', ''))
        
        if m_house and j_house:
            diff = abs(m_house - j_house)
            if moon.sign == jupiter.sign or diff in [0, 3, 6, 9]:
                reason = f"Moon (Sign: {moon.sign}) and Jupiter share a harmonious Kendra relationship."
                impact = "Bestows wisdom, high social reputation, financial prosperity, respect in society, and the ability to overcome major life obstacles gracefully."
                return {"status": "DETECTED", "rule": rule, "reason": reason, "impact": impact}
            else:
                reason = "Angular distance between Moon and Jupiter does not form a Kendra aspect."
                impact = "Financial and social success depends on individual planetary dashas rather than combined yoga support."
                return {"status": "Not Detected", "rule": rule, "reason": reason, "impact": "Standard wealth and wisdom progression."}
        return {"status": "Not Detected", "rule": rule, "reason": "Insufficient house mapping.", "impact": "N/A"}

    # 4. Dhana Yog
    def check_dhana_yog(self):
        wealth_houses = [2, 5, 9, 11]
        rule = "Concentration of multiple wealth-karaka planets in auspicious wealth houses (2nd, 5th, 9th, 11th)."
        found = []
        for p_name, p_obj in self.planets.items():
            h = self.get_house_number(getattr(p_obj, 'house', ''))
            if h in wealth_houses:
                found.append(f"{p_obj.name.capitalize()} (H{h})")
                
        if len(found) >= 3:
            reason = f"Found {len(found)} key planets ({', '.join(found)}) positioned in wealth houses."
            impact = "Strong potential for accumulation of wealth, multiple sources of income, smart investments, and financial stability over time."
            return {"status": "DETECTED (Strong Wealth Flow)", "rule": rule, "reason": reason, "impact": impact}
        else:
            reason = f"Only {len(found)} planet(s) found in wealth houses."
            impact = "Balanced financial flow; wealth accumulation requires disciplined savings and careful investment planning."
            return {"status": "Moderate Wealth Flow", "rule": rule, "reason": reason, "impact": impact}

    # 5. Raja Yog
    def check_raja_yog(self):
        rule = "High concentration of planets in Kendra (1, 4, 7, 10) and Trikona (1, 5, 9) leadership houses."
        kendra_trikona_count = sum(1 for p_name, p_obj in self.planets.items() 
                                   if self.get_house_number(getattr(p_obj, 'house', '')) in [1, 4, 5, 7, 9, 10])
        if kendra_trikona_count >= 4:
            reason = f"{kendra_trikona_count} planets reside in powerful Kendra/Trikona houses."
            impact = "Promotes career authority, leadership roles, public recognition, status elevation, and successful execution of major life goals."
            return {"status": "DETECTED", "rule": rule, "reason": reason, "impact": impact}
        else:
            reason = f"Only {kendra_trikona_count} planets are placed in Kendra/Trikona houses."
            impact = "Progress in career comes through steady, consistent effort rather than sudden authoritative leaps."
            return {"status": "Weak / Standard Formation", "rule": rule, "reason": reason, "impact": impact}

    # 6. Vipreet Rajyog
    def check_vipreet_rajyog(self):
        rule = "Malefic planets (like Saturn/Mars) occupying Dusthana houses (6th, 8th, or 12th)."
        malefic_houses = [6, 8, 12]
        dusthana_malefics = []
        for p_name, p_obj in self.planets.items():
            h = self.get_house_number(getattr(p_obj, 'house', ''))
            if h in malefic_houses and p_name in ['saturn', 'mars']:
                dusthana_malefics.append(f"{p_obj.name.capitalize()} in House {h}")
                
        if len(dusthana_malefics) >= 2:
            reason = f"Strong malefics ({', '.join(dusthana_malefics)}) are placed in challenging Dusthana houses."
            impact = "Sudden unexpected breakthroughs after initial struggles, victory over competitors, and recovery from prolonged financial or health hurdles."
            return {"status": "POTENTIAL VIPREET RAJYOG", "rule": rule, "reason": reason, "impact": impact}
        else:
            reason = "Required heavy malefic configuration inside 6th, 8th, or 12th houses is incomplete."
            impact = "Standard handling of obstacles and litigation through routine legal or personal measures."
            return {"status": "Not Detected", "rule": rule, "reason": reason, "impact": "No special sudden reversal effects."}

    # 7. Real-Time Sade Sati
    def check_sade_sati(self):
        rule = "Saturn transiting through the 12th, 1st, or 2nd sign relative to the natal Moon sign."
        moon = self.planets.get('moon')
        if not moon:
            return {"status": "Not Evaluated", "rule": rule, "reason": "Moon data missing.", "impact": "N/A"}
        
        moon_sign = moon.sign
        now = datetime.now()
        
        try:
            transit_subject = AstrologicalSubjectFactory.from_birth_data(
                name="TransitCheck",
                year=now.year,
                month=now.month,
                day=now.day,
                hour=12,
                minute=0,
                lng=self.subject.lng,
                lat=self.subject.lat,
                tz_str="Asia/Kolkata",
                online=False,
                zodiac_type="Sidereal",
                sidereal_mode="LAHIRI"
            )
            saturn_transit_sign = transit_subject.saturn.sign
            zodiac_signs = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']
            
            moon_idx = zodiac_signs.index(moon_sign)
            saturn_idx = zodiac_signs.index(saturn_transit_sign)
            
            prev_sign_idx = (moon_idx - 1) % 12
            next_sign_idx = (moon_idx + 1) % 12
            
            if saturn_idx == prev_sign_idx:
                reason = f"Real-time Transit Saturn ({saturn_transit_sign}) is in the 12th sign from natal Moon ({moon_sign})."
                impact = "May bring minor sleep disturbances, increased expenditure, or mental restlessness requiring careful financial planning."
                return {"status": "ACTIVE (Phase 1)", "rule": rule, "reason": reason, "impact": impact}
            elif saturn_idx == moon_idx:
                reason = f"Real-time Transit Saturn ({saturn_transit_sign}) is directly over natal Moon ({moon_sign}) - Peak Phase."
                return {"status": "ACTIVE (Phase 2 - Peak)", "rule": rule, "reason": reason, "impact": "Brings major life lessons, emotional maturity, professional test of patience, and transformation through hard work."}
            elif saturn_idx == next_sign_idx:
                reason = f"Real-time Transit Saturn ({saturn_transit_sign}) is in the 2nd sign from natal Moon ({moon_sign})."
                impact = "Focus shifts to family finances, speech control, and stabilizing wealth after the intense peak phase."
                return {"status": "ACTIVE (Phase 3)", "rule": rule, "reason": reason, "impact": impact}
            else:
                reason = f"Transit Saturn is in {saturn_transit_sign}, while natal Moon is in {moon_sign} (Outside Sade Sati zone)."
                impact = "Mental peace, emotional stability, and professional growth flow without heavy Saturnian restrictions."
                return {"status": "NOT ACTIVE (Clear)", "rule": rule, "reason": reason, "impact": impact}
        except Exception as e:
            return {"status": "Error", "rule": rule, "reason": str(e), "impact": "N/A"}

    def analyze_all(self):
        return {
            "manglik": self.check_manglik_dosh(),
            "budhaditya": self.check_budhaditya_yog(),
            "gajakesari": self.check_gajakesari_yog(),
            "dhana": self.check_dhana_yog(),
            "raja_yog": self.check_raja_yog(),
            "vipreet": self.check_vipreet_rajyog(),
            "sade_sati": self.check_sade_sati()
        }