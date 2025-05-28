
import os
import json
import logging
import requests
import urllib.parse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen-2.5-72b-instruct:free"

DEEP_REASONING_PROMPT = """You are a deep thinking AI, you may use extremely long chains of thought to deeply consider the problem and deliberate with yourself via systematic reasoning processes to help come to a correct solution prior to answering. You should enclose your thoughts and internal monologue inside <think> </think> tags, and then provide your solution or response to the problem."""

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://cv-optimizer-pro.repl.co/"
}

def send_api_request(prompt, max_tokens=2000, language='pl'):
    """
    Send a request to the OpenRouter API with language specification
    """
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter API key not found")
        raise ValueError("OpenRouter API key not set in environment variables")
    
    # Language-specific system prompts
    language_prompts = {
        'pl': "Jesteś ekspertem w optymalizacji CV i doradcą kariery. ZAWSZE odpowiadaj w języku polskim, niezależnie od języka CV lub opisu pracy. Używaj polskiej terminologii HR i poprawnej polszczyzny.",
        'en': "You are an expert resume editor and career advisor. ALWAYS respond in English, regardless of the language of the CV or job description. Use proper English HR terminology and grammar."
    }
    
    system_prompt = DEEP_REASONING_PROMPT + "\n" + language_prompts.get(language, language_prompts['pl'])
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    try:
        logger.debug(f"Sending request to OpenRouter API")
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        logger.debug("Received response from OpenRouter API")
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise ValueError("Unexpected API response format")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"Failed to communicate with OpenRouter API: {str(e)}")
    
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing API response: {str(e)}")
        raise Exception(f"Failed to parse OpenRouter API response: {str(e)}")

def analyze_cv_score(cv_text, job_description="", language='pl'):
    """
    Analizuje CV i przyznaje ocenę punktową 1-100 z szczegółowym uzasadnieniem
    """
    prompt = f"""
    Przeanalizuj poniższe CV i przyznaj mu ocenę punktową od 1 do 100, gdzie:
    - 90-100: Doskonałe CV, gotowe do wysłania
    - 80-89: Bardzo dobre CV z drobnymi usprawnieniami
    - 70-79: Dobre CV wymagające kilku poprawek
    - 60-69: Przeciętne CV wymagające znaczących poprawek
    - 50-59: Słabe CV wymagające dużych zmian
    - Poniżej 50: CV wymagające całkowitego przepisania

    CV do oceny:
    {cv_text}

    {"Wymagania z oferty pracy: " + job_description if job_description else ""}

    Uwzględnij w ocenie:
    1. Strukturę i organizację treści (20 pkt)
    2. Klarowność i zwięzłość opisów (20 pkt)
    3. Dopasowanie do wymagań stanowiska (20 pkt)
    4. Obecność słów kluczowych branżowych (15 pkt)
    5. Prezentację osiągnięć i rezultatów (15 pkt)
    6. Gramatykę i styl pisania (10 pkt)

    Odpowiedź w formacie JSON:
    {{
        "score": [liczba 1-100],
        "grade": "[A+/A/B+/B/C+/C/D/F]",
        "category_scores": {{
            "structure": [1-20],
            "clarity": [1-20], 
            "job_match": [1-20],
            "keywords": [1-15],
            "achievements": [1-15],
            "language": [1-10]
        }},
        "strengths": ["punkt mocny 1", "punkt mocny 2", "punkt mocny 3"],
        "weaknesses": ["słabość 1", "słabość 2", "słabość 3"],
        "recommendations": ["rekomendacja 1", "rekomendacja 2", "rekomendacja 3"],
        "summary": "Krótkie podsumowanie oceny CV"
    }}
    """
    
    return send_api_request(prompt, max_tokens=2500, language=language)

