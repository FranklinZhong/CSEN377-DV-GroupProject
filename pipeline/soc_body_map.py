# MedDRA System Organ Class → SVG body-part identifier
# None = SOC doesn't map to a specific visible body region (general/admin, investigations, etc.)
SOC_TO_BODY_PART: dict[str, str | None] = {
    "Blood and lymphatic system disorders":                          "blood",
    "Cardiac disorders":                                             "heart",
    "Congenital, familial and genetic disorders":                    None,
    "Ear and labyrinth disorders":                                   "ear",
    "Endocrine disorders":                                           "endocrine",
    "Eye disorders":                                                 "eye",
    "Gastrointestinal disorders":                                    "stomach",
    "General disorders and administration site conditions":          None,
    "Hepatobiliary disorders":                                       "liver",
    "Immune system disorders":                                       "immune",
    "Infections and infestations":                                   None,
    "Injury, poisoning and procedural complications":                None,
    "Investigations":                                                None,
    "Metabolism and nutrition disorders":                            "endocrine",
    "Musculoskeletal and connective tissue disorders":               "muscle",
    "Neoplasms benign, malignant and unspecified (incl cysts and polyps)": None,
    "Nervous system disorders":                                      "brain",
    "Pregnancy, puerperium and perinatal conditions":                "reproductive",
    "Psychiatric disorders":                                         "brain",
    "Renal and urinary disorders":                                   "kidney",
    "Reproductive system and breast disorders":                      "reproductive",
    "Respiratory, thoracic and mediastinal disorders":               "lung",
    "Skin and subcutaneous tissue disorders":                        "skin",
    "Social circumstances":                                          None,
    "Surgical and medical procedures":                               None,
    "Vascular disorders":                                            "vascular",
    "Product issues":                                                None,
}

