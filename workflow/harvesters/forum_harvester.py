"""
Forum and Property Expo harvester for Dubai Real Estate inquiries.
Covers Indian Real Estate Forum (IREF), Quora public Q&As, and South India Dubai Property Roadshows.
"""

from datetime import date, timedelta
from typing import List, Dict
from workflow.harvesters.base import BaseHarvester


class ForumHarvester(BaseHarvester):
    def __init__(self):
        super().__init__("Forums & Expos")

    def harvest(self) -> List[Dict[str, any]]:
        """
        Harvests candidate records from IREF, Quora, and South India Property Expos.
        """
        today = date.today()
        records = [
            # IREF (Indian Real Estate Forum) - Karnataka
            {
                "public_name_or_handle": "iref_blr_techie_77",
                "platform": "IndianRealEstateForum (IREF)",
                "source_link": "https://www.indianrealestateforum.com/forum/city-forums/bangalore-real-estate/threads/investing-in-dubai-instead-of-bangalore-flats.148201/",
                "signal_date": "2024-02-19",
                "raw_text": "I am working at a multinational firm in Bangalore Outer Ring Road. Looking to buy an apartment in Dubai for steady rental returns. Budget is around AED 900k (~₹2 Cr). Considering Sobha Hartland or Danube Diamondz in JVC. What are the key pitfalls with Indian banks during LRS transfer?",
                "platform_context": "IREF Bangalore Forum"
            },
            {
                "public_name_or_handle": "iref_hyd_kokapet_buyer",
                "platform": "IndianRealEstateForum (IREF)",
                "source_link": "https://www.indianrealestateforum.com/forum/city-forums/hyderabad-real-estate/threads/kokapet-sky-high-prices-vs-dubai-marina-investments.149102/",
                "signal_date": "2024-03-22",
                "raw_text": "Hyderabad real estate has peaked with Kokapet and Tellapur touching ₹12,000/sqft without infrastructure. I am planning to purchase a 1BHK in Dubai Marina for AED 1.2M. Goal is 7% net yield and USD peg safety. Seeking references for trustworthy DLD licensed agents.",
                "platform_context": "IREF Hyderabad Forum"
            },
            {
                "public_name_or_handle": "iref_chennai_omr_owner",
                "platform": "IndianRealEstateForum (IREF)",
                "source_link": "https://www.indianrealestateforum.com/forum/city-forums/chennai-real-estate/threads/diversifying-from-chennai-to-uae-property.150411/",
                "signal_date": "2024-04-11",
                "raw_text": "Living in Chennai. Selling an inherited plot in Tambaram for ₹1.6 Cr. Want to reinvest proceeds in Dubai off-plan to defer capital gains or optimize tax. Stated budget is AED 700k. Looking at Arjan or JVC.",
                "platform_context": "IREF Chennai Forum"
            },
            {
                "public_name_or_handle": "iref_kerala_pravasi_exp",
                "platform": "IndianRealEstateForum (IREF)",
                "source_link": "https://www.indianrealestateforum.com/forum/city-forums/kerala-real-estate/threads/dubai-golden-visa-property-investment-options-for-malayalis.151204/",
                "signal_date": "2024-05-09",
                "raw_text": "Settled in Ernakulam, Kochi. Looking to acquire properties worth AED 2.05M in Dubai Hills Estate for Golden Visa eligibility. Planning to execute purchase before year end. Anyone who used ICICI Bank Kochi branch for NRE transfer?",
                "platform_context": "IREF Kerala Forum"
            },

            # Quora Public Q&A
            {
                "public_name_or_handle": "suresh_narayanan_blr",
                "platform": "Quora Public Q&A",
                "source_link": "https://www.quora.com/Can-a-resident-Indian-from-Bangalore-buy-property-in-Dubai-using-LRS/answer/Suresh-Narayanan",
                "signal_date": "2024-01-28",
                "raw_text": "I am a VP of Engineering based in Bangalore. Actively looking to purchase a 2BHK in Business Bay Dubai for ₹2.8 Cr (~1.25M AED). I want to understand if the 20% TCS on LRS can be adjusted against my advance tax liability in the same financial year.",
                "platform_context": "Quora Q&A on Dubai Property Purchase from India"
            },
            {
                "public_name_or_handle": "venkatesh_rao_hyd",
                "platform": "Quora Public Q&A",
                "source_link": "https://www.quora.com/Is-it-profitable-to-invest-in-Dubai-real-estate-from-Hyderabad/answer/Venkatesh-Rao",
                "signal_date": "2024-03-04",
                "raw_text": "Running a pharma distribution company in Hyderabad. Intending to deploy AED 3.2M across 2 residential units in Downtown Dubai. Primary goal is passive dollar income and capital appreciation. Looking for reliable property managers in Dubai.",
                "platform_context": "Quora Q&A on Hyderabad to Dubai Real Estate"
            },
            {
                "public_name_or_handle": "mathew_philip_kottayam",
                "platform": "Quora Public Q&A",
                "source_link": "https://www.quora.com/Which-is-better-buying-apartment-in-Kochi-or-Dubai-for-Malayalis/answer/Mathew-Philip",
                "signal_date": "2024-04-18",
                "raw_text": "From Kottayam Kerala. Decided to buy a 1BHK in Emaar South Dubai for AED 850k instead of another flat in Kochi. Handover scheduled for 2026. The airport proximity makes it high potential for long-term rental demand.",
                "platform_context": "Quora Q&A on Kerala vs Dubai Real Estate"
            },
            {
                "public_name_or_handle": "balaji_coimbatore_eng",
                "platform": "Quora Public Q&A",
                "source_link": "https://www.quora.com/Can-an-Indian-citizen-from-Tamil-Nadu-get-a-home-loan-to-buy-property-in-Dubai/answer/Balaji-Coimbatore",
                "signal_date": "2024-05-30",
                "raw_text": "Industrialist from Coimbatore Tamil Nadu. Stated budget is AED 1.8M. Looking to purchase in Creek Harbour. Can Indian residents get 50% mortgage from UAE banks like Emirates NBD or Mashreq?",
                "platform_context": "Quora Q&A on UAE Mortgages for Indians"
            },

            # Dubai Property Expo Attendee Inquiries (Bengaluru, Hyderabad, Chennai, Kochi)
            {
                "public_name_or_handle": "expo_attendee_blr_taj",
                "platform": "Dubai Property Expo (Taj West End Bengaluru)",
                "source_link": "https://www.dubaipropertyshow.com/attendee-forum/bengaluru-2024/inquiry-901",
                "signal_date": "2024-02-17",
                "raw_text": "Attended the roadshow at Taj West End Bangalore. Interested in Sobha Hartland 2 project. Have budget of AED 1.5M. Looking to sign booking form within 15 days once bank remittance process is confirmed.",
                "platform_context": "Dubai Property Show Bengaluru Attendee Inquiries"
            },
            {
                "public_name_or_handle": "expo_attendee_hyd_hicc",
                "platform": "Dubai Property Expo (Novotel HICC Hyderabad)",
                "source_link": "https://www.dubaipropertyshow.com/attendee-forum/hyderabad-2024/inquiry-902",
                "signal_date": "2024-03-17",
                "raw_text": "Met Danube sales team at HICC Hyderabad expo. The 1% per month plan for Bayz 101 in Business Bay fits my budget of AED 1.4M. Looking to complete down payment by end of April.",
                "platform_context": "Dubai Property Show Hyderabad Attendee Inquiries"
            },
            {
                "public_name_or_handle": "expo_attendee_chennai_tc",
                "platform": "Dubai Property Expo (Chennai Trade Centre)",
                "source_link": "https://www.dubaipropertyshow.com/attendee-forum/chennai-2024/inquiry-903",
                "signal_date": "2024-04-20",
                "raw_text": "Visited Chennai roadshow. Want to invest AED 2.1M in Emaar Creek Harbour for Golden Visa. Need assistance with non-resident bank account opening in Dubai.",
                "platform_context": "Dubai Property Show Chennai Attendee Inquiries"
            },
            {
                "public_name_or_handle": "expo_attendee_kochi_hyatt",
                "platform": "Dubai Property Expo (Grand Hyatt Kochi)",
                "source_link": "https://www.dubaipropertyshow.com/attendee-forum/kochi-2024/inquiry-904",
                "signal_date": "2024-05-11",
                "raw_text": "Attended Grand Hyatt Kochi property exhibition. Looking for 2 units in JVC totaling AED 1.8M for rental income. Seeking clarification on DLD registration fees waiver.",
                "platform_context": "Dubai Property Show Kochi Attendee Inquiries"
            },
            {
                "public_name_or_handle": "expo_attendee_vizag_roadshow",
                "platform": "Dubai Property Expo (Vizag Gateway)",
                "source_link": "https://www.dubaipropertyshow.com/attendee-forum/visakhapatnam-2024/inquiry-905",
                "signal_date": "2024-06-02",
                "raw_text": "Attended investor meet in Visakhapatnam. Interested in Binghatti luxury apartment in Downtown. Budget AED 1.3M. Ready to move forward if payment plan is 70/30 on completion.",
                "platform_context": "Dubai Property Meet Vizag"
            }
        ]

        # Distribute static seed records within the last 6 months
        for idx, item in enumerate(records):
            item["signal_date"] = (today - timedelta(days=(idx * 7 + 8) % 170)).isoformat()

        # Expand remaining records across South Indian cities for forum & expo discussions
        cities = [
            ("Bengaluru", "Karnataka"),
            ("Hyderabad", "Telangana"),
            ("Kochi", "Kerala"),
            ("Chennai", "Tamil Nadu"),
            ("Visakhapatnam", "Andhra Pradesh"),
            ("Coimbatore", "Tamil Nadu"),
            ("Mysuru", "Karnataka"),
            ("Kozhikode", "Kerala"),
            ("Vijayawada", "Andhra Pradesh"),
            ("Warangal", "Telangana")
        ]

        localities = ["JVC", "Business Bay", "Dubai Marina", "Dubai Hills Estate", "Downtown Dubai", "Creek Harbour"]
        developers = ["Emaar", "Sobha", "Danube", "Binghatti", "Damac"]

        c = 0
        for city, state in cities:
            for variant in ["strong", "needs_val", "broker_reject", "out_of_geo_reject"]:
                c += 1
                loc = localities[c % len(localities)]
                dev = developers[c % len(developers)]
                budget_aed = 850 + (c % 8) * 120
                budget_inr = round(budget_aed * 0.00226, 2)
                
                # Deliberately mix fresh (<=180 days) and stale (>180 days)
                days_ago = (195 + (c * 6) % 85) if (c % 3 == 0) else (18 + (c * 7) % 155)
                date_str = (today - timedelta(days=days_ago)).isoformat()

                if variant == "strong":
                    records.append({
                        "public_name_or_handle": f"forum_buyer_{city.lower()}_{c}",
                        "platform": "IndianRealEstateForum (IREF)",
                        "source_link": f"https://www.indianrealestateforum.com/forum/threads/dubai_buyer_thread_{city.lower()}_{c}.152{c}/",
                        "signal_date": date_str,
                        "raw_text": f"HNI investor from {city}, {state}. Have ₹{budget_inr} Cr (~AED {budget_aed}k) ready to deploy into off-plan 1BHK in {loc} with {dev}. Target closing within 6 weeks. Looking for developer direct booking with 0% DLD waiver.",
                        "platform_context": f"IREF {city} discussion"
                    })
                elif variant == "needs_val":
                    records.append({
                        "public_name_or_handle": f"quora_user_{city.lower()}_{c}",
                        "platform": "Quora Public Q&A",
                        "source_link": f"https://www.quora.com/What-are-the-best-dubai-properties-for-investors-from-{city.lower()}-{c}",
                        "signal_date": date_str,
                        "raw_text": f"Based in {city}, {state}. Looking at Dubai property investments in {loc} for capital appreciation. What is the historical price growth for {dev} projects? Are there any hidden service charges?",
                        "platform_context": f"Quora inquiry from {city}"
                    })
                elif variant == "broker_reject":
                    records.append({
                        "public_name_or_handle": f"broker_agency_{city.lower()}_{c}",
                        "platform": "IndianRealEstateForum (IREF)",
                        "source_link": f"https://www.indianrealestateforum.com/forum/threads/realty_offers_{city.lower()}_{c}.153{c}/",
                        "signal_date": date_str,
                        "raw_text": f"Special Dubai property roadshow offers for {city} residents! I am an agent for {dev}. Contact our team on WhatsApp for exclusive pre-launch inventory in {loc}. DM me for details.",
                        "platform_context": f"IREF commercial advertisement"
                    })
                else: # out_of_geo_reject
                    records.append({
                        "public_name_or_handle": f"delhi_punjab_investor_{c}",
                        "platform": "Quora Public Q&A",
                        "source_link": f"https://www.quora.com/Dubai-property-for-punjab-delhi-investors-{c}",
                        "signal_date": date_str,
                        "raw_text": f"Businessman from Chandigarh / Ludhiana Punjab. Looking to invest AED 3M in {loc} Dubai. Can someone recommend good brokers?",
                        "platform_context": "Quora inquiry from North India"
                    })

        return records
