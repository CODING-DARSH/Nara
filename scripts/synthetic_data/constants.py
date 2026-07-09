"""
NARA Synthetic Data Generator — Constants & Distributions
All probabilities sourced from:
  - ICMR-NIN "What India Eats" 2021
  - NFHS-5 National Family Health Survey 2021
  - Census of India 2011
  - MOSPI Household Consumption Survey 2022
  - Published food behaviour research (Indian Journal of Community Medicine)
"""

# ── India States with population weights ─────────────────────
# Source: Census 2011 population proportions
STATE_POPULATION_WEIGHTS = {
    "Uttar Pradesh":        0.166,
    "Maharashtra":          0.096,
    "Bihar":                0.086,
    "West Bengal":          0.076,
    "Madhya Pradesh":       0.060,
    "Rajasthan":            0.057,
    "Tamil Nadu":           0.056,
    "Karnataka":            0.050,
    "Gujarat":              0.050,
    "Andhra Pradesh":       0.049,
    "Telangana":            0.029,
    "Odisha":               0.035,
    "Kerala":               0.027,
    "Jharkhand":            0.026,
    "Assam":                0.026,
    "Punjab":               0.023,
    "Haryana":              0.021,
    "Delhi":                0.013,
    "Chhattisgarh":         0.021,
    "Uttarakhand":          0.008,
    "Himachal Pradesh":     0.006,
    "Tripura":              0.003,
    "Meghalaya":            0.002,
    "Manipur":              0.002,
    "Nagaland":             0.002,
    "Goa":                  0.001,
    "Arunachal Pradesh":    0.001,
    "Sikkim":               0.001,
}

# ── State to Region mapping ───────────────────────────────────
STATE_REGION = {
    "Tamil Nadu": "south", "Karnataka": "south", "Kerala": "south",
    "Andhra Pradesh": "south", "Telangana": "south",
    "Uttar Pradesh": "north", "Bihar": "north", "Rajasthan": "north",
    "Punjab": "north", "Haryana": "north", "Delhi": "north",
    "Madhya Pradesh": "north", "Uttarakhand": "north",
    "Himachal Pradesh": "north", "Chhattisgarh": "north",
    "Jharkhand": "north",
    "Maharashtra": "west", "Gujarat": "west", "Goa": "west",
    "West Bengal": "east", "Odisha": "east", "Assam": "east",
    "Tripura": "east", "Meghalaya": "northeast", "Manipur": "northeast",
    "Nagaland": "northeast", "Arunachal Pradesh": "northeast",
    "Sikkim": "northeast",
}

# ── Major cities by state with tier ──────────────────────────
STATE_CITIES = {
    "Tamil Nadu":       [("Chennai", 1), ("Coimbatore", 2), ("Madurai", 2), ("Salem", 3), ("Tiruchirappalli", 2)],
    "Karnataka":        [("Bangalore", 1), ("Mysore", 2), ("Hubli", 2), ("Mangalore", 2), ("Belgaum", 3)],
    "Kerala":           [("Kochi", 2), ("Thiruvananthapuram", 2), ("Kozhikode", 2), ("Thrissur", 2), ("Kollam", 3)],
    "Andhra Pradesh":   [("Visakhapatnam", 2), ("Vijayawada", 2), ("Guntur", 2), ("Tirupati", 2), ("Kurnool", 3)],
    "Telangana":        [("Hyderabad", 1), ("Warangal", 2), ("Nizamabad", 3), ("Karimnagar", 3)],
    "Uttar Pradesh":    [("Lucknow", 2), ("Kanpur", 2), ("Agra", 2), ("Varanasi", 2), ("Prayagraj", 2), ("Meerut", 2)],
    "Bihar":            [("Patna", 2), ("Gaya", 3), ("Bhagalpur", 3), ("Muzaffarpur", 3)],
    "Rajasthan":        [("Jaipur", 2), ("Jodhpur", 2), ("Udaipur", 2), ("Kota", 2), ("Ajmer", 3)],
    "Punjab":           [("Ludhiana", 2), ("Amritsar", 2), ("Jalandhar", 2), ("Patiala", 3)],
    "Haryana":          [("Gurugram", 1), ("Faridabad", 2), ("Panipat", 3), ("Ambala", 3)],
    "Delhi":            [("New Delhi", 1), ("Noida", 1), ("Ghaziabad", 2)],
    "Maharashtra":      [("Mumbai", 1), ("Pune", 1), ("Nagpur", 2), ("Nashik", 2), ("Aurangabad", 2)],
    "Gujarat":          [("Ahmedabad", 1), ("Surat", 1), ("Vadodara", 2), ("Rajkot", 2), ("Gandhinagar", 2)],
    "Goa":              [("Panaji", 2), ("Margao", 2), ("Vasco", 3)],
    "West Bengal":      [("Kolkata", 1), ("Howrah", 2), ("Durgapur", 2), ("Asansol", 2), ("Siliguri", 2)],
    "Odisha":           [("Bhubaneswar", 2), ("Cuttack", 2), ("Rourkela", 2), ("Berhampur", 3)],
    "Assam":            [("Guwahati", 2), ("Silchar", 3), ("Dibrugarh", 3)],
    "Madhya Pradesh":   [("Bhopal", 2), ("Indore", 2), ("Jabalpur", 2), ("Gwalior", 2)],
    "Chhattisgarh":     [("Raipur", 2), ("Bhilai", 2), ("Bilaspur", 3)],
    "Jharkhand":        [("Ranchi", 2), ("Jamshedpur", 2), ("Dhanbad", 2)],
    "Uttarakhand":      [("Dehradun", 2), ("Haridwar", 3), ("Roorkee", 3)],
    "Himachal Pradesh": [("Shimla", 2), ("Dharamshala", 3), ("Solan", 3)],
    "Tripura":          [("Agartala", 2)],
    "Meghalaya":        [("Shillong", 2)],
    "Manipur":          [("Imphal", 2)],
    "Nagaland":         [("Kohima", 2), ("Dimapur", 3)],
    "Arunachal Pradesh":[("Itanagar", 3)],
    "Sikkim":           [("Gangtok", 3)],
}

# ── Religion distribution by state ───────────────────────────
# Source: Census 2011
STATE_RELIGION_DIST = {
    "Tamil Nadu":       {"hindu": 0.875, "muslim": 0.057, "christian": 0.062, "other": 0.006},
    "Karnataka":        {"hindu": 0.840, "muslim": 0.128, "christian": 0.019, "other": 0.013},
    "Kerala":           {"hindu": 0.549, "muslim": 0.267, "christian": 0.183, "other": 0.001},
    "Andhra Pradesh":   {"hindu": 0.900, "muslim": 0.091, "christian": 0.007, "other": 0.002},
    "Telangana":        {"hindu": 0.854, "muslim": 0.127, "christian": 0.015, "other": 0.004},
    "Uttar Pradesh":    {"hindu": 0.794, "muslim": 0.194, "christian": 0.003, "other": 0.009},
    "Bihar":            {"hindu": 0.826, "muslim": 0.168, "christian": 0.001, "other": 0.005},
    "Rajasthan":        {"hindu": 0.889, "muslim": 0.095, "jain": 0.013, "other": 0.003},
    "Punjab":           {"hindu": 0.384, "muslim": 0.019, "sikh": 0.578, "christian": 0.011, "other": 0.008},
    "Haryana":          {"hindu": 0.874, "muslim": 0.072, "sikh": 0.045, "other": 0.009},
    "Delhi":            {"hindu": 0.818, "muslim": 0.129, "sikh": 0.040, "christian": 0.008, "other": 0.005},
    "Maharashtra":      {"hindu": 0.797, "muslim": 0.115, "buddhist": 0.059, "jain": 0.013, "christian": 0.010, "other": 0.006},
    "Gujarat":          {"hindu": 0.889, "muslim": 0.097, "jain": 0.010, "other": 0.004},
    "Goa":              {"hindu": 0.665, "muslim": 0.082, "christian": 0.252, "other": 0.001},
    "West Bengal":      {"hindu": 0.706, "muslim": 0.277, "christian": 0.006, "other": 0.011},
    "Odisha":           {"hindu": 0.933, "muslim": 0.025, "christian": 0.026, "other": 0.016},
    "Assam":            {"hindu": 0.613, "muslim": 0.343, "christian": 0.038, "other": 0.006},
    "Madhya Pradesh":   {"hindu": 0.907, "muslim": 0.068, "jain": 0.009, "other": 0.016},
    "Chhattisgarh":     {"hindu": 0.937, "muslim": 0.021, "christian": 0.019, "other": 0.023},
    "Jharkhand":        {"hindu": 0.677, "muslim": 0.147, "christian": 0.046, "other": 0.130},
    "Uttarakhand":      {"hindu": 0.852, "muslim": 0.140, "sikh": 0.003, "other": 0.005},
    "Himachal Pradesh": {"hindu": 0.955, "muslim": 0.021, "sikh": 0.012, "other": 0.012},
    "Tripura":          {"hindu": 0.832, "muslim": 0.085, "christian": 0.036, "other": 0.047},
    "Meghalaya":        {"hindu": 0.115, "muslim": 0.043, "christian": 0.836, "other": 0.006},
    "Manipur":          {"hindu": 0.413, "muslim": 0.086, "christian": 0.411, "other": 0.090},
    "Nagaland":         {"hindu": 0.080, "christian": 0.880, "muslim": 0.020, "other": 0.020},
    "Arunachal Pradesh":{"hindu": 0.341, "christian": 0.306, "buddhist": 0.252, "other": 0.101},
    "Sikkim":           {"hindu": 0.578, "buddhist": 0.278, "christian": 0.099, "other": 0.045},
}