# Body-part keyword vocabulary for NLP extraction from both WebMD review text
# and FAERS MedDRA Preferred Terms (PT_NORM).
# Includes US English, British English (MedDRA uses British), and Latin MedDRA terms.
# Keys must match the values in SOC_TO_BODY_PART.
BODY_PART_KEYWORDS: dict[str, list[str]] = {
    "brain": [
        # Natural language
        "brain", "head", "headache", "migraine", "dizziness", "dizzy",
        "memory", "cognitive", "confusion", "seizure", "tremor", "nervous",
        "neurological", "concentration", "focus", "mood", "anxiety", "depression",
        "insomnia", "sleep", "hallucination", "psychosis", "paranoia",
        # MedDRA PT terms
        "syncope", "somnolence", "paraesthesia", "paresthesia", "neuropathy",
        "encephalopathy", "meningitis", "cerebral", "intracranial",
        "peripheral neuropathy", "altered mental", "lethargy", "amnesia",
        "dysarthria", "ataxia", "dystonia", "dyskinesia",
    ],
    "eye": [
        "eye", "eyes", "vision", "sight", "blurry", "blurred", "pupil",
        "retina", "optic", "dry eye", "tearing",
        # MedDRA PT terms
        "ocular", "conjunctivitis", "keratitis", "uveitis", "cataract",
        "glaucoma", "photophobia", "diplopia", "lacrimation", "blepharitis",
        "visual acuity", "visual field",
    ],
    "ear": [
        "ear", "ears", "hearing", "tinnitus", "ringing", "vertigo",
        # MedDRA PT terms
        "otalgia", "otitis", "hypoacusis", "deafness", "vestibular",
        "labyrinthitis", "ear pain",
    ],
    "heart": [
        "heart", "cardiac", "chest pain", "palpitation", "palpitations",
        "heartbeat", "pulse", "arrhythmia", "chest",
        # MedDRA PT terms (British spellings + Latin)
        "tachycardia", "bradycardia", "fibrillation", "myocardial",
        "coronary", "angina", "cardiomyopathy", "cardiotoxicity",
        "heart failure", "atrial", "ventricular", "endocarditis",
    ],
    "lung": [
        "lung", "lungs", "breathing", "breath", "shortness of breath",
        "cough", "coughing", "respiratory", "bronchial", "asthma", "wheezing",
        # MedDRA PT terms (British spellings critical here)
        "dyspnoea", "dyspnea",          # British + US
        "pneumonia", "pneumonitis",
        "pulmonary", "bronchitis", "bronchospasm",
        "pleural", "emphysema", "fibrosis", "haemoptysis", "hemoptysis",
        "tachypnoea", "tachypnea",
        "respiratory failure", "hypoxia",
    ],
    "stomach": [
        "stomach", "nausea", "vomit", "vomiting", "constipation",
        "bowel", "intestine", "gut", "gastric", "abdominal", "abdomen",
        "bloating", "cramp", "cramping", "indigestion", "heartburn", "acid",
        "reflux",
        # MedDRA PT terms (British spellings critical here)
        "diarrhoea", "diarrhea",        # British + US
        "dyspepsia", "flatulence",
        "gastrointestinal", "enteritis", "colitis", "gastritis",
        "abdominal pain", "rectal", "intestinal obstruction",
        "nausea and vomiting", "haematemesis", "hematemesis",
        "melaena", "melena",
    ],
    "liver": [
        "liver", "hepatic", "jaundice", "bile", "gallbladder",
        # MedDRA PT terms
        "hepatitis", "hepatotoxicity", "hepatomegaly", "cholestasis",
        "liver failure", "cirrhosis", "transaminase", "bilirubin",
        "alanine aminotransferase", "aspartate aminotransferase", "alt", "ast",
    ],
    "kidney": [
        "kidney", "kidneys", "renal", "urinary", "bladder", "urine",
        "urination", "frequent urination",
        # MedDRA PT terms
        "nephropathy", "nephritis", "proteinuria", "haematuria", "hematuria",
        "oliguria", "dysuria", "urolithiasis", "acute kidney",
        "chronic kidney", "glomerulonephritis",
    ],
    "skin": [
        "skin", "rash", "itching", "itch", "hives", "acne", "dermatitis",
        "sweating", "sweat", "swelling", "bruising", "hair loss", "dry skin",
        # MedDRA PT terms (Latin/British spellings critical)
        "pruritus",                     # Latin: itching
        "alopecia",                     # Latin: hair loss
        "urticaria",                    # Latin: hives
        "erythema", "psoriasis", "eczema",
        "hyperhidrosis",                # excessive sweating
        "photosensitivity", "angioedema",
        "pemphigus", "bullous", "vesicular", "pustular",
        "skin disorder", "dermatological",
    ],
    "muscle": [
        "muscle", "muscles", "joint", "joints", "arthritis", "back pain",
        "back", "spine", "spinal", "bone", "bones", "weakness", "fatigue",
        "tired", "tiredness",
        # MedDRA PT terms (Latin/British spellings critical)
        "arthralgia",                   # Latin: joint pain
        "myalgia",                      # Latin: muscle pain
        "asthenia",                     # Latin: weakness/fatigue
        "myopathy", "myositis", "tendinitis", "bursitis",
        "musculoskeletal", "fibromyalgia", "osteoporosis",
        "muscle spasm", "muscle weakness", "rhabdomyolysis",
        "limb pain", "extremity pain",
    ],
    "blood": [
        "blood", "bleeding", "bruising", "clot", "anemia", "platelet",
        "blood sugar", "glucose",
        # MedDRA PT terms
        "thrombosis", "thrombocytopenia", "neutropenia", "leukopenia",
        "lymphopenia", "pancytopenia", "haemorrhage", "hemorrhage",
        "epistaxis",                    # nosebleed
        "anaemia", "anemia",            # British + US
        "coagulation", "haematological", "hematological",
        "deep vein", "pulmonary embolism",
    ],
    "vascular": [
        "blood pressure", "hypertension", "hypotension", "vein", "artery",
        "circulation", "swelling", "edema",
        # MedDRA PT terms
        "oedema",                       # British: edema
        "peripheral oedema", "peripheral edema",
        "vasculitis", "ischaemia", "ischemia",
        "embolism", "atherosclerosis", "phlebitis",
    ],
    "endocrine": [
        "thyroid", "hormone", "hormonal", "insulin", "adrenal",
        "weight gain", "weight loss",
        # MedDRA PT terms
        "hypothyroidism", "hyperthyroidism", "diabetes", "hyperglycaemia",
        "hyperglycemia", "hypoglycaemia", "hypoglycemia",
        "cushings", "addisons", "pituitary", "parathyroid",
        "weight decreased", "weight increased",
    ],
    "immune": [
        "immune", "allergy", "allergic", "inflammation", "autoimmune",
        "fever",
        # MedDRA PT terms
        "pyrexia",                      # Latin: fever
        "anaphylaxis", "anaphylactic",
        "cytokine", "immunosuppression", "immunodeficiency",
        "hypersensitivity", "drug hypersensitivity",
        "systemic inflammatory",
    ],
    "reproductive": [
        "breast", "uterus", "menstrual", "period", "vaginal", "prostate",
        "sexual", "libido", "erectile", "fertility",
        # MedDRA PT terms
        "amenorrhoea", "amenorrhea",    # British + US
        "dysmenorrhoea", "dysmenorrhea",
        "gynecomastia", "gynaecomastia",
        "ovarian", "testicular", "endometrial",
        "menorrhagia", "oligomenorrhoea",
    ],
}