def analyze_keywords_match(cv_text, job_description, language='pl'):
    """
    Analizuje dopasowanie słów kluczowych z CV do wymagań oferty pracy
    """
    if not job_description:
        return "Brak opisu stanowiska do analizy słów kluczowych."
    
    prompt = f"""
    Przeanalizuj dopasowanie słów kluczowych między CV a wymaganiami oferty pracy.

    CV:
    {cv_text}

    Oferta pracy:
    {job_description}

    Odpowiedź w formacie JSON:
    {{
        "match_percentage": [0-100],
        "found_keywords": ["słowo1", "słowo2", "słowo3"],
        "missing_keywords": ["brakujące1", "brakujące2", "brakujące3"],
        "recommendations": [
            "Dodaj umiejętność: [nazwa]",
            "Podkreśl doświadczenie w: [obszar]",
            "Użyj terminów branżowych: [terminy]"
        ],
        "priority_additions": ["najważniejsze słowo1", "najważniejsze słowo2"],
        "summary": "Krótkie podsumowanie analizy dopasowania"
    }}
    """
    
    return send_api_request(prompt, max_tokens=2000, language=language)

def check_grammar_and_style(cv_text, language='pl'):
    """
    Sprawdza gramatykę, styl i poprawność językową CV
    """
    prompt = f"""
    Przeanalizuj poniższe CV pod kątem gramatyki, stylu i poprawności językowej.

    CV:
    {cv_text}

    Sprawdź:
    1. Błędy gramatyczne i ortograficzne
    2. Spójność czasów gramatycznych
    3. Profesjonalność języka
    4. Klarowność przekazu
    5. Zgodność z konwencjami CV

    Odpowiedź w formacie JSON:
    {{
        "grammar_score": [1-10],
        "style_score": [1-10],
        "professionalism_score": [1-10],
        "errors": [
            {{"type": "gramatyka", "text": "błędny tekst", "correction": "poprawka", "line": "sekcja"}},
            {{"type": "styl", "text": "tekst do poprawy", "suggestion": "sugestia", "line": "sekcja"}}
        ],
        "style_suggestions": [
            "Użyj bardziej dynamicznych czasowników akcji",
            "Unikaj powtórzeń słów",
            "Zachowaj spójny format dat"
        ],
        "overall_quality": "ocena ogólna jakości językowej",
        "summary": "Podsumowanie analizy językowej"
    }}
    """
    
    return send_api_request(prompt, max_tokens=1500)

def optimize_for_position(cv_text, job_title, job_description="", language='pl'):
    """
    Optymalizuje CV pod konkretne stanowisko
    """
    prompt = f"""
    Zoptymalizuj poniższe CV specjalnie pod stanowisko: {job_title}

    CV:
    {cv_text}

    {"Wymagania z oferty: " + job_description if job_description else ""}

    Stwórz zoptymalizowaną wersję CV, która:
    1. Podkreśla najważniejsze umiejętności dla tego stanowiska
    2. Reorganizuje sekcje według priorytetów dla tej roli
    3. Dostosowuje język do branżowych standardów
    4. Maksymalizuje dopasowanie do wymagań
    5. Zachowuje autentyczność i prawdziwość informacji

    Odpowiedź w formacie JSON:
    {{
        "optimized_cv": "Zoptymalizowana wersja CV",
        "key_changes": ["zmiana 1", "zmiana 2", "zmiana 3"],
        "focus_areas": ["obszar 1", "obszar 2", "obszar 3"],
        "added_elements": ["dodany element 1", "dodany element 2"],
        "positioning_strategy": "Strategia pozycjonowania kandydata",
        "summary": "Podsumowanie optymalizacji"
    }}
    """
    
    return send_api_request(prompt, max_tokens=2500)

def generate_interview_tips(cv_text, job_description="", language='pl'):
    """
    Generuje spersonalizowane tipy na rozmowę kwalifikacyjną
    """
    prompt = f"""
    Na podstawie CV i opisu stanowiska, przygotuj spersonalizowane tipy na rozmowę kwalifikacyjną.

    CV:
    {cv_text}

    {"Stanowisko: " + job_description if job_description else ""}

    Odpowiedź w formacie JSON:
    {{
        "preparation_tips": [
            "Przygotuj się na pytanie o [konkretny aspekt z CV]",
            "Przećwicz opowiadanie o projekcie [nazwa projektu]",
            "Badź gotowy na pytania techniczne o [umiejętność]"
        ],
        "strength_stories": [
            {{"strength": "umiejętność", "story_outline": "jak opowiedzieć o sukcesie", "example": "konkretny przykład z CV"}},
            {{"strength": "osiągnięcie", "story_outline": "struktura opowieści", "example": "przykład z doświadczenia"}}
        ],
        "weakness_preparation": [
            {{"potential_weakness": "obszar do poprawy", "how_to_address": "jak to przedstawić pozytywnie"}},
            {{"potential_weakness": "luka w CV", "how_to_address": "jak wytłumaczyć"}}
        ],
        "questions_to_ask": [
            "Przemyślane pytanie o firmę/zespół",
            "Pytanie o rozwój w roli",
            "Pytanie o wyzwania stanowiska"
        ],
        "research_suggestions": [
            "Sprawdź informacje o: [aspekt firmy]",
            "Poznaj ostatnie projekty firmy",
            "Zbadaj kulturę organizacyjną"
        ],
        "summary": "Kluczowe rady dla tego kandydata"
    }}
    """
    
    return send_api_request(prompt, max_tokens=2000)

def optimize_cv(cv_text, job_description, language='pl', is_premium=False, payment_verified=False):
    """
    Create an optimized version of CV using ONLY authentic data from the original CV
    Premium users get extended token limits for more detailed CV generation
    """
    prompt = f"""
    ZADANIE: Automatycznie rozpoznaj branżę/sektor na podstawie CV, a następnie zoptymalizuj je pod kątem tej branży i stanowiska, używając WYŁĄCZNIE prawdziwych informacji z oryginalnego CV.

    ABSOLUTNE ZASADY - PRZECZYTAJ UWAŻNIE:
    1. ❌ ZAKAZ WYMYŚLANIA: NIE dodawaj żadnych nowych informacji, firm, stanowisk, dat, liczb, procent, osiągnięć
    2. ❌ ZAKAZ DODAWANIA: NIE twórz nowych umiejętności, certyfikatów, projektów czy doświadczeń
    3. ✅ DOZWOLONE: Tylko przepisanie istniejących informacji z CV w bardziej profesjonalny sposób
    4. ✅ DOZWOLONE: Uporządkowanie i lepsze sformułowanie tego, co już jest w CV
    5. ✅ DOSTOSOWANIE BRANŻOWE: Użyj terminologii i stylu właściwego dla rozpoznanej branży

    KROK 1 - ROZPOZNANIE BRANŻY:
    Na podstawie doświadczenia zawodowego, umiejętności i wykształcenia określ główną branżę/sektor:
    - IT/Technologie (programowanie, systemy, data science)
    - Finanse/Bankowość (księgowość, analizy finansowe, banking)
    - Medycyna/Zdrowie (opieka zdrowotna, farmacja, medycyna)
    - Edukacja (nauczanie, szkolenia, rozwój)
    - Marketing/Sprzedaż (digital marketing, sprzedaż, reklama)
    - Logistyka/Transport (łańcuch dostaw, kurierzy, magazyny)
    - Inżynieria/Produkcja (mechanical, electrical, civil engineering)
    - HR/Zarządzanie (kadry, zarządzanie projektami)
    - Inne (określ konkretnie)

    INSTRUKCJE SZCZEGÓŁOWE Z KONTEKSTEM BRANŻOWYM:

    1. DANE OSOBOWE:
       - Przepisz dokładnie imię, nazwisko i kontakt z oryginalnego CV
       - NIE dodawaj nowych informacji kontaktowych

    2. PODSUMOWANIE ZAWODOWE:
       - Napisz krótkie podsumowanie bazując TYLKO na doświadczeniu z CV
       - Użyj tylko tych umiejętności, które są faktycznie wymienione w CV
       - NIE wymyślaj branży ani specjalizacji, których nie ma w oryginale

    3. DOŚWIADCZENIE ZAWODOWE:
       - Przepisz każde stanowisko DOKŁADNIE jak w oryginale (firma, stanowisko, daty)
       - Dla każdego miejsca pracy napisz 3-4 punkty opisujące obowiązki
       - Bazuj punkty TYLKO na informacjach z oryginalnego CV
       - Użyj profesjonalnych czasowników (planowałem, koordynowałem, obsługiwałem)
       - NIE dodawaj liczb, procent ani wymyślonych osiągnięć

    4. UMIEJĘTNOŚCI:
       - Przepisz TYLKO te umiejętności, które są wymienione w oryginalnym CV
       - Pogrupuj je w kategorie (np. Techniczne, Komunikacyjne, Zawodowe)
       - NIE dodawaj nowych umiejętności

    5. WYKSZTAŁCENIE:
       - Przepisz dokładnie informacje o wykształceniu z CV
       - NIE dodawaj kursów czy certyfikatów, których nie ma w oryginale

    6. DOPASOWANIE DO STANOWISKA:
       - Wyeksponuj te elementy z CV, które pasują do opisu stanowiska
       - Ale NIE dodawaj nowych elementów - tylko lepiej opisuj istniejące

    PRZYKŁAD DOBREGO PODEJŚCIA:
    Oryginał: "Dostarczanie paczek"
    Zoptymalizowane: "Realizowałem terminowe dostawy paczek do klientów"

    PRZYKŁAD ZŁEGO PODEJŚCIA (NIE RÓB TEGO):
    ❌ "Zwiększyłem efektywność dostaw o 25%" (gdy nie ma takiej informacji w CV)
    ❌ "Zarządzałem zespołem 5 kurierów" (gdy nie ma takiej informacji w CV)

    ORYGINALNE CV:
    {cv_text}

    STANOWISKO, DO KTÓREGO OPTYMALIZUJEMY:
    {job_description}

    WYGENERUJ: Profesjonalne CV używając WYŁĄCZNIE informacji z oryginalnego CV, bez dodawania żadnych wymyślonych elementów.

    ODPOWIEDŹ W FORMACIE JSON:
    {{
        "detected_industry": "rozpoznana branża/sektor",
        "industry_keywords": ["słowo kluczowe 1", "słowo kluczowe 2", "słowo kluczowe 3"],
        "optimized_cv": "Kompletne zoptymalizowane CV z branżowym dostosowaniem",
        "key_improvements": [
            "Dostosowano terminologię do branży [nazwa branży]",
            "Podkreślono kluczowe umiejętności [konkretne umiejętności]",
            "Wzmocniono sekcję [nazwa sekcji]"
        ],
        "ats_compatibility_score": "[0-100]",
        "job_match_score": "[0-100]",
        "positioning_strategy": "Jak kandydat jest pozycjonowany w branży",
        "summary": "Zwięzłe podsumowanie wprowadzonych ulepszeń"
    }}"""
    
    # Rozszerzony limit tokenów dla płacących użytkowników
    if is_premium or payment_verified:
        # Płacący użytkownicy - znacznie rozszerzony limit tokenów
        max_tokens = 6000  # Bardzo duży limit dla kompletnego CV
        prompt += f"""
        
        INSTRUKCJE PREMIUM - PEŁNE CV:
        - Stwórz szczegółowe opisy każdego stanowiska (5-8 punktów na pozycję)
        - Dodaj rozbudowane podsumowanie zawodowe z kluczowymi osiągnięciami
        - Rozwinij każdą sekcję umiejętności z precyzyjnymi opisami
        - Zastosuj zaawansowane formatowanie profesjonalnego CV
        - Użyj branżowej terminologii i zaawansowanego języka biznesowego
        - Stwórz CV gotowe do wysłania do najlepszych firm i korporacji
        - Wykorzystaj pełny potencjał każdej informacji z oryginalnego CV
        """
    else:
        # Bezpłatni użytkownicy - podstawowy limit
        max_tokens = 3000  # Zwiększony z 2500 dla lepszej jakości
        prompt += f"""
        
        INSTRUKCJE STANDARD:
        - Stwórz solidną optymalizację CV (3-4 punkty na pozycję)
        - Dodaj profesjonalne podsumowanie zawodowe
        - Uporządkuj umiejętności w logiczne kategorie
        - Zastosuj czytelne i spójne formatowanie
        """
    
    return send_api_request(prompt, max_tokens=max_tokens, language=language)