# ── Mother tongue by state ────────────────────────────────────
STATE_MOTHER_TONGUE = {
    "Tamil Nadu": ["Tamil"], "Karnataka": ["Kannada", "Telugu", "Tulu"],
    "Kerala": ["Malayalam"], "Andhra Pradesh": ["Telugu"],
    "Telangana": ["Telugu", "Urdu"], "Uttar Pradesh": ["Hindi", "Urdu", "Bhojpuri"],
    "Bihar": ["Hindi", "Bhojpuri", "Maithili"], "Rajasthan": ["Hindi", "Rajasthani"],
    "Punjab": ["Punjabi", "Hindi"], "Haryana": ["Hindi", "Haryanvi"],
    "Delhi": ["Hindi", "Punjabi", "Urdu"], "Maharashtra": ["Marathi", "Hindi"],
    "Gujarat": ["Gujarati"], "Goa": ["Konkani", "Marathi", "English"],
    "West Bengal": ["Bengali"], "Odisha": ["Odia"],
    "Assam": ["Assamese", "Bengali", "Bodo"],
    "Madhya Pradesh": ["Hindi"], "Chhattisgarh": ["Chhattisgarhi", "Hindi"],
    "Jharkhand": ["Hindi", "Santali"], "Uttarakhand": ["Hindi", "Garhwali"],
    "Himachal Pradesh": ["Hindi", "Pahari"], "Tripura": ["Bengali", "Kokborok"],
    "Meghalaya": ["Khasi", "English"], "Manipur": ["Meitei", "English"],
    "Nagaland": ["English", "Nagamese"], "Arunachal Pradesh": ["English", "Nyishi"],
    "Sikkim": ["Nepali", "Sikkimese"],
}

# ── Age distribution ──────────────────────────────────────────
# Source: Census 2011 age pyramid
AGE_DISTRIBUTION = {
    (18, 25): 0.22,
    (26, 35): 0.25,
    (36, 45): 0.20,
    (46, 55): 0.16,
    (56, 65): 0.11,
    (66, 80): 0.06,
}

# ── Gender distribution ───────────────────────────────────────
GENDER_DISTRIBUTION = {"male": 0.52, "female": 0.47, "other": 0.01}

# ── Urban/Rural split by state ────────────────────────────────
# Source: Census 2011
STATE_URBAN_RATIO = {
    "Delhi": 0.978, "Goa": 0.623, "Maharashtra": 0.453,
    "Gujarat": 0.428, "Tamil Nadu": 0.484, "Karnataka": 0.387,
    "Punjab": 0.375, "Haryana": 0.348, "Kerala": 0.476,
    "West Bengal": 0.318, "Andhra Pradesh": 0.331, "Telangana": 0.389,
    "Rajasthan": 0.248, "Uttar Pradesh": 0.221, "Bihar": 0.114,
    "Madhya Pradesh": 0.277, "Odisha": 0.168, "Assam": 0.143,
    "Jharkhand": 0.241, "Chhattisgarh": 0.239, "Uttarakhand": 0.307,
    "Himachal Pradesh": 0.100, "Tripura": 0.264, "Meghalaya": 0.202,
    "Manipur": 0.302, "Nagaland": 0.289, "Arunachal Pradesh": 0.228,
    "Sikkim": 0.249,
}

# ── Occupation types ──────────────────────────────────────────
OCCUPATION_TYPES = {
    "software_engineer":    {"income_tier": "high",   "stress": "medium", "commute": (30, 90),  "wfh_prob": 0.6},
    "office_worker":        {"income_tier": "medium", "stress": "medium", "commute": (45, 120), "wfh_prob": 0.2},
    "student":              {"income_tier": "low",    "stress": "high",   "commute": (20, 60),  "wfh_prob": 0.3},
    "homemaker":            {"income_tier": "medium", "stress": "low",    "commute": (0, 10),   "wfh_prob": 0.95},
    "business_owner":       {"income_tier": "high",   "stress": "high",   "commute": (20, 60),  "wfh_prob": 0.4},
    "field_worker":         {"income_tier": "low",    "stress": "high",   "commute": (60, 180), "wfh_prob": 0.0},
    "healthcare_worker":    {"income_tier": "medium", "stress": "high",   "commute": (30, 60),  "wfh_prob": 0.0},
    "teacher":              {"income_tier": "medium", "stress": "medium", "commute": (20, 60),  "wfh_prob": 0.1},
    "driver":               {"income_tier": "low",    "stress": "high",   "commute": (0, 30),   "wfh_prob": 0.0},
    "daily_wage_worker":    {"income_tier": "low",    "stress": "high",   "commute": (30, 90),  "wfh_prob": 0.0},
    "retired":              {"income_tier": "medium", "stress": "low",    "commute": (0, 10),   "wfh_prob": 1.0},
    "freelancer":           {"income_tier": "medium", "stress": "medium", "commute": (0, 20),   "wfh_prob": 0.8},
}

# Occupation distribution by age group
OCCUPATION_BY_AGE = {
    (18, 25): {"student": 0.45, "software_engineer": 0.10, "office_worker": 0.15, "field_worker": 0.15, "daily_wage_worker": 0.10, "driver": 0.05},
    (26, 35): {"software_engineer": 0.18, "office_worker": 0.22, "homemaker": 0.15, "business_owner": 0.12, "field_worker": 0.12, "healthcare_worker": 0.08, "teacher": 0.08, "driver": 0.05},
    (36, 45): {"software_engineer": 0.15, "office_worker": 0.20, "homemaker": 0.18, "business_owner": 0.15, "field_worker": 0.12, "healthcare_worker": 0.08, "teacher": 0.08, "driver": 0.04},
    (46, 55): {"office_worker": 0.18, "homemaker": 0.22, "business_owner": 0.18, "field_worker": 0.15, "teacher": 0.10, "driver": 0.07, "daily_wage_worker": 0.10},
    (56, 65): {"retired": 0.30, "homemaker": 0.25, "business_owner": 0.15, "field_worker": 0.15, "daily_wage_worker": 0.15},
    (66, 80): {"retired": 0.65, "homemaker": 0.30, "daily_wage_worker": 0.05},
}

# ── Income tiers ──────────────────────────────────────────────
INCOME_TIERS = {
    "low":    {"monthly_food_budget": (1500, 4000),  "order_budget_per_meal": (80, 200)},
    "medium": {"monthly_food_budget": (4000, 12000), "order_budget_per_meal": (150, 400)},
    "high":   {"monthly_food_budget": (12000, 35000),"order_budget_per_meal": (300, 800)},
}

# ── Living situations ─────────────────────────────────────────
LIVING_SITUATIONS = {
    "alone":            {"cooking_prob": 0.35, "order_prob": 0.55, "street_food_prob": 0.10},
    "with_spouse":      {"cooking_prob": 0.65, "order_prob": 0.28, "street_food_prob": 0.07},
    "with_family":      {"cooking_prob": 0.75, "order_prob": 0.18, "street_food_prob": 0.07},
    "hostel_pg":        {"cooking_prob": 0.05, "order_prob": 0.50, "street_food_prob": 0.45},
    "with_roommates":   {"cooking_prob": 0.25, "order_prob": 0.55, "street_food_prob": 0.20},
}

# Living situation probabilities by age and occupation
LIVING_BY_AGE_OCCUPATION = {
    "student":          {"hostel_pg": 0.55, "with_family": 0.35, "with_roommates": 0.10},
    "software_engineer":{"alone": 0.25, "with_spouse": 0.30, "with_family": 0.20, "with_roommates": 0.25},
    "office_worker":    {"alone": 0.15, "with_spouse": 0.35, "with_family": 0.35, "with_roommates": 0.15},
    "homemaker":        {"with_spouse": 0.50, "with_family": 0.50},
    "business_owner":   {"with_spouse": 0.45, "with_family": 0.40, "alone": 0.15},
    "field_worker":     {"with_family": 0.60, "with_roommates": 0.25, "alone": 0.15},
    "healthcare_worker":{"alone": 0.20, "with_spouse": 0.35, "with_family": 0.30, "with_roommates": 0.15},
    "teacher":          {"with_family": 0.50, "with_spouse": 0.35, "alone": 0.15},
    "driver":           {"with_family": 0.70, "alone": 0.20, "with_roommates": 0.10},
    "daily_wage_worker":{"with_family": 0.75, "with_roommates": 0.20, "alone": 0.05},
    "retired":          {"with_family": 0.60, "with_spouse": 0.40},
    "freelancer":       {"alone": 0.30, "with_spouse": 0.30, "with_family": 0.25, "with_roommates": 0.15},
}

# ── Health conditions prevalence ──────────────────────────────
# Source: NFHS-5 2021, state-level adjusted
CONDITION_PREVALENCE_BY_AGE_GENDER = {
    "type2_diabetes": {
        (18, 25): {"male": 0.02, "female": 0.02},
        (26, 35): {"male": 0.06, "female": 0.05},
        (36, 45): {"male": 0.12, "female": 0.10},
        (46, 55): {"male": 0.20, "female": 0.18},
        (56, 65): {"male": 0.28, "female": 0.25},
        (66, 80): {"male": 0.32, "female": 0.30},
    },
    "prediabetes": {
        (18, 25): {"male": 0.05, "female": 0.04},
        (26, 35): {"male": 0.10, "female": 0.08},
        (36, 45): {"male": 0.18, "female": 0.15},
        (46, 55): {"male": 0.25, "female": 0.22},
        (56, 65): {"male": 0.28, "female": 0.25},
        (66, 80): {"male": 0.25, "female": 0.22},
    },
    "hypertension": {
        (18, 25): {"male": 0.04, "female": 0.02},
        (26, 35): {"male": 0.10, "female": 0.06},
        (36, 45): {"male": 0.22, "female": 0.16},
        (46, 55): {"male": 0.35, "female": 0.28},
        (56, 65): {"male": 0.50, "female": 0.45},
        (66, 80): {"male": 0.60, "female": 0.58},
    },
    "pcos": {
        (18, 25): {"male": 0.0, "female": 0.12},
        (26, 35): {"male": 0.0, "female": 0.14},
        (36, 45): {"male": 0.0, "female": 0.08},
        (46, 55): {"male": 0.0, "female": 0.02},
        (56, 65): {"male": 0.0, "female": 0.0},
        (66, 80): {"male": 0.0, "female": 0.0},
    },
    "thyroid": {
        (18, 25): {"male": 0.01, "female": 0.04},
        (26, 35): {"male": 0.02, "female": 0.06},
        (36, 45): {"male": 0.03, "female": 0.08},
        (46, 55): {"male": 0.04, "female": 0.10},
        (56, 65): {"male": 0.05, "female": 0.12},
        (66, 80): {"male": 0.06, "female": 0.14},
    },
    "high_cholesterol": {
        (18, 25): {"male": 0.05, "female": 0.04},
        (26, 35): {"male": 0.12, "female": 0.09},
        (36, 45): {"male": 0.22, "female": 0.18},
        (46, 55): {"male": 0.32, "female": 0.28},
        (56, 65): {"male": 0.40, "female": 0.38},
        (66, 80): {"male": 0.45, "female": 0.44},
    },
    "obesity": {
        (18, 25): {"male": 0.05, "female": 0.08},
        (26, 35): {"male": 0.12, "female": 0.16},
        (36, 45): {"male": 0.18, "female": 0.22},
        (46, 55): {"male": 0.22, "female": 0.26},
        (56, 65): {"male": 0.20, "female": 0.24},
        (66, 80): {"male": 0.16, "female": 0.20},
    },
    "ibs": {
        (18, 25): {"male": 0.06, "female": 0.10},
        (26, 35): {"male": 0.07, "female": 0.11},
        (36, 45): {"male": 0.06, "female": 0.09},
        (46, 55): {"male": 0.05, "female": 0.08},
        (56, 65): {"male": 0.05, "female": 0.07},
        (66, 80): {"male": 0.04, "female": 0.06},
    },
    "lactose_intolerance": {
        (18, 25): {"male": 0.12, "female": 0.12},
        (26, 35): {"male": 0.14, "female": 0.14},
        (36, 45): {"male": 0.16, "female": 0.16},
        (46, 55): {"male": 0.18, "female": 0.18},
        (56, 65): {"male": 0.20, "female": 0.20},
        (66, 80): {"male": 0.22, "female": 0.22},
    },
    "gluten_intolerance": {
        (18, 25): {"male": 0.02, "female": 0.03},
        (26, 35): {"male": 0.02, "female": 0.03},
        (36, 45): {"male": 0.02, "female": 0.03},
        (46, 55): {"male": 0.02, "female": 0.02},
        (56, 65): {"male": 0.02, "female": 0.02},
        (66, 80): {"male": 0.02, "female": 0.02},
    },
    "anemia": {
        (18, 25): {"male": 0.10, "female": 0.28},
        (26, 35): {"male": 0.08, "female": 0.30},
        (36, 45): {"male": 0.08, "female": 0.24},
        (46, 55): {"male": 0.10, "female": 0.20},
        (56, 65): {"male": 0.14, "female": 0.18},
        (66, 80): {"male": 0.18, "female": 0.20},
    },
}

# ── Dietary restrictions by religion ─────────────────────────
RELIGION_DIETARY_CONSTRAINTS = {
    "hindu": {
        "vegetarian_prob": 0.28,
        "no_beef_prob": 0.82,
        "no_pork_prob": 0.05,
        "no_onion_garlic_prob": 0.08,
        "fasting_frequency": "occasional",
    },
    "muslim": {
        "vegetarian_prob": 0.05,
        "halal_required": True,
        "no_pork_prob": 1.0,
        "no_alcohol_prob": 0.92,
        "fasting_frequency": "ramadan_plus",
    },
    "jain": {
        "vegetarian_prob": 1.0,
        "no_root_vegetables_prob": 0.75,
        "no_onion_garlic_prob": 0.85,
        "fasting_frequency": "frequent",
    },
    "sikh": {
        "vegetarian_prob": 0.30,
        "no_beef_prob": 0.65,
        "no_halal_prob": 0.60,
        "fasting_frequency": "rare",
    },
    "christian": {
        "vegetarian_prob": 0.10,
        "no_beef_prob": 0.10,
        "fasting_frequency": "lent",
    },
    "buddhist": {
        "vegetarian_prob": 0.45,
        "no_beef_prob": 0.70,
        "fasting_frequency": "occasional",
    },
    "other": {
        "vegetarian_prob": 0.20,
        "fasting_frequency": "rare",
    },
}

