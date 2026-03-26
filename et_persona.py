PERSONA_JOURNEYS = [
    {
        "id": "journey_rookie",
        "persona": "The Rookie (Retail / First-time Investor)",
        "content": "A 22–25 year old first-time investor who just started earning. Struggles with jargon overload and fear of losing capital. Ideal journey starts with ET Money for SIPs, moving to ET Masterclass for basics, and ET Prime for simplified explainers.",
        "metadata": {
            "type": "persona_journey",
            "sophistication": "beginner",
            "profession": "salaried_employee",
            "goal": "wealth_building",
            "journey_steps": ["ET Money", "ET Masterclass", "ET Prime"],
            "avoid": ["Intraday trading", "complex derivatives", "HNI products"]
        }
    },
    {
        "id": "journey_wealth_builder",
        "persona": "The Wealth Builder (Mutual Fund Investor)",
        "content": "A 30–40 year old steady earner focused on long-term CAGR. Struggles with portfolio rebalancing and tax leakage. Journey involves ET Money for health checks, ET Markets for tracking, and ET Prime for macro trends.",
        "metadata": {
            "type": "persona_journey",
            "sophistication": "intermediate",
            "intent": "investing",
            "goal": "wealth_building",
            "journey_steps": ["ET Money", "ET Markets", "ET Prime"],
            "avoid": ["Penny stocks", "high-risk crypto", "get rich quick webinars"]
        }
    },
    {
        "id": "journey_scaler",
        "persona": "The Scaler (SME Owner)",
        "content": "SME owner looking to modernize and scale. Needs access to MSME loans, GST compliance, and digital transformation. Journey: ET Rise for funding news, ET Government for schemes, and ET Masterclass for digital skills.",
        "metadata": {
            "type": "persona_journey",
            "profession": "sme_owner",
            "goal": "business_scaling",
            "journey_steps": ["ET Rise", "ET Government", "ET Masterclass"],
            "avoid": ["Large-cap M&A", "high-frequency trading"]
        }
    },
    {
        "id": "journey_strategist",
        "persona": "The Strategist (CXO)",
        "content": "Senior executive with 15+ years experience. Focused on disruption, talent, and geopolitical risk. Uses ET Prime for strategy, ET Events for networking, and ET BrandEquity for consumer trends.",
        "metadata": {
            "type": "persona_journey",
            "profession": "cxo",
            "sophistication": "expert",
            "goal": "professional_authority",
            "journey_steps": ["ET Prime", "ET Events", "ET BrandEquity"],
            "avoid": ["Basic investing guides", "entry-level job alerts"]
        }
    },
    {
        "id": "journey_innovator",
        "persona": "The Innovator (Startup Founder)",
        "content": "Early-stage founder focused on fundraising and hiring. Needs VC eyes and regulatory clarity. Journey: ET Prime for startup tracking, ET Rise for networking, and ET Masterclass for growth hacking.",
        "metadata": {
            "type": "persona_journey",
            "profession": "startup_founder",
            "intent": "growing_business",
            "journey_steps": ["ET Prime", "ET Rise", "ET Masterclass"],
            "avoid": ["Legacy PSU news", "fixed-income products"]
        }
    },
    {
        "id": "journey_nri",
        "persona": "The Global Indian (NRI)",
        "content": "NRI living abroad looking at Indian investments. Concerned with taxation (NRE/NRO) and FEMA. Uses ET Now for live forex, ET Markets for stocks, and ET TravelWorld for visit trends.",
        "metadata": {
            "type": "persona_journey",
            "persona_type": "nri",
            "goal": "protecting_wealth",
            "journey_steps": ["ET Now", "ET Markets", "ET TravelWorld"],
            "avoid": ["Local city municipality news"]
        }
    },
    {
        "id": "journey_day_mover",
        "persona": "The Day Mover (Active Trader)",
        "content": "Full-time trader focused on technical patterns and execution speed. Needs real-time data and sentiment. Uses ET Markets for charts, ET Now for live segments, and ET Prime for sectoral analysis.",
        "metadata": {
            "type": "persona_journey",
            "profession": "active_trader",
            "intent": "investing",
            "journey_steps": ["ET Markets", "ET Now", "ET Prime"],
            "avoid": ["Long-form blogs", "10-year lock-in products"]
        }
    },
    {
        "id": "journey_policy_watcher",
        "persona": "The Policy Watcher (IAS / Policy Maker)",
        "content": "Government official tracking e-governance and policy benchmarks. Needs case studies and inter-state success stories. Journey: ET Government, ET Masterclass (AI in Gov), and ET Now debates.",
        "metadata": {
            "type": "persona_journey",
            "profession": "policy_maker",
            "interest": "e_governance",
            "journey_steps": ["ET Government", "ET Masterclass", "ET Now"],
            "avoid": ["Consumer deals", "lifestyle travel"]
        }
    },
    {
        "id": "journey_high_flyer",
        "persona": "The High-Flyer (HNI)",
        "content": "HNI with net worth > 5Cr focused on alpha and estate planning. Needs bespoke services and inheritance tax clarity. Uses ET Markets (Premium), ET Events (CXO Roundtables), and ET Prime.",
        "metadata": {
            "type": "persona_journey",
            "persona_type": "hni",
            "goal": "protecting_wealth",
            "journey_steps": ["ET Markets", "ET Events", "ET Prime"],
            "avoid": ["Small-ticket SIP campaigns"]
        }
    },
    {
        "id": "journey_career_starter",
        "persona": "The Career Starter (Student)",
        "content": "Final year student or young professional. Needs business context and upskilling. Uses ET Masterclass for certificates, ET Prime for interview prep, and ET BrandEquity for marketing trends.",
        "metadata": {
            "type": "persona_journey",
            "persona_type": "student",
            "goal": "career_growth",
            "journey_steps": ["ET Masterclass", "ET Prime", "ET BrandEquity"],
            "avoid": ["Retirement planning", "high-ticket property"]
        }
    },
    {
        "id": "journey_travel_enthusiast",
        "persona": "The Travel Enthusiast (Corporate Traveler)",
        "content": "Corporate professional/HNI frequent flyer. Focused on loyalty, visas, and wellness. Uses ET TravelWorld for aviation, ET Prime for hospitality, and ET Now for luxury lifestyle.",
        "metadata": {
            "type": "persona_journey",
            "interest": "hospitality",
            "profession": "corporate_professional",
            "journey_steps": ["ET TravelWorld", "ET Prime", "ET Now"],
            "avoid": ["Budget backpacking", "low-tier rail news"]
        }
    },
    {
        "id": "journey_marketing_maven",
        "persona": "The Marketing Maven (Brand Leader)",
        "content": "CMO/Creative Director focused on ROI and AI in ads. Needs consumer behavior shifts. Uses ET BrandEquity for campaigns, ET Masterclass for MarTech, and ET Prime for insights.",
        "metadata": {
            "type": "persona_journey",
            "profession": "marketing_head",
            "intent": "news",
            "journey_steps": ["ET BrandEquity", "ET Masterclass", "ET Prime"],
            "avoid": ["Stock market technicals", "MSME tax tips"]
        }
    },
    {
        "id": "journey_tech_architect",
        "persona": "The Tech Architect (IT Pro)",
        "content": "CTO/Lead Dev focused on tech stack and cybersecurity. Uses ET Prime for tech deep-dives, ET Masterclass for AI leadership, and ET Events for tech summits.",
        "metadata": {
            "type": "persona_journey",
            "interest": "ai",
            "profession": "corporate_professional",
            "journey_steps": ["ET Prime", "ET Masterclass", "ET Events"],
            "avoid": ["Commodity markets", "agriculture policy"]
        }
    },
    {
        "id": "journey_retail_manager",
        "persona": "The Retail Manager (Salaried Employee)",
        "content": "Mid-level manager focused on family security, home loans, and insurance. Uses ET Money for Genius/Insurance, ET Now for finance debates, and ET Markets for tax funds.",
        "metadata": {
            "type": "persona_journey",
            "profession": "salaried_employee",
            "goal": "saving_specific",
            "journey_steps": ["ET Money", "ET Now", "ET Markets"],
            "avoid": ["High-risk small-cap tips"]
        }
    },
    {
        "id": "journey_real_estate",
        "persona": "The Real Estate Investor",
        "content": "Individual diversifying into physical assets. Needs RERA compliance and yield analysis. Uses ET Prime (Real Estate), ET Markets (REITs), and ET Government (Infra updates).",
        "metadata": {
            "type": "persona_journey",
            "interest": "smart_infrastructure",
            "intent": "investing",
            "journey_steps": ["ET Prime", "ET Markets", "ET Government"],
            "avoid": ["Daily crypto", "fast-fashion trends"]
        }
    }
]