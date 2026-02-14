"""
SEO Content Enrichment Engine
==============================
Zero-cost, template-based content enrichment that makes each job posting
unique for Google indexing. No AI API calls needed.

3 layers:
1. Randomized unique intro (840+ combinations)
2. Location context paragraphs (per city)
3. Somali language keywords/tags
"""

import random

# ==========================================
# 1. UNIQUE INTRO TEMPLATES
# ==========================================

INTRO_OPENERS = [
    "{org} is currently seeking a qualified {title} to join their team in {location}.",
    "A new {type} opportunity for a {title} has been announced by {org} in {location}.",
    "{org}, based in {location}, is looking for an experienced {title} to fill an open position.",
    "An exciting {type} vacancy for a {title} is now available at {org}, {location}.",
    "{org} has announced a {type} opening for the role of {title} in {location}.",
    "A {title} position is currently open at {org} with the duty station in {location}.",
    "{org} invites qualified candidates to apply for the {title} role in {location}.",
    "The position of {title} at {org} in {location} is now open for applications.",
    "Are you an experienced professional? {org} is hiring a {title} in {location}.",
    "{org} is recruiting a {title} for their {location} office.",
    "Join {org} as a {title} — this {type} role is based in {location}.",
    "Vacancy announcement: {org} seeks a {title} for their operations in {location}.",
    "{location}-based {org} is looking to fill the role of {title}.",
    "A career opportunity awaits at {org} — they are hiring a {title} in {location}.",
    "Seeking a new challenge? {org} has a {title} position open in {location}.",
]

INTRO_MIDDLES = [
    "This role falls within the {sector} sector and requires candidates with {exp} of relevant experience.",
    "The ideal candidate will have {exp} of professional experience in the {sector} field.",
    "Candidates should bring {exp} of hands-on experience, preferably in the {sector} sector.",
    "This {sector} sector position calls for a professional with {exp} of demonstrated expertise.",
    "The role requires a skilled individual with {exp} of experience in {sector} or a related field.",
    "Professionals with a background in {sector} and at least {exp} of experience are encouraged to apply.",
    "With {exp} of experience required, this position is suited for mid-to-senior level professionals in {sector}.",
    "The successful candidate will bring strong {sector} experience spanning at least {exp}.",
]

INTRO_MIDDLES_NO_EXP = [
    "This position is within the {sector} sector.",
    "The role is part of the organization's {sector} operations.",
    "This opportunity is in the {sector} field.",
    "The position falls under the {sector} sector and is open to qualified professionals.",
]

INTRO_MIDDLES_NO_SECTOR = [
    "Candidates with {exp} of relevant professional experience are encouraged to apply.",
    "The ideal candidate will bring {exp} of demonstrated experience to this role.",
    "This role calls for a professional with at least {exp} of relevant experience.",
]

INTRO_CLOSERS_WITH_DEADLINE = [
    "Interested applicants should submit their applications before {deadline}.",
    "The application deadline is {deadline} — early applications are encouraged.",
    "Applications are open until {deadline}. Don't miss this opportunity.",
    "Submit your application by {deadline} to be considered for this role.",
    "The closing date for this vacancy is {deadline}.",
    "Qualified candidates are urged to apply before the {deadline} deadline.",
    "This position closes on {deadline}. Apply now to be considered.",
]

INTRO_CLOSERS_NO_DEADLINE = [
    "Interested candidates are encouraged to apply as soon as possible.",
    "Applications should be submitted at the earliest opportunity.",
    "Qualified professionals are invited to submit their applications promptly.",
    "Early applications are encouraged as the position may close once filled.",
]

# ==========================================
# 2. LOCATION CONTEXT PARAGRAPHS
# ==========================================