# ── Regional cuisine affinity distributions ───────────────────
# Source: ICMR What India Eats 2021
# Format: cuisine_type: (mean_frequency_per_week, std_dev)
REGIONAL_CUISINE_AFFINITY = {
    "south": {
        "south_indian": (6.5, 0.8),
        "biryani":      (1.2, 0.6),
        "north_indian": (0.8, 0.5),
        "street_food":  (1.5, 0.7),
        "chinese":      (0.5, 0.4),
        "dessert":      (0.8, 0.5),
    },
    "north": {
        "north_indian": (5.5, 0.9),
        "street_food":  (2.0, 0.8),
        "biryani":      (1.0, 0.6),
        "south_indian": (0.4, 0.3),
        "chinese":      (0.6, 0.4),
        "dessert":      (1.0, 0.5),
    },
    "west": {
        "gujarati":     (4.0, 0.9),
        "maharashtrian":(3.5, 0.9),
        "north_indian": (1.5, 0.6),
        "street_food":  (2.0, 0.7),
        "biryani":      (0.8, 0.5),
        "dessert":      (1.2, 0.5),
    },
    "east": {
        "bengali":      (5.0, 0.9),
        "north_indian": (1.2, 0.6),
        "street_food":  (1.5, 0.7),
        "biryani":      (0.8, 0.5),
        "chinese":      (0.8, 0.5),
        "dessert":      (1.5, 0.6),
    },
    "northeast": {
        "northeast":    (5.5, 0.8),
        "chinese":      (1.5, 0.6),
        "north_indian": (0.8, 0.5),
        "street_food":  (1.0, 0.5),
        "dessert":      (0.5, 0.4),
    },
}
# ADD these new keys — generators need to check state first, then fall back to region
REGIONAL_CUISINE_AFFINITY_BY_STATE = {
    "Assam": {
        "assamese":     (5.0, 0.8),   # rice, fish, mustard-based
        "northeast":    (3.0, 0.7),
        "north_indian": (0.5, 0.3),
        "bengali":      (0.3, 0.2),   # some overlap but not dominant
    },
    "Odisha": {
        "odia":         (5.5, 0.8),   # dal pakhala, dalma, chhena poda
        "east_indian":  (2.0, 0.6),
        "north_indian": (0.8, 0.4),
        "bengali":      (0.4, 0.2),   # some overlap, neighboring state
    },
    "Tripura": {
        "bengali":      (3.0, 0.7),   # genuine overlap, large Bengali population
        "northeast":    (2.5, 0.7),
        "north_indian": (0.5, 0.3),
    },
    "Meghalaya": {
        "northeast":    (5.0, 0.8),
        "north_indian": (0.5, 0.3),
        "bengali":      (0.2, 0.1),
    },
    "Manipur": {
        "northeast":    (5.5, 0.8),
        "north_indian": (0.4, 0.3),
        "bengali":      (0.2, 0.1),
    },
    "Nagaland": {
        "northeast":    (5.5, 0.8),
        "north_indian": (0.3, 0.2),
    },
    "Arunachal Pradesh": {
        "northeast":    (5.5, 0.8),
        "north_indian": (0.4, 0.3),
    },
    "Sikkim": {
        "northeast":    (4.0, 0.8),
        "north_indian": (1.0, 0.5),
        "bengali":      (0.5, 0.3),
    },
}
# ── Dish pools by cuisine ─────────────────────────────────────
# These are the dishes in our nutrition KB mapped by cuisine
CUISINE_DISH_POOLS = {
    "south_indian": [
        "idli", "dosa", "masala dosa", "rava dosa", "set dosa", "neer dosa",
        "uttapam", "medu vada", "masala vada", "upma", "vegetable upma",
        "pongal", "sweet pongal", "curd rice", "lemon rice", "tamarind rice",
        "coconut rice", "tomato rice", "bisibelebath", "vangi bath",
        "sambar", "rasam", "avial", "thoran", "appam", "puttu",
        "pesarattu", "adai", "rava idli", "parotta", "kottu roti",
        "kerala fish curry", "murukku", "coconut chutney", "tomato chutney",
    ],
    "north_indian": [
        "dal makhani", "dal tadka", "moong dal", "chana dal", "masoor dal",
        "butter chicken", "chicken curry", "chicken tikka", "tandoori chicken",
        "chicken korma", "chicken do pyaza", "mutton curry", "rogan josh", "keema",
        "palak paneer", "paneer tikka masala", "shahi paneer", "kadai paneer",
        "paneer bhurji", "matar paneer", "malai kofta", "kadhi",
        "aloo gobi", "chole", "rajma", "baingan bharta", "aloo matar",
        "bhindi masala", "aloo palak", "shahi korma",
        "roti", "naan", "paratha", "aloo paratha", "gobi paratha",
        "paneer paratha", "puri", "bhatura", "missi roti",
        "jeera rice", "pulao",
    ],
    "biryani": [
        "chicken biryani", "mutton biryani", "veg biryani",
        "egg biryani", "prawn biryani",
    ],
    "gujarati": [
        "dhokla", "thepla", "handvo", "khandvi", "undhiyu",
        "dal dhokli", "gujarati kadhi", "sev tameta", "rotlo", "sukhdi",
    ],
    "maharashtrian": [
        "pav bhaji", "misal pav", "vada pav", "puran poli",
        "bharli vangi", "ukdiche modak", "sabudana khichdi",
        "poha", "thalipeeth",
    ],
    "rajasthani": [
        "dal baati churma", "laal maas", "gatte ki sabzi",
        "ker sangri", "bajra khichdi", "rabdi",
    ],
    "bengali": [
        "machher jhol", "shorshe ilish", "aloo posto",
        "chingri malai curry", "luchi", "mishti doi",
        "rasgulla", "sandesh",
    ],
    "street_food": [
        "samosa", "pani puri", "bhel puri", "sev puri", "dahi puri",
        "aloo tikki", "dabeli", "chole bhature", "kathi roll", "chaat",
        "vada pav", "pav bhaji",
    ],
    "dessert": [
        "gulab jamun", "kheer", "jalebi", "halwa", "gajar halwa",
        "ladoo", "barfi", "kaju katli", "rasmalai", "kulfi",
        "shrikhand", "payasam", "rasgulla", "sandesh", "mishti doi",
        "rabdi",
    ],
    "beverage": [
        "masala chai", "filter coffee", "lassi", "buttermilk",
        "nimbu pani", "aam panna", "jaljeera", "thandai",
        "coconut water", "sugarcane juice", "rooh afza",
    ],
    "staple": [
        "steamed rice", "brown rice", "khichdi", "paneer", "egg",
        "chicken", "egg curry", "anda bhurji", "dahi", "raita",
        "mango pickle", "papadum",
    ],
    "goan": ["goan fish curry", "vindaloo", "bebinca"],
    "odia": [
    "dal pakhala", "dalma", "chhena poda", "santula",
    "mahura", "pakhala bhata", "saga bhaja",
    ],
    "assamese": [
        "masor tenga", "duck curry", "aloo pitika", "khar",
        "paro mangkho", "bamboo shoot curry",
    ],
}

# ── Meal timing distributions ─────────────────────────────────
# Format: (mean_hour, std_dev) for each region and occasion
MEAL_TIMING = {
    "south": {
        "breakfast": (7.5, 0.8),
        "lunch":     (13.0, 0.7),
        "snack":     (16.5, 0.8),
        "dinner":    (20.0, 0.8),
    },
    "north": {
        "breakfast": (8.5, 1.0),
        "lunch":     (13.5, 0.8),
        "snack":     (17.0, 0.8),
        "dinner":    (21.0, 1.0),
    },
    "west": {
        "breakfast": (8.0, 0.8),
        "lunch":     (13.0, 0.7),
        "snack":     (16.5, 0.8),
        "dinner":    (20.5, 0.8),
    },
    "east": {
        "breakfast": (8.0, 0.9),
        "lunch":     (13.0, 0.8),
        "snack":     (17.0, 0.8),
        "dinner":    (21.0, 0.9),
    },
    "northeast": {
        "breakfast": (7.5, 0.8),
        "lunch":     (12.5, 0.7),
        "snack":     (16.0, 0.8),
        "dinner":    (19.5, 0.8),
    },
}

# ── Seasons in India ──────────────────────────────────────────
MONTH_TO_SEASON = {
    1: "winter", 2: "winter", 3: "summer_onset",
    4: "summer", 5: "summer", 6: "monsoon_onset",
    7: "monsoon", 8: "monsoon", 9: "monsoon_end",
    10: "autumn", 11: "winter_onset", 12: "winter",
}