def generate_recruiter_feedback(cv_text, job_description="", language='pl'):
    """
    Generate feedback on a CV as if from an AI recruiter
    """
    context = ""
    if job_description:
        context = f"Opis stanowiska do kontekstu:\n{job_description}"
        
    prompt = f"""
    ZADANIE: Jesteś doświadczonym rekruterem. Przeanalizuj to CV i udziel szczegółowej, konstruktywnej opinii w języku polskim.
    
    ⚠️ KLUCZOWE: Oceniaj TYLKO to co faktycznie jest w CV. NIE ZAKŁADAJ, NIE DOMYŚLAJ się i NIE DODAWAJ informacji, których tam nie ma.
    
    Uwzględnij w ocenie:
    1. Ogólne wrażenie i pierwsza reakcja na podstawie faktycznej treści CV
    2. Mocne strony i słabości wynikające z konkretnych informacji w CV
    3. Ocena formatowania i struktury CV
    4. Jakość treści i sposób prezentacji faktycznych doświadczeń
    5. Kompatybilność z systemami ATS
    6. Konkretne sugestie poprawek oparte na tym co jest w CV
    7. Ocena ogólna w skali 1-10
    8. Prawdopodobieństwo zaproszenia na rozmowę
    
    {context}
    
    CV do oceny:
    {cv_text}
    
    Odpowiedź w formacie JSON:
    {{
        "overall_impression": "Pierwsze wrażenie oparte na faktycznej treści CV",
        "rating": [1-10],
        "strengths": [
            "Mocna strona 1 (konkretnie z CV)",
            "Mocna strona 2 (konkretnie z CV)", 
            "Mocna strona 3 (konkretnie z CV)"
        ],
        "weaknesses": [
            "Słabość 1 z sugestią poprawy (bazując na CV)",
            "Słabość 2 z sugestią poprawy (bazując na CV)",
            "Słabość 3 z sugestią poprawy (bazując na CV)"
        ],
        "formatting_assessment": "Ocena layoutu, struktury i czytelności faktycznej treści",
        "content_quality": "Ocena jakości treści rzeczywiście obecnej w CV",
        "ats_compatibility": "Czy CV przejdzie przez systemy automatycznej selekcji",
        "specific_improvements": [
            "Konkretna poprawa 1 (oparta na faktach z CV)",
            "Konkretna poprawa 2 (oparta na faktach z CV)",
            "Konkretna poprawa 3 (oparta na faktach z CV)"
        ],
        "interview_probability": "Prawdopodobieństwo zaproszenia oparte na faktach z CV",
        "recruiter_summary": "Podsumowanie z perspektywy rekrutera - tylko fakty z CV"
    }}
    
    Bądź szczery, ale konstruktywny. Oceniaj tylko to co rzeczywiście jest w CV, nie dodawaj od siebie.
    """
    
    return send_api_request(prompt, max_tokens=2000)