LOCATION_CONTEXT = {
    'hargeisa': "Hargeisa is the capital and largest city of Somaliland, serving as the region's main economic and administrative hub. The city is home to a growing number of international organizations, NGOs, and private sector companies, making it a key employment center in the Horn of Africa. Professionals relocating to Hargeisa will find a dynamic and rapidly developing urban environment.",

    'mogadishu': "Mogadishu, known locally as Muqdisho, is the capital of Somalia and the country's largest city. It serves as the political, economic, and cultural heart of the nation. The city hosts the headquarters of numerous UN agencies, international NGOs, and government institutions, offering diverse career opportunities for development and humanitarian professionals.",

    'garowe': "Garowe is the administrative capital of the Puntland State of Somalia. The city has developed into an important center for governance, education, and humanitarian operations in northeastern Somalia. Many international organizations maintain offices in Garowe, supporting development and resilience-building programs across the region.",

    'baidoa': "Baidoa is the interim capital of the South West State of Somalia. The city is strategically important for humanitarian operations and has a significant presence of international and local organizations working on food security, health, and livelihood programs. It offers opportunities for professionals in the humanitarian and development sectors.",

    'kismayo': "Kismayo is the commercial capital of the Jubaland State in southern Somalia. Situated along the Indian Ocean coast, it is an important port city and a growing center for trade, humanitarian assistance, and development programming. Opportunities in Kismayo span multiple sectors including logistics, agriculture, and community development.",

    'bosaso': "Bosaso is a major port city in the Puntland region and one of Somalia's busiest commercial centers. The city serves as a hub for trade, fishing, and maritime activities along the Gulf of Aden. International organizations and businesses operating in Bosaso offer opportunities in trade facilitation, development, and humanitarian assistance.",

    'burao': "Burao is the second-largest city in Somaliland and the capital of the Togdheer region. Known for its vibrant livestock market — one of the largest in the Horn of Africa — Burao is an important center for trade and commerce. The city offers opportunities in agriculture, livestock value chains, and community development.",

    'berbera': "Berbera is a historic port city in Somaliland located on the Gulf of Aden. The city is undergoing significant development with the modernization of its port facilities, creating new opportunities in logistics, trade, infrastructure, and maritime sectors. It serves as a strategic gateway for regional commerce.",

    'beledweyne': "Beledweyne is the capital of the Hiraan region in central Somalia, situated along the Shabelle River. The city is an important center for agricultural activities and has a growing presence of humanitarian organizations. Professionals with expertise in flood response, agriculture, and community resilience will find relevant opportunities here.",

    'galkayo': "Galkayo is a major city in central Somalia straddling the border between Puntland and Galmudug states. It serves as an important commercial and humanitarian hub for central Somalia. Multiple international organizations maintain operations here, focusing on peacebuilding, displacement response, and community development.",

    'jowhar': "Jowhar is the capital of the Hirshabelle State and an important agricultural center in the Shabelle valley. The city has a growing presence of government institutions and development organizations working on agricultural productivity, food security, and governance strengthening programs.",

    'nairobi': "Nairobi, Kenya's capital, is the largest city in East Africa and a major hub for international organizations, UN agencies, and multinational companies. The city serves as the regional coordination center for many Horn of Africa operations, offering diverse career opportunities across development, technology, finance, and humanitarian sectors.",

    'djibouti': "Djibouti City is the capital of the Republic of Djibouti, strategically located at the crossroads of Africa and the Middle East. The city hosts multiple international military bases, UN agencies, and development organizations, offering unique opportunities in logistics, maritime services, security, and international development.",

    'somaliland': "Somaliland is a self-declared republic in the Horn of Africa with a relatively stable political environment and growing economy. Employment opportunities are concentrated in the main cities of Hargeisa, Burao, and Berbera, spanning government, NGOs, telecoms, and the private sector.",

    'puntland': "Puntland is a semi-autonomous state in northeastern Somalia with its capital in Garowe. The region has a developing governance structure and hosts numerous international organizations. Employment opportunities center around humanitarian assistance, governance support, fisheries, and infrastructure development.",

    'somalia': "Somalia is located in the Horn of Africa and has a growing job market, particularly in the humanitarian, development, and private sectors. Major employment hubs include Mogadishu, Hargeisa, Garowe, Baidoa, and Kismayo, with opportunities from international NGOs, UN agencies, government institutions, and an expanding private sector.",

    'somalia & somaliland': "This position covers operations across both Somalia and Somaliland, offering a dynamic and impactful work environment. The Horn of Africa region presents unique professional challenges and opportunities in humanitarian response, development programming, governance, and private sector growth.",

    'jigjiga': "Jigjiga is the capital of the Somali Regional State (Somali Galbeed) in eastern Ethiopia. The city serves as an important economic center for the ethnic Somali population in Ethiopia and hosts various government and non-governmental organizations working on development and humanitarian programs.",
}

# ==========================================
# 3. SOMALI KEYWORDS
# ==========================================

SOMALI_SECTOR_TAGS = {
    'education': 'Waxbarasho', 'health': 'Caafimaad', 'consultancies': 'La-talinta',
    'engineering': 'Injineernimo', 'finance': 'Maaliyadda', 'administration': 'Maamulka',
    'logistics': 'Saadka & Gaadiidka', 'ict/technology/computers': 'Tiknoolajiyada',
    'protection': 'Ilaalinta', 'wash': 'Biyaha & Nadaafadda', 'food security': 'Amniga Cuntada',
    'nutrition': 'Nafaqada', 'agriculture': 'Beeraha', 'governance': 'Dowladnimada',
    'human resources': 'Shaqaalaha', 'communication': 'Isgaarsiinta', 'security': 'Amniga',
    'legal': 'Sharciga', 'procurement': 'Iibsiga',
    'monitoring and evaluation': 'Kormeerka & Qiimaynta',
    'health/wash': 'Caafimaad & Nadaafadda',
}