# ── Festival calendar ─────────────────────────────────────────
# Format: (month, day_range, religions_affected, food_impact)
FESTIVALS = [
    {"name": "Makar Sankranti", "month": 1, "days": [14, 15], "religions": ["hindu"], "region": ["north", "west", "south"], "food_impact": {"til_sweets": 3.0, "khichdi": 2.5}},
    {"name": "Pongal",          "month": 1, "days": [14, 15, 16, 17], "religions": ["hindu"], "region": ["south"], "food_impact": {"sweet_pongal": 4.0, "sugarcane": 2.0}},
    {"name": "Republic Day",    "month": 1, "days": [26], "religions": ["all"], "region": ["all"], "food_impact": {"sweets": 1.5}},
    {"name": "Holi",            "month": 3, "days": [25, 26], "religions": ["hindu"], "region": ["north", "west"], "food_impact": {"sweets": 2.5, "thandai": 4.0, "gujiya": 3.0}},
    {"name": "Gudi Padwa",      "month": 4, "days": [9], "religions": ["hindu"], "region": ["west"], "food_impact": {"sweets": 2.0, "shrikhand": 3.0}},
    {"name": "Eid ul Fitr",     "month": 4, "days": [21], "religions": ["muslim"], "region": ["all"], "food_impact": {"biryani": 3.0, "sweets": 3.0, "haleem": 2.5}},
    {"name": "Onam",            "month": 8, "days": [29, 30, 31], "religions": ["hindu"], "region": ["south"], "food_impact": {"sadya": 5.0, "payasam": 3.0}},
    {"name": "Ganesh Chaturthi","month": 8, "days": [19], "religions": ["hindu"], "region": ["west", "south"], "food_impact": {"modak": 4.0, "sweets": 2.5}},
    {"name": "Navratri",        "month": 10, "days": list(range(3, 13)), "religions": ["hindu"], "region": ["north", "west"], "food_impact": {"sabudana": 3.0, "fasting_foods": 4.0}},
    {"name": "Dussehra",        "month": 10, "days": [12], "religions": ["hindu"], "region": ["all"], "food_impact": {"sweets": 2.0}},
    {"name": "Diwali",          "month": 11, "days": [1, 2, 3, 4, 5], "religions": ["hindu", "jain", "sikh"], "region": ["all"], "food_impact": {"sweets": 4.0, "ladoo": 3.5, "barfi": 3.0, "kaju_katli": 3.5}},
    {"name": "Chhath Puja",     "month": 11, "days": [7, 8], "religions": ["hindu"], "region": ["east", "north"], "food_impact": {"thekua": 3.0, "fasting_foods": 2.5}},
    {"name": "Christmas",       "month": 12, "days": [25, 26], "religions": ["christian"], "region": ["all"], "food_impact": {"cake": 3.0, "sweets": 2.0}},
    {"name": "Eid ul Adha",     "month": 6, "days": [17], "religions": ["muslim"], "region": ["all"], "food_impact": {"mutton": 4.0, "biryani": 3.5}},
    {"name": "Durga Puja",      "month": 10, "days": [3, 4, 5, 6, 7], "religions": ["hindu"], "region": ["east"], "food_impact": {"sweets": 3.0, "biryani": 2.0, "fish": 2.5}},
    {"name": "Baisakhi",        "month": 4, "days": [13, 14], "religions": ["sikh", "hindu"], "region": ["north"], "food_impact": {"lassi": 3.0, "sweets": 2.0}},
    {"name": "Puri Rath Yatra", "month": 7, "days": [7], "religions": ["hindu"], "region": ["east"], "food_impact": {"khichdi": 2.5, "dal": 2.0}},
    {"name": "Raksha Bandhan",  "month": 8, "days": [19], "religions": ["hindu"], "region": ["north", "west"], "food_impact": {"sweets": 2.5}},
    {"name": "Janmashtami",     "month": 8, "days": [26], "religions": ["hindu"], "region": ["all"], "food_impact": {"fasting_foods": 3.0, "sweets": 2.0}},
    {"name": "Ramadan",         "month": 3, "days": list(range(12, 32)) + list(range(1, 12)), "religions": ["muslim"], "region": ["all"], "food_impact": {"sehri": 5.0, "iftar": 5.0, "biryani": 2.0}},
]

# ── Fasting schedules by religion ────────────────────────────
FASTING_SCHEDULES = {
    "hindu": {
        "ekadashi":         {"frequency": "twice_monthly", "allowed": ["fruits", "milk", "sabudana"], "skip_grains": True},
        "monday_fast":      {"frequency": "weekly",        "allowed": ["fruits", "milk"], "skip_grains": True, "probability": 0.18},
        "saturday_fast":    {"frequency": "weekly",        "allowed": ["limited"], "skip_grains": False, "probability": 0.12},
        "navratri":         {"frequency": "annual_9days",  "allowed": ["sabudana", "kuttu", "fruits", "milk"], "skip_grains": True},
        "shravan_no_nonveg":{"frequency": "monthly_shravan","allowed": ["veg_only"], "skip_grains": False},
    },
    "muslim": {
        "ramadan":          {"frequency": "annual_30days", "allowed": ["iftar_sehri"], "skip_grains": False, "full_day_fast": True},
    },
    "jain": {
        "paryushan":        {"frequency": "annual_8days",  "allowed": ["limited_jain"], "skip_grains": True},
        "no_after_sunset":  {"frequency": "daily",         "allowed": ["before_sunset_only"], "skip_grains": False},
        "monthly_fast":     {"frequency": "monthly",       "allowed": ["limited"], "skip_grains": True, "probability": 0.40},
    },
    "christian": {
        "good_friday":      {"frequency": "annual_1day",   "allowed": ["limited"], "skip_grains": False},
        "lent_friday":      {"frequency": "weekly_40days", "allowed": ["no_meat"], "skip_grains": False},
    },
}

# ── Weather by city and month ─────────────────────────────────
# Temperature ranges (°C) and monsoon flag
CITY_WEATHER = {
    "Chennai":      {1: (24, "dry"), 2: (26, "dry"), 3: (29, "dry"), 4: (32, "dry"), 5: (35, "dry"), 6: (34, "humid"), 7: (33, "monsoon"), 8: (33, "monsoon"), 9: (33, "monsoon"), 10: (30, "monsoon"), 11: (27, "dry"), 12: (25, "dry")},
    "Bangalore":    {1: (21, "dry"), 2: (24, "dry"), 3: (27, "dry"), 4: (29, "dry"), 5: (28, "dry"), 6: (25, "monsoon"), 7: (23, "monsoon"), 8: (24, "monsoon"), 9: (24, "monsoon"), 10: (23, "monsoon"), 11: (22, "dry"), 12: (21, "dry")},
    "Mumbai":       {1: (24, "dry"), 2: (26, "dry"), 3: (29, "dry"), 4: (31, "dry"), 5: (33, "humid"), 6: (30, "monsoon"), 7: (28, "monsoon"), 8: (28, "monsoon"), 9: (29, "monsoon"), 10: (30, "dry"), 11: (28, "dry"), 12: (25, "dry")},
    "Delhi":        {1: (14, "cold"), 2: (18, "cold"), 3: (24, "dry"), 4: (30, "dry"), 5: (36, "hot"), 6: (38, "hot"), 7: (32, "monsoon"), 8: (31, "monsoon"), 9: (30, "monsoon"), 10: (26, "dry"), 11: (20, "dry"), 12: (15, "cold")},
    "Kolkata":      {1: (20, "dry"), 2: (24, "dry"), 3: (29, "dry"), 4: (33, "dry"), 5: (34, "dry"), 6: (33, "monsoon"), 7: (30, "monsoon"), 8: (30, "monsoon"), 9: (30, "monsoon"), 10: (28, "dry"), 11: (24, "dry"), 12: (20, "dry")},
    "Hyderabad":    {1: (22, "dry"), 2: (25, "dry"), 3: (29, "dry"), 4: (33, "dry"), 5: (35, "dry"), 6: (31, "monsoon"), 7: (27, "monsoon"), 8: (27, "monsoon"), 9: (27, "monsoon"), 10: (26, "dry"), 11: (23, "dry"), 12: (21, "dry")},
    "default":      {1: (22, "dry"), 2: (25, "dry"), 3: (28, "dry"), 4: (31, "dry"), 5: (33, "dry"), 6: (30, "monsoon"), 7: (28, "monsoon"), 8: (28, "monsoon"), 9: (29, "monsoon"), 10: (27, "dry"), 11: (24, "dry"), 12: (22, "dry")},
}