def generate_cover_letter(cv_text, job_description, language='pl'):
    """
    Generate a cover letter based on a CV and job description
    """
    prompt = f"""
    ZADANIE: Napisz spersonalizowany list motywacyjny w języku polskim WYŁĄCZNIE na podstawie faktów z CV.
    
    ⚠️ ABSOLUTNE WYMAGANIA:
    - Używaj TYLKO informacji faktycznie obecnych w CV
    - NIE WYMYŚLAJ doświadczeń, projektów, osiągnięć ani umiejętności
    - NIE DODAWAJ informacji, których nie ma w oryginalnym CV
    - Jeśli w CV brakuje jakichś informacji - nie uzupełniaj ich
    
    List motywacyjny powinien:
    - Być profesjonalnie sformatowany
    - Podkreślać umiejętności i doświadczenia faktycznie wymienione w CV
    - Łączyć prawdziwe doświadczenie kandydata z wymaganiami stanowiska
    - Zawierać przekonujące wprowadzenie oparte na faktach z CV
    - Mieć około 300-400 słów
    - Być napisany naturalnym, profesjonalnym językiem polskim
    
    Struktura listu:
    1. Nagłówek z danymi kontaktowymi
    2. Zwrot do adresata
    3. Wprowadzenie - dlaczego aplikujesz
    4. Główna treść - dopasowanie doświadczenia do wymagań
    5. Zakończenie z wyrażeniem zainteresowania
    6. Pozdrowienia
    
    Opis stanowiska:
    {job_description}
    
    CV kandydata:
    {cv_text}
    
    Napisz kompletny list motywacyjny w języku polskim. Użyj profesjonalnego, ale ciepłego tonu.
    """
    
    return send_api_request(prompt, max_tokens=2000)

def analyze_job_url(url):
    """
    Extract job description from a URL with improved handling for popular job sites
    """
    try:
        logger.debug(f"Analyzing job URL: {url}")
        
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        job_text = ""
        domain = parsed_url.netloc.lower()
        
        if 'linkedin.com' in domain:
            containers = soup.select('.description__text, .show-more-less-html, .jobs-description__content')
            if containers:
                job_text = containers[0].get_text(separator='\n', strip=True)
                
        elif 'indeed.com' in domain:
            container = soup.select_one('#jobDescriptionText')
            if container:
                job_text = container.get_text(separator='\n', strip=True)
                
        elif 'pracuj.pl' in domain:
            containers = soup.select('[data-test="section-benefit-expectations-text"], [data-test="section-description-text"]')
            if containers:
                job_text = '\n'.join([c.get_text(separator='\n', strip=True) for c in containers])
                
        elif 'olx.pl' in domain or 'praca.pl' in domain:
            containers = soup.select('.offer-description, .offer-content, .description')
            if containers:
                job_text = containers[0].get_text(separator='\n', strip=True)
        
        if not job_text:
            potential_containers = soup.select('.job-description, .description, .details, article, .job-content, [class*=job], [class*=description], [class*=offer]')
            if potential_containers:
                for container in potential_containers:
                    container_text = container.get_text(separator='\n', strip=True)
                    if len(container_text) > len(job_text):
                        job_text = container_text
            
            if not job_text and soup.body:
                for tag in soup.select('nav, header, footer, script, style, iframe'):
                    tag.decompose()
                
                job_text = soup.body.get_text(separator='\n', strip=True)
                
                if len(job_text) > 10000:
                    paragraphs = job_text.split('\n')
                    keywords = ['requirements', 'responsibilities', 'qualifications', 'skills', 'experience', 'about the job',
                                'wymagania', 'obowiązki', 'kwalifikacje', 'umiejętności', 'doświadczenie', 'o pracy']
                    
                    relevant_paragraphs = []
                    found_relevant = False
                    
                    for paragraph in paragraphs:
                        if any(keyword.lower() in paragraph.lower() for keyword in keywords):
                            found_relevant = True
                        if found_relevant and len(paragraph.strip()) > 50:
                            relevant_paragraphs.append(paragraph)
                    
                    if relevant_paragraphs:
                        job_text = '\n'.join(relevant_paragraphs)
        
        job_text = '\n'.join([' '.join(line.split()) for line in job_text.split('\n') if line.strip()])
        
        if not job_text:
            raise ValueError("Could not extract job description from the URL")
        
        logger.debug(f"Successfully extracted job description from URL")
        
        if len(job_text) > 4000:
            logger.debug(f"Job description is long ({len(job_text)} chars), summarizing with AI")
            job_text = summarize_job_description(job_text)
        
        return job_text
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching job URL: {str(e)}")
        raise Exception(f"Failed to fetch job posting from URL: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error analyzing job URL: {str(e)}")
        raise Exception(f"Failed to analyze job posting: {str(e)}")