SOMALI_TYPE_TAGS = {
    'full time': 'Shaqo Buuxda', 'part time': 'Shaqo Waqti-gaaban',
    'consultant': 'La-talin', 'internship': 'Tababar',
    'temporary': 'Ku-meel-gaar', 'freelancer': 'Shaqo Madax-bannaan',
}

SOMALI_LOCATION_TAGS = {
    'mogadishu': 'Shaqo Muqdisho', 'hargeisa': 'Shaqo Hargeysa',
    'garowe': 'Shaqo Garoowe', 'kismayo': 'Shaqo Kismaayo',
    'baidoa': 'Shaqo Baydhabo', 'bosaso': 'Shaqo Boosaaso',
    'burao': 'Shaqo Burco', 'berbera': 'Shaqo Berbera',
    'beledweyne': 'Shaqo Beledweyne', 'galkayo': 'Shaqo Gaalkacyo',
    'jowhar': 'Shaqo Jawhar', 'nairobi': 'Shaqo Nairobi',
    'djibouti': 'Shaqo Jabuuti',
}


def get_somali_tags(job):
    """Generate Somali keyword tags for a job"""
    tags = set()
    job_type = (job.get('type') or '').lower()
    sector = (job.get('sector') or job.get('category') or '').lower()
    location = (job.get('location') or '').lower()

    for eng, som in SOMALI_SECTOR_TAGS.items():
        if eng in sector:
            tags.add(som)

    for eng, som in SOMALI_TYPE_TAGS.items():
        if eng in job_type:
            tags.add(som)

    for eng, som in SOMALI_LOCATION_TAGS.items():
        if eng in location:
            tags.add(som)

    if not any(t.startswith('Shaqo ') for t in tags):
        tags.add('Shaqo Soomaaliya')

    tags.add('Shaqo Cusub')  # "New Job"
    return list(tags)


# ==========================================
# MAIN ENRICHMENT FUNCTION
# ==========================================

def _fill(template, data):
    result = template
    for key, val in data.items():
        result = result.replace('{' + key + '}', val)
    return result


def enrich_description(job):
    """
    Takes a job dict and returns an enriched description string with:
    1. Unique intro paragraph
    2. Original description
    3. Location context
    4. Somali keywords
    """
    data = {
        'org': job.get('organization') or job.get('company') or 'The hiring organization',
        'title': job.get('title') or 'this position',
        'location': job.get('location') or 'Somalia',
        'type': (job.get('type') or 'full time').lower(),
        'sector': job.get('sector') or job.get('category') or '',
        'exp': job.get('experience') or '',
        'deadline': job.get('deadline') or '',
    }

    # --- Layer 1: Unique intro ---
    intro = _fill(random.choice(INTRO_OPENERS), data)

    if data['exp'] and data['sector']:
        intro += ' ' + _fill(random.choice(INTRO_MIDDLES), data)
    elif data['sector']:
        intro += ' ' + _fill(random.choice(INTRO_MIDDLES_NO_EXP), data)
    elif data['exp']:
        intro += ' ' + _fill(random.choice(INTRO_MIDDLES_NO_SECTOR), data)

    if data['deadline']:
        intro += ' ' + _fill(random.choice(INTRO_CLOSERS_WITH_DEADLINE), data)
    else:
        intro += ' ' + _fill(random.choice(INTRO_CLOSERS_NO_DEADLINE), data)

    # --- Layer 2: Original description ---
    original = job.get('description') or ''

    # --- Layer 3: Location context ---
    loc_key = (job.get('location') or 'somalia').lower().strip()
    location_para = LOCATION_CONTEXT.get(loc_key, LOCATION_CONTEXT.get('somalia', ''))

    # --- Layer 4: Somali tags ---
    tags = get_somali_tags(job)
    tags_line = 'Ereyada Soomaaliga (Somali Keywords): ' + ' \u2022 '.join(tags) if tags else ''

    # --- Assemble ---
    parts = [intro, '']
    if original:
        parts.append(original)
        parts.append('')
    parts.append(f'--- About {job.get("location") or "Somalia"} ---')
    parts.append(location_para)
    parts.append('')
    if tags_line:
        parts.append(tags_line)

    return '\n'.join(parts).strip()