# ── Persona definitions ───────────────────────────────────────
PERSONAS = {
    "south_indian_office_worker": {
        "region": "south", "age_range": (24, 45), "occupation": "office_worker",
        "income_tier": "medium", "health_literacy": 0.6, "habit_strength": 0.75,
        "stress_profile": "medium", "trend_susceptibility": 0.3,
        "cooking_skill": 0.6, "order_frequency_weekly": 2.5,
    },
    "north_indian_student": {
        "region": "north", "age_range": (18, 24), "occupation": "student",
        "income_tier": "low", "health_literacy": 0.4, "habit_strength": 0.45,
        "stress_profile": "high", "trend_susceptibility": 0.7,
        "cooking_skill": 0.2, "order_frequency_weekly": 4.0,
    },
    "gujarati_homemaker": {
        "region": "west", "age_range": (26, 55), "occupation": "homemaker",
        "income_tier": "medium", "health_literacy": 0.55, "habit_strength": 0.85,
        "stress_profile": "low", "trend_susceptibility": 0.2,
        "cooking_skill": 0.95, "order_frequency_weekly": 0.8,
    },
    "bengali_professional": {
        "region": "east", "age_range": (26, 50), "occupation": "office_worker",
        "income_tier": "medium", "health_literacy": 0.65, "habit_strength": 0.70,
        "stress_profile": "medium", "trend_susceptibility": 0.35,
        "cooking_skill": 0.70, "order_frequency_weekly": 2.0,
    },
    "diabetic_senior_south": {
        "region": "south", "age_range": (50, 75), "occupation": "retired",
        "income_tier": "medium", "health_literacy": 0.75, "habit_strength": 0.88,
        "stress_profile": "low", "trend_susceptibility": 0.1,
        "cooking_skill": 0.80, "order_frequency_weekly": 0.5,
        "forced_conditions": ["type2_diabetes"],
    },
    "punjabi_fitness": {
        "region": "north", "age_range": (20, 40), "occupation": "software_engineer",
        "income_tier": "high", "health_literacy": 0.80, "habit_strength": 0.65,
        "stress_profile": "medium", "trend_susceptibility": 0.6,
        "cooking_skill": 0.55, "order_frequency_weekly": 3.5,
    },
    "mumbai_young_professional": {
        "region": "west", "age_range": (22, 38), "occupation": "software_engineer",
        "income_tier": "high", "health_literacy": 0.65, "habit_strength": 0.45,
        "stress_profile": "high", "trend_susceptibility": 0.75,
        "cooking_skill": 0.35, "order_frequency_weekly": 5.0,
    },
    "rajasthani_vegetarian": {
        "region": "west", "age_range": (25, 65), "occupation": "business_owner",
        "income_tier": "medium", "health_literacy": 0.45, "habit_strength": 0.82,
        "stress_profile": "medium", "trend_susceptibility": 0.15,
        "cooking_skill": 0.75, "order_frequency_weekly": 1.0,
    },
    "kerala_health_conscious": {
        "region": "south", "age_range": (28, 55), "occupation": "healthcare_worker",
        "income_tier": "medium", "health_literacy": 0.88, "habit_strength": 0.70,
        "stress_profile": "high", "trend_susceptibility": 0.40,
        "cooking_skill": 0.80, "order_frequency_weekly": 1.5,
    },
    "hypertension_north_indian": {
        "region": "north", "age_range": (45, 70), "occupation": "retired",
        "income_tier": "medium", "health_literacy": 0.60, "habit_strength": 0.80,
        "stress_profile": "low", "trend_susceptibility": 0.1,
        "cooking_skill": 0.65, "order_frequency_weekly": 0.8,
        "forced_conditions": ["hypertension"],
    },
    "pcos_young_woman": {
        "region": "west", "age_range": (18, 38), "occupation": "office_worker",
        "income_tier": "medium", "health_literacy": 0.72, "habit_strength": 0.55,
        "stress_profile": "high", "trend_susceptibility": 0.65,
        "cooking_skill": 0.50, "order_frequency_weekly": 2.5,
        "forced_conditions": ["pcos"],
        "forced_gender": "female",
    },
    "jain_strict_vegetarian": {
        "region": "west", "age_range": (25, 65), "occupation": "business_owner",
        "income_tier": "high", "health_literacy": 0.60, "habit_strength": 0.90,
        "stress_profile": "low", "trend_susceptibility": 0.10,
        "cooking_skill": 0.85, "order_frequency_weekly": 1.2,
        "forced_religion": "jain",
    },
}

# ── Cooking skill distribution ────────────────────────────────
COOKING_SKILL_LEVELS = {
    0.1: "cannot_cook",     # orders or canteen only
    0.3: "basic",           # dal rice eggs only
    0.55: "moderate",       # most home dishes
    0.75: "good",           # regional specialties
    0.90: "expert",         # rarely orders out
}

# ── Health literacy impact on food choices ────────────────────
# How much health literacy changes compliance with health conditions
HEALTH_LITERACY_COMPLIANCE = {
    0.0: 0.05,   # no awareness, 5% compliance
    0.2: 0.15,
    0.4: 0.35,
    0.6: 0.60,
    0.8: 0.80,
    1.0: 0.95,   # full awareness, 95% compliance
}

# ── Stress impact on food choices ────────────────────────────
# Multiplier on comfort food probability
STRESS_COMFORT_FOOD_MULTIPLIER = {
    "none":   1.0,
    "low":    1.1,
    "medium": 1.35,
    "high":   1.80,
    "extreme":2.50,
}

# Comfort foods by region
COMFORT_FOODS = {
    "south": ["curd rice", "khichdi", "pongal", "idli", "rasam"],
    "north": ["dal tadka", "khichdi", "aloo paratha", "rajma", "chole"],
    "west":  ["khichdi", "dal dhokli", "sabudana khichdi", "poha"],
    "east":  ["khichdi", "dal pakhala", "machher jhol", "aloo posto"],
}

# ── Social context distribution ───────────────────────────────
SOCIAL_CONTEXT_BY_DAY = {
    "weekday": {
        "breakfast": {"alone": 0.70, "with_family": 0.28, "with_colleagues": 0.02},
        "lunch":     {"alone": 0.45, "with_colleagues": 0.38, "with_friends": 0.10, "with_family": 0.07},
        "snack":     {"alone": 0.60, "with_colleagues": 0.30, "with_friends": 0.10},
        "dinner":    {"with_family": 0.52, "alone": 0.30, "with_friends": 0.10, "with_spouse": 0.08},
    },
    "weekend": {
        "breakfast": {"with_family": 0.55, "alone": 0.30, "with_spouse": 0.15},
        "lunch":     {"with_family": 0.48, "with_friends": 0.25, "alone": 0.15, "at_restaurant": 0.12},
        "snack":     {"with_friends": 0.40, "alone": 0.35, "with_family": 0.25},
        "dinner":    {"with_family": 0.40, "with_friends": 0.30, "at_restaurant": 0.18, "alone": 0.12},
    },
}

# ── Month position budget multiplier ─────────────────────────
# Day of month → budget multiplier
def get_month_position_multiplier(day_of_month: int) -> float:
    if day_of_month <= 3:    return 1.40   # just got paid
    elif day_of_month <= 10: return 1.20   # early month
    elif day_of_month <= 20: return 1.00   # mid month normal
    elif day_of_month <= 25: return 0.85   # getting tight
    else:                    return 0.70   # month end struggle

# ── Meal skip probabilities ───────────────────────────────────
SKIP_PROBABILITY = {
    "breakfast": {
        "student":           0.35,
        "software_engineer": 0.25,
        "office_worker":     0.20,
        "homemaker":         0.05,
        "field_worker":      0.15,
        "retired":           0.05,
        "default":           0.18,
    },
    "lunch": {
        "student":           0.12,
        "software_engineer": 0.15,
        "office_worker":     0.08,
        "homemaker":         0.03,
        "field_worker":      0.05,
        "retired":           0.04,
        "default":           0.08,
    },
    "dinner": {
        "default":           0.03,
    },
}