def summarize_job_description(job_text):
    """
    Summarize a long job description using the AI
    """
    prompt = f"""
    ZADANIE: Wyciągnij i podsumuj kluczowe informacje z tego ogłoszenia o pracę w języku polskim.
    
    Uwzględnij:
    1. Stanowisko i nazwa firmy (jeśli podane)
    2. Wymagane umiejętności i kwalifikacje
    3. Obowiązki i zakres zadań
    4. Preferowane doświadczenie
    5. Inne ważne szczegóły (benefity, lokalizacja, itp.)
    6. TOP 5 słów kluczowych krytycznych dla tego stanowiska
    
    Tekst ogłoszenia:
    {job_text[:4000]}...
    
    Stwórz zwięzłe ale kompletne podsumowanie tego ogłoszenia, skupiając się na informacjach istotnych dla optymalizacji CV.
    Na końcu umieść sekcję "KLUCZOWE SŁOWA:" z 5 najważniejszymi terminami.
    
    Odpowiedź w języku polskim.
    """
    
    return send_api_request(prompt, max_tokens=1500)

def ats_optimization_check(cv_text, job_description="", language='pl'):
    """
    Check CV against ATS (Applicant Tracking System) and provide suggestions for improvement
    """
    context = ""
    if job_description:
        context = f"Ogłoszenie o pracę dla odniesienia:\n{job_description[:2000]}"
        
    prompt = f"""
    TASK: Przeprowadź dogłębną analizę CV pod kątem kompatybilności z systemami ATS (Applicant Tracking System) i wykryj potencjalne problemy.
    
    Przeprowadź następujące analizy:
    
    1. WYKRYWANIE PROBLEMÓW STRUKTURALNYCH:
       - Znajdź sekcje, które są w nieodpowiednich miejscach (np. doświadczenie zawodowe w sekcji zainteresowań)
       - Wskaż niespójności w układzie i formatowaniu
       - Zidentyfikuj zduplikowane informacje w różnych sekcjach
       - Zaznacz fragmenty tekstu, które wyglądają na wygenerowane przez AI
       - Znajdź ciągi znaków bez znaczenia lub losowe znaki
    
    2. ANALIZA FORMATOWANIA ATS:
       - Wykryj problemy z formatowaniem, które mogą utrudnić odczyt przez systemy ATS
       - Sprawdź, czy nagłówki sekcji są odpowiednio wyróżnione
       - Zweryfikuj, czy tekst jest odpowiednio podzielony na sekcje
       - Oceń czytelność dla systemów automatycznych
    
    3. ANALIZA SŁÓW KLUCZOWYCH:
       - Sprawdź gęstość słów kluczowych i trafność ich wykorzystania
       - Zidentyfikuj brakujące słowa kluczowe z branży/stanowiska
       - Oceń rozmieszczenie słów kluczowych w dokumencie
    
    4. OCENA KOMPLETNOŚCI:
       - Zidentyfikuj brakujące sekcje lub informacje, które są często wymagane przez ATS
       - Wskaż informacje, które należy uzupełnić
    
    5. WERYFIKACJA AUTENTYCZNOŚCI:
       - Zaznacz fragmenty, które wyglądają na sztuczne lub wygenerowane przez AI
       - Podkreśl niespójności między różnymi częściami CV
    
    6. OCENA OGÓLNA:
       - Oceń ogólną skuteczność CV w systemach ATS w skali 1-10
       - Podaj główne powody obniżonej oceny
    
    {context}
    
    CV do analizy:
    {cv_text}
    
    Odpowiedz w tym samym języku co CV. Jeśli CV jest po polsku, odpowiedz po polsku.
    Format odpowiedzi:
    
    1. OCENA OGÓLNA (skala 1-10): [ocena]
    
    2. PROBLEMY KRYTYCZNE:
    [Lista wykrytych krytycznych problemów]
    
    3. PROBLEMY ZE STRUKTURĄ:
    [Lista problemów strukturalnych]
    
    4. PROBLEMY Z FORMATOWANIEM ATS:
    [Lista problemów z formatowaniem]
    
    5. ANALIZA SŁÓW KLUCZOWYCH:
    [Wyniki analizy słów kluczowych]
    
    6. BRAKUJĄCE INFORMACJE:
    [Lista brakujących informacji]
    
    7. PODEJRZANE ELEMENTY:
    [Lista elementów, które wydają się wygenerowane przez AI lub są niespójne]
    
    8. REKOMENDACJE NAPRAWCZE:
    [Konkretne sugestie, jak naprawić zidentyfikowane problemy]
    
    9. PODSUMOWANIE:
    [Krótkie podsumowanie i zachęta]
    """
    
    return send_api_request(prompt, max_tokens=1800)

