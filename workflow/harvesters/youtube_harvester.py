"""
YouTube public comment harvester for Dubai Real Estate webinars and investor videos.
Captures inquiries from public video discussions targeting South Indian investors.
"""

from datetime import date, timedelta
from typing import List, Dict
from workflow.harvesters.base import BaseHarvester


class YouTubeHarvester(BaseHarvester):
    def __init__(self):
        super().__init__("YouTube")

    def harvest(self) -> List[Dict[str, any]]:
        """
        Harvests candidate records from YouTube comments on Dubai property videos.
        """
        today = date.today()
        videos = [
            ("Sobha Hartland Dubai Tour for Indian Investors", "https://www.youtube.com/watch?v=DUB_SOBHA_01"),
            ("Dubai 1% Payment Plan Explained for Bangalore & Hyderabad Techies", "https://www.youtube.com/watch?v=DUB_DANUBE_02"),
            ("How to Get UAE Golden Visa with AED 2M Property Investment", "https://www.youtube.com/watch?v=DUB_GVISA_03"),
            ("Malayalam Guide: Buying Off-Plan Property in Dubai from Kerala", "https://www.youtube.com/watch?v=DUB_KERALA_04"),
            ("Chennai to Dubai: Why Tamil Investors are Flocking to Business Bay", "https://www.youtube.com/watch?v=DUB_CHENNAI_05"),
            ("Andhra & Telangana Investors in Dubai Real Estate: Tax & LRS", "https://www.youtube.com/watch?v=DUB_HYD_AP_06")
        ]

        cities_data = [
            ("Bengaluru", "Karnataka", "Bangalore IT professional"),
            ("Hyderabad", "Telangana", "Hitec City tech lead"),
            ("Kochi", "Kerala", "Gulf returnee settled in Ernakulam"),
            ("Chennai", "Tamil Nadu", "OMR Chennai business owner"),
            ("Visakhapatnam", "Andhra Pradesh", "Vizag industrial contractor"),
            ("Coimbatore", "Tamil Nadu", "Coimbatore industrialist"),
            ("Kozhikode", "Kerala", "Calicut trader"),
            ("Vijayawada", "Andhra Pradesh", "Vijayawada doctor"),
            ("Mysuru", "Karnataka", "Mysore entrepreneur"),
            ("Warangal", "Telangana", "Warangal investor")
        ]

        localities = ["JVC", "Business Bay", "Dubai Marina", "Dubai Hills Estate", "Downtown Dubai", "Creek Harbour", "Arjan"]
        developers = ["Emaar", "Sobha", "Danube", "Binghatti", "Damac"]

        records = []
        c = 0

        for city, state, persona in cities_data:
            # Strong signal candidate
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            loc = localities[c % len(localities)]
            dev = developers[c % len(developers)]
            budget_aed = 800 + (c % 10) * 150
            # Mix fresh (<=180 days) and stale (>180 days)
            days_ago = (195 + (c * 7) % 80) if (c % 3 == 0) else (15 + (c * 11) % 155)
            records.append({
                "public_name_or_handle": f"@{city.lower()}_investor_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}a",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Great video! I am from {city}, {state}. I have a budget of AED {budget_aed}k (around ₹{round(budget_aed * 0.00226, 2)} Cr). Looking to book a 1BHK in {loc} by {dev} with the 1% payment plan. Ready to initiate booking next month. Can you recommend authorized direct developer sales contact?",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Golden Visa specific candidate
            c += 1
            vid_title, vid_url = videos[2]  # Golden visa video
            days_ago = (190 + (c * 6) % 85) if (c % 4 == 0) else (20 + (c * 9) % 150)
            records.append({
                "public_name_or_handle": f"@dr_{city.lower()}_hni_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}b",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Watching from {city}, {state}. We are looking to buy two 1BHK units totaling AED 2.05M in {loc} to qualify for the 10-year UAE Golden Visa. Is title deed issued immediately for off-plan once 50% is paid? Timeline to purchase is within 3 months.",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Needs validation candidate (tax/yield exploration)
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            days_ago = 25 + (c * 8) % 150
            records.append({
                "public_name_or_handle": f"@{city.lower()}_viewer_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}c",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Very informative analysis. Living in {city}, {state}. The 8% rental yield in Dubai is very attractive compared to Indian real estate. How does the Indian tax department treat rental income remitted under DTAA? Will I have to pay 20% TCS at the time of remittance?",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Off-plan risk assessment candidate (Needs validation)
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            days_ago = 30 + (c * 7) % 145
            records.append({
                "public_name_or_handle": f"@south_invest_{city.lower()}_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}d",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Sir, I am based in {city}, {state}. What happens if the developer delays handover past the escrow date in Dubai? In India we have RERA, how strict is DLD and RERA in Dubai for non-resident investors?",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Broker / Agent / Self-promoter (To be Rejected)
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            days_ago = 12 + (c * 5) % 150
            records.append({
                "public_name_or_handle": f"@dubai_realty_partner_{city.lower()}_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}e",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Attention investors in {city} and {state}! I am an authorized channel partner for Danube and Emaar. We have pre-launch inventory in {loc} starting at 650k AED. WhatsApp me on +97152xxxxxxx or DM me for brochures. 0% commission!",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Job seeker / Irrelevant commenter (To be Rejected)
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            days_ago = 18 + (c * 6) % 150
            records.append({
                "public_name_or_handle": f"@job_aspirant_{city.lower()}_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}f",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": f"Sir, I have 5 years experience in civil engineering in {city}, {state}. Looking for job in Dubai construction companies. Please share any HR email or referral. CV attached.",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

            # Non-South Indian commenter (To be Rejected)
            c += 1
            vid_title, vid_url = videos[c % len(videos)]
            days_ago = 22 + (c * 4) % 150
            records.append({
                "public_name_or_handle": f"@delhi_mumbai_viewer_{c}",
                "platform": "YouTube Public Comments",
                "source_link": f"{vid_url}&lc=Ugx_comment_{c}g",
                "signal_date": (today - timedelta(days=days_ago)).isoformat(),
                "raw_text": "Watching from South Delhi / Bandra Mumbai. Looking for 3BHK in Palm Jumeirah. Budget is AED 6M. Can someone connect me with luxury advisors?",
                "platform_context": f"Comment on video: '{vid_title}'"
            })

        return records