# ── Life event types ──────────────────────────────────────────
LIFE_EVENT_TYPES = {
    "health_diagnosis": {
        "probability_per_year": 0.08,
        "transition_weeks": (2, 8),
        "diet_impact": "moderate_to_high",
    },
    "city_relocation": {
        "probability_per_year": 0.06,
        "transition_weeks": (4, 12),
        "diet_impact": "moderate",
    },
    "started_gym": {
        "probability_per_year": 0.12,
        "transition_weeks": (2, 6),
        "diet_impact": "protein_increase",
    },
    "marriage": {
        "probability_per_year": 0.04,
        "transition_weeks": (4, 12),
        "diet_impact": "dietary_merge",
    },
    "job_change": {
        "probability_per_year": 0.15,
        "transition_weeks": (2, 4),
        "diet_impact": "timing_change",
    },
    "pregnancy": {
        "probability_per_year": 0.03,
        "transition_weeks": (4, 36),
        "diet_impact": "calorie_increase",
        "gender_restricted": "female",
    },
    "financial_stress": {
        "probability_per_year": 0.10,
        "transition_weeks": (4, 16),
        "diet_impact": "budget_reduction",
    },
}

# ── GI scores for health compliance tracking ──────────────────
DISH_GI_SCORES = {
    "idli": 70, "dosa": 69, "masala dosa": 68, "steamed rice": 73,
    "brown rice": 55, "roti": 62, "naan": 71, "paratha": 62,
    "puri": 68, "bhatura": 72, "chicken biryani": 58,
    "dal makhani": 38, "dal tadka": 32, "moong dal": 30,
    "chole": 28, "rajma": 29, "palak paneer": 30,
    "butter chicken": 35, "chicken curry": 28,
    "samosa": 60, "vada pav": 65, "pani puri": 62,
    "gulab jamun": 85, "jalebi": 88, "kheer": 75,
    "pongal": 58, "khichdi": 50, "upma": 66,
    "sabudana khichdi": 72, "poha": 68,
    "masala chai": 45, "lassi": 48, "buttermilk": 30,
}

# Default GI for dishes not in above dict
DEFAULT_GI = 55

# ── Portion size multipliers ──────────────────────────────────
PORTION_MULTIPLIERS = {
    "alone_weekday":     0.90,
    "alone_stressed":    1.20,
    "with_family":       1.00,
    "with_colleagues":   0.95,
    "with_friends":      1.10,
    "post_skip":         1.25,
    "post_workout":      1.30,
    "festival":          1.40,
    "late_night":        0.80,
}
"""
constraints.py — additions to your existing constants.py
Add these blocks to constants.py (or import from here).

Every rule that can be violated lives here as data.
Generators import and use these — they never hardcode religion/condition/event logic inline.
"""

# ─────────────────────────────────────────────────────────────
# 1. FASTING FOODS — keyed by religion
#    Generators call: FASTING_FOODS[religion]["during"]
#    or              FASTING_FOODS[religion]["post_fast"]
# ─────────────────────────────────────────────────────────────

FASTING_FOODS = {
    "hindu": {
        "during": {
            "sabudana khichdi": 0.25, "dahi":           0.20,
            "kuttu roti":       0.15, "singhare ki puri":0.10,
            "fruits":           0.15, "milk":            0.10,
            "coconut water":    0.05,
        },
        "post_fast": ["sabudana khichdi", "kheer", "halwa", "dahi",
                      "fruits", "khichdi", "puri"],
        "forbidden": [],
    },
    "muslim": {
        "during": {
            # Ramadan: no food during daylight. 
            # "during" here means sehri (pre-dawn) foods.
            "roti":        0.20, "eggs":        0.15,
            "dal tadka":   0.15, "steamed rice":0.15,
            "paratha":     0.20, "dahi":        0.15,
        },
        "post_fast": [
            # Iftar foods — must NOT include Hindu vrat foods
            "dates", "sheer khurma", "kheer", "haleem",
            "samosa", "fruit chaat", "biryani", "chicken curry",
            "anda bhurji", "sewaiyan", "dahi",
        ],
        "forbidden": [
            # Hindu vrat foods — never appear in Muslim fasting context
            "sabudana khichdi", "kuttu roti", "singhare ki puri",
            "sendha namak dishes",
        ],
    },
    "jain": {
        "during": {
            "dahi":   0.30, "fruits":  0.25,
            "milk":   0.20, "dry_fruits": 0.15,
            "coconut water": 0.10,
        },
        "post_fast": ["kheer", "dahi", "khichdi", "fruits",
                      "sabudana khichdi", "milk"],
        "forbidden": ["non_veg", "root_vegetables", "onion", "garlic"],
    },
    "christian": {
        "during": {
            "fish curry":  0.30, "steamed rice": 0.25,
            "vegetables":  0.25, "fruits":       0.20,
        },
        "post_fast": ["fish curry", "steamed rice", "vegetables"],
        "forbidden": ["meat"],  # on fast days only
    },
    "default": {
        "during": {
            "dahi": 0.30, "khichdi": 0.30,
            "steamed rice": 0.20, "fruits": 0.20,
        },
        "post_fast": ["dahi", "khichdi", "steamed rice", "fruits"],
        "forbidden": [],
    },
}


def get_fasting_foods(religion: str, phase: str = "during") -> dict:
    """
    phase = "during" → weighted dict for food selection
    phase = "post_fast" → list of allowed break-fast foods
    phase = "forbidden" → list that must be excluded
    """
    pool = FASTING_FOODS.get(religion, FASTING_FOODS["default"])
    return pool.get(phase, pool.get("during", {}))


# ─────────────────────────────────────────────────────────────
# 2. BMI RISK WEIGHTS — condition probability multipliers
#    generate_users.py calls: BMI_RISK_WEIGHTS[condition](bmi)
# ─────────────────────────────────────────────────────────────

def bmi_diabetes_multiplier(bmi: float) -> float:
    """Returns probability multiplier for type2_diabetes given BMI."""
    if bmi >= 35:   return 5.0
    if bmi >= 30:   return 3.5
    if bmi >= 27.5: return 2.0
    if bmi >= 25:   return 1.4
    if bmi < 18.5:  return 0.5   # underweight has lower T2D risk
    return 1.0


def bmi_hypertension_multiplier(bmi: float) -> float:
    if bmi >= 35:   return 4.0
    if bmi >= 30:   return 2.5
    if bmi >= 27.5: return 1.6
    if bmi >= 25:   return 1.2
    return 1.0


def bmi_obesity_multiplier(bmi: float) -> float:
    """Only used if obesity is being sampled as a condition independently."""
    return 1.0 if bmi >= 30 else 0.0  # hard gate: obesity ↔ BMI≥30


BMI_RISK_WEIGHTS = {
    "type2_diabetes":  bmi_diabetes_multiplier,
    "prediabetes":     lambda bmi: bmi_diabetes_multiplier(bmi) * 0.7,
    "hypertension":    bmi_hypertension_multiplier,
    "high_cholesterol":lambda bmi: 1.8 if bmi >= 30 else 1.2 if bmi >= 25 else 1.0,
    "obesity":         bmi_obesity_multiplier,
    "sleep_apnea":     lambda bmi: 3.0 if bmi >= 30 else 1.0,
}

# Usage in generate_users.py sample_health_conditions():
#
#   for condition, age_gender_dist in CONDITION_PREVALENCE_BY_AGE_GENDER.items():
#       base_prob = age_gender_dist[bucket].get(g, 0.0)
#       if condition in BMI_RISK_WEIGHTS:
#           base_prob *= BMI_RISK_WEIGHTS[condition](bmi)
#       if random.random() < min(base_prob, 0.95):
#           conditions.append(condition)


# ─────────────────────────────────────────────────────────────
# 3. LIFE EVENT BEHAVIOR DELTAS
#    generate_meal_logs.py calls get_event_modifier(event_type, ...)
#    to shift portion, calorie target, protein target, budget, timing
# ─────────────────────────────────────────────────────────────