def analyze_cv_strengths(cv_text, job_title="analityk danych", language='pl'):
    """
    Analyze CV strengths for a specific job position and provide improvement suggestions
    """
    prompt = f"""
    ZADANIE: Przeprowadź dogłębną analizę mocnych stron tego CV w kontekście stanowiska {job_title}.
    
    1. Zidentyfikuj i szczegółowo omów 5-7 najsilniejszych elementów CV, które są najbardziej wartościowe dla pracodawcy.
    2. Dla każdej mocnej strony wyjaśnij, dlaczego jest ona istotna właśnie dla stanowiska {job_title}.
    3. Zaproponuj konkretne ulepszenia, które mogłyby wzmocnić te mocne strony.
    4. Wskaż obszary, które mogłyby zostać dodane lub rozbudowane, aby CV było jeszcze lepiej dopasowane do stanowiska.
    5. Zaproponuj, jak lepiej zaprezentować osiągnięcia i umiejętności, aby były bardziej przekonujące.
    
    CV:
    {cv_text}
    
    Pamiętaj, aby Twoja analiza była praktyczna i pomocna. Używaj konkretnych przykładów z CV i odnoś je do wymagań typowych dla stanowiska {job_title}.
    """
    
    return send_api_request(prompt, max_tokens=2500)

def generate_interview_questions(cv_text, job_description="", language='pl'):
    """
    Generate likely interview questions based on CV and job description
    """
    context = ""
    if job_description:
        context = f"Uwzględnij poniższe ogłoszenie o pracę przy tworzeniu pytań:\n{job_description[:2000]}"
        
    prompt = f"""
    TASK: Wygeneruj zestaw potencjalnych pytań rekrutacyjnych, które kandydat może otrzymać podczas rozmowy kwalifikacyjnej.
    
    Pytania powinny być:
    1. Specyficzne dla doświadczenia i umiejętności kandydata wymienionych w CV
    2. Dopasowane do stanowiska (jeśli podano opis stanowiska)
    3. Zróżnicowane - połączenie pytań technicznych, behawioralnych i sytuacyjnych
    4. Realistyczne i często zadawane przez rekruterów
    
    Uwzględnij po co najmniej 3 pytania z każdej kategorii:
    - Pytania o doświadczenie zawodowe
    - Pytania techniczne/o umiejętności
    - Pytania behawioralne
    - Pytania sytuacyjne
    - Pytania o motywację i dopasowanie do firmy/stanowiska
    
    {context}
    
    CV:
    {cv_text}
    
    Odpowiedz w tym samym języku co CV. Jeśli CV jest po polsku, odpowiedz po polsku.
    Dodatkowo, do każdego pytania dodaj krótką wskazówkę, jak można by na nie odpowiedzieć w oparciu o informacje z CV.
    """
    
    return send_api_request(prompt, max_tokens=2000)