# Each event type defines how it changes meal generation parameters
# during the transition window.
# Values are MULTIPLIERS (1.0 = no change) or ABSOLUTE DELTAS.

LIFE_EVENT_DELTAS = {
    "started_gym": {
        "protein_multiplier":   1.35,   # +35% protein in dish selection
        "calorie_multiplier":   1.10,   # slight calorie increase
        "health_literacy_boost":0.08,   # more health-aware choices
        "preferred_occasions":  None,   # no timing change
        "budget_multiplier":    1.0,
        "description": "Increases protein affinity and health-aware dish selection",
    },
    "pregnancy": {
        "calorie_multiplier":   1.20,
        "protein_multiplier":   1.15,
        "portion_multiplier":   1.15,
        "skip_probability_mult":0.5,    # less likely to skip meals
        "budget_multiplier":    1.0,
        "description": "Higher calories, more regular eating pattern",
    },
    "financial_stress": {
        "budget_multiplier":    0.65,   # tighter budget
        "order_probability_mult":0.40,  # orders delivery less
        "comfort_food_boost":   0.20,   # more comfort food seeking
        "calorie_multiplier":   0.95,
        "description": "Lower budget, less delivery, more comfort food",
    },
    "health_diagnosis": {
        "health_literacy_boost":0.15,   # sudden health awareness
        "compliance_boost":     0.20,   # more health-compliant choices
        "gi_sensitivity":       True,   # for diabetes: avoid high-GI
        "calorie_multiplier":   0.92,
        "description": "Triggers health-aware dish selection and compliance",
    },
    "city_relocation": {
        "cuisine_shift": True,          # cuisine affinity changes toward new city
        "comfort_food_boost": 0.15,     # more comfort food while settling
        "social_context_shift": "alone",# more alone eating initially
        "budget_multiplier":   0.85,    # relocation costs
        "description": "Shifts cuisine preferences toward new city's cuisine",
    },
    "marriage": {
        "social_context_shift": "with_spouse",
        "portion_multiplier":   1.05,
        "cuisine_diversity_boost": 0.15,  # exposed to partner's preferences
        "budget_multiplier":    1.10,
        "description": "More meals with spouse, slightly higher budget",
    },
    "job_change": {
        "meal_timing_shift":    True,   # different office hours → different meal times
        "skip_probability_mult":1.20,   # adjustment period → more skips
        "budget_multiplier":    1.0,
        "description": "Meal timing shifts, slightly more skips during transition",
    },
}


def get_event_modifier(event_type: str, weeks_since_event: int,
                        transition_weeks: int, observance: float = 1.0) -> dict:
    """
    Returns a dict of active modifiers for the current meal.
    Modifiers fade linearly toward 1.0 (no effect) as weeks_since_event → transition_weeks.

    Usage in generate_meal_logs_for_user():
        phase, diet_change = get_event_phase(current_date)
        if phase != "normal":
            mod = get_event_modifier(phase, weeks_since_event, transition_weeks)
            # apply mod["calorie_multiplier"], mod["protein_multiplier"], etc.
    """
    if event_type not in LIFE_EVENT_DELTAS:
        return {}

    deltas = LIFE_EVENT_DELTAS[event_type]

    # Fade factor: 1.0 at event start, 0.0 at transition end
    # So modifier = 1.0 + (delta - 1.0) * fade
    if transition_weeks <= 0:
        fade = 0.0
    else:
        fade = max(0.0, 1.0 - (weeks_since_event / transition_weeks))

    active = {}
    for key, value in deltas.items():
        if key == "description":
            continue
        if isinstance(value, float) and value != 1.0:
            # Interpolate toward 1.0 (neutral)
            active[key] = 1.0 + (value - 1.0) * fade
        elif isinstance(value, bool) and value:
            active[key] = fade > 0.1  # boolean: active if fade > 10%
        elif isinstance(value, str):
            active[key] = value if fade > 0.1 else None
        else:
            active[key] = value

    return active


# ─────────────────────────────────────────────────────────────
# 4. FAMILY HISTORY CORRELATIONS
#    generate_users.py calls sample_family_history(conditions)
#    instead of random.sample()
# ─────────────────────────────────────────────────────────────

FAMILY_HISTORY_GIVEN_CONDITIONS = {
    # condition → {family_history_item: probability}
    "type2_diabetes":  {"diabetes": 0.55, "heart_disease": 0.20},
    "prediabetes":     {"diabetes": 0.40},
    "hypertension":    {"hypertension": 0.45, "heart_disease": 0.25},
    "high_cholesterol":{"heart_disease": 0.40},
    "obesity":         {"diabetes": 0.30, "heart_disease": 0.20},
    "pcos":            {"diabetes": 0.20},
    "heart_disease":   {"heart_disease": 0.50},
}

FAMILY_HISTORY_BASE_RATES = {
    # background rates for users without the condition
    "cancer":       0.12,
    "heart_disease":0.08,
    "diabetes":     0.10,
    "hypertension": 0.08,
    "none":         0.0,   # added at the end if list is empty
}


def sample_family_history(conditions: list) -> list:
    """
    Generates correlated family history from user's conditions.
    Replaces: random.sample(["diabetes","hypertension",...], k=random.randint(0,2))
    """
    import random
    history = set()

    # Condition-correlated history
    for condition in conditions:
        if condition in FAMILY_HISTORY_GIVEN_CONDITIONS:
            for fh_item, prob in FAMILY_HISTORY_GIVEN_CONDITIONS[condition].items():
                if random.random() < prob:
                    history.add(fh_item)

    # Background base rates
    for fh_item, rate in FAMILY_HISTORY_BASE_RATES.items():
        if fh_item == "none":
            continue
        if fh_item not in history and random.random() < rate:
            history.add(fh_item)

    if not history:
        history.add("none")

    return list(history)


# ─────────────────────────────────────────────────────────────
# 5. BMI OUTCOME MODEL
#    generate_remaining.py replaces the hardcoded -2.0 formula
# ─────────────────────────────────────────────────────────────

def compute_bmi_change(avg_calories_per_meal: float,
                        meals_per_day: float,
                        height_cm: float,
                        fitness_goal: str,
                        activity_level: str,
                        quarter_days: int = 90) -> float:
    """
    Realistic BMI change over a quarter based on caloric balance.
    Returns a BMI delta (positive = gain, negative = loss).
    Typical range: -1.5 to +1.5 per quarter.
    """
    import numpy as np

    # Estimate TDEE from activity level
    tdee_map = {
        "sedentary":        1600,
        "lightly_active":   1900,
        "moderately_active":2100,
        "very_active":      2400,
    }
    tdee = tdee_map.get(activity_level, 2000)

    # Intentional deficit/surplus based on fitness goal
    goal_adjustment = {
        "lose_weight":   -250,
        "gain_muscle":   +200,
        "maintain":       0,
        "general_health": -50,
        "manage_condition":-100,
    }
    tdee += goal_adjustment.get(fitness_goal, 0)

    daily_calories = avg_calories_per_meal * meals_per_day
    daily_surplus = daily_calories - tdee
    total_surplus_kcal = daily_surplus * quarter_days

    # 7700 kcal ≈ 1 kg body weight change
    weight_change_kg = total_surplus_kcal / 7700
    height_m = height_cm / 100
    bmi_change = weight_change_kg / (height_m ** 2)

    # Add realistic noise and clamp
    noise = np.random.normal(0, 0.6)
    return round(max(-3.0, min(3.0, bmi_change + noise)), 2)


# ─────────────────────────────────────────────────────────────
# 6. COMPLIANCE DELTA MODEL
#    Replaces: compliance_improvement = compliance_rate - 0.5
# ─────────────────────────────────────────────────────────────

def compute_compliance_improvement(current_compliance: float,
                                    prev_compliance: float) -> float:
    """
    Returns actual quarter-over-quarter compliance change.
    prev_compliance should be stored per user across quarters.
    Falls back to a plausible estimate if no prior data.
    """
    import numpy as np
    if prev_compliance is None:
        # First quarter: assume user started at 0.5 baseline
        baseline = 0.5
    else:
        baseline = prev_compliance
    return round(current_compliance - baseline + np.random.normal(0, 0.02), 3)