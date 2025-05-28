import os
import json
import logging
import requests
import urllib.parse
from bs4 import BeautifulSoup
from utils.openrouter_api import send_api_request

logger = logging.getLogger(__name__)

def extract_job_info_from_url(url):
    """
    Automatycznie wyciąga tytuł stanowiska i opis pracy z linku do oferty
    Zwraca: {'job_title': str, 'job_description': str, 'company': str}
    """
    try:
        logger.info(f"Wyciąganie informacji z URL: {url}")
        
        # Sprawdź format URL
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Nieprawidłowy format URL")
        
        # Pobierz stronę
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pl,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = parsed_url.netloc.lower()
        
        # Wyciągnij informacje specyficzne dla różnych portali
        job_info = extract_by_domain(soup, domain)
        
        # Jeśli nie udało się wyciągnąć specyficznie, spróbuj ogólnych selektorów
        if not job_info['job_title'] or not job_info['job_description']:
            job_info = extract_generic(soup, job_info)
        
        # Użyj AI do poprawy i uzupełnienia informacji
        if job_info['job_title'] or job_info['job_description']:
            job_info = enhance_with_ai(job_info, url)
        
        logger.info(f"Pomyślnie wyciągnięto: tytuł='{job_info['job_title'][:50]}...', opis={len(job_info['job_description'])} znaków")
        
        return job_info
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd pobierania strony: {str(e)}")
        raise Exception(f"Nie udało się pobrać oferty z URL: {str(e)}")
    
    except Exception as e:
        logger.error(f"Błąd analizy URL: {str(e)}")
        raise Exception(f"Nie udało się przeanalizować oferty: {str(e)}")

def extract_by_domain(soup, domain):
    """Wyciąga informacje specyficzne dla różnych portali pracy"""
    job_info = {'job_title': '', 'job_description': '', 'company': ''}
    
    try:
        if 'linkedin.com' in domain:
            # LinkedIn
            title_elem = soup.select_one('.top-card-layout__title, .jobs-unified-top-card__job-title, h1')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            company_elem = soup.select_one('.top-card-layout__card .topcard__org-name-link, .jobs-unified-top-card__company-name')
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            desc_elem = soup.select_one('.description__text, .show-more-less-html__markup, .jobs-description__content')
            if desc_elem:
                job_info['job_description'] = desc_elem.get_text(separator='\n', strip=True)
                
        elif 'indeed.com' in domain:
            # Indeed
            title_elem = soup.select_one('.jobsearch-JobInfoHeader-title, h1[data-testid="job-title"]')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            company_elem = soup.select_one('[data-testid="inlineHeader-companyName"], .icl-u-lg-mr--sm')
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            desc_elem = soup.select_one('#jobDescriptionText, [data-testid="job-description"]')
            if desc_elem:
                job_info['job_description'] = desc_elem.get_text(separator='\n', strip=True)
                
        elif 'pracuj.pl' in domain:
            # Pracuj.pl
            title_elem = soup.select_one('[data-test="text-jobTitle"], .offer-viewBBjNq h1')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            company_elem = soup.select_one('[data-test="text-employer"], .offer-company-name')
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            desc_containers = soup.select('[data-test="section-description-text"], [data-test="section-requirements-text"], [data-test="section-offered-text"]')
            if desc_containers:
                job_info['job_description'] = '\n\n'.join([c.get_text(separator='\n', strip=True) for c in desc_containers])
                
        elif 'nofluffjobs.com' in domain:
            # NoFluffJobs
            title_elem = soup.select_one('h1[data-cy="JobOfferTitle"], .posting-details-description h1')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            company_elem = soup.select_one('[data-cy="CompanyName"], .company-name')
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            desc_elem = soup.select_one('[data-cy="JobOfferDescription"], .posting-details-description')
            if desc_elem:
                job_info['job_description'] = desc_elem.get_text(separator='\n', strip=True)
                
        elif 'olx.pl' in domain:
            # OLX Praca - zaktualizowane selektory
            title_elem = soup.select_one('h1, [data-cy="ad_title"], .css-1juynto, .ad-title')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            # Szukaj opisu w różnych miejscach
            desc_containers = soup.select('[data-cy="ad_description"], .css-g5mtl5, .description, .ad-description, .ad-description-full')
            if desc_containers:
                job_info['job_description'] = desc_containers[0].get_text(separator='\n', strip=True)
            else:
                # Jeśli nie ma specyficznych selektorów, szukaj w całej treści
                # Znajdź wszystkie div-y i p-ki które mogą zawierać opis
                potential_desc = soup.select('div:has(p), section, article, .content, .details')
                for container in potential_desc:
                    text = container.get_text(separator='\n', strip=True)
                    if len(text) > 100 and 'opis' in text.lower() or 'stanowisko' in text.lower() or 'wymagania' in text.lower():
                        job_info['job_description'] = text
                        break
                
        elif 'justjoin.it' in domain:
            # JustJoin.it
            title_elem = soup.select_one('h1[data-test-id="offer-title"], .MuiTypography-h1')
            if title_elem:
                job_info['job_title'] = title_elem.get_text(strip=True)
            
            company_elem = soup.select_one('[data-test-id="company-name"], .MuiTypography-h6')
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            desc_elem = soup.select_one('[data-test-id="offer-description"], .OfferDescription')
            if desc_elem:
                job_info['job_description'] = desc_elem.get_text(separator='\n', strip=True)
                
    except Exception as e:
        logger.warning(f"Błąd podczas wyciągania dla domeny {domain}: {str(e)}")
    
    return job_info

def extract_generic(soup, existing_info):
    """Ogólne wyciąganie informacji gdy specyficzne selektory nie działają"""
    
    # Jeśli nie ma tytułu, szukaj w ogólnych miejscach
    if not existing_info['job_title']:
        title_selectors = [
            'h1', '.job-title', '.offer-title', '.position-title',
            '[class*="title"]', '[class*="job"]', '[class*="position"]',
            'title', '.headline', '.job-header h1'
        ]
        
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title_text = elem.get_text(strip=True)
                if 5 < len(title_text) < 100:  # Rozsądna długość tytułu
                    existing_info['job_title'] = title_text
                    break
    
    # Jeśli nie ma opisu, szukaj w ogólnych miejscach
    if not existing_info['job_description']:
        desc_selectors = [
            '.job-description', '.offer-description', '.description',
            '.job-content', '.offer-content', '.content',
            '[class*="description"]', '[class*="details"]',
            'article', '.main-content', '.job-details'
        ]
        
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                desc_text = elem.get_text(separator='\n', strip=True)
                if len(desc_text) > 100:  # Minimum dla opisu
                    existing_info['job_description'] = desc_text
                    break
    
    # Specjalna obsługa dla OLX - wyciągnij tekst z całej strony i filtruj
    if not existing_info['job_description'] and 'olx.pl' in soup.get_text().lower():
        all_text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        
        # Znajdź linie które mogą zawierać opis pracy
        job_related_lines = []
        job_keywords = ['stanowisko', 'praca', 'wymagania', 'obowiązki', 'opis', 'oferujemy', 'poszukujemy', 'mile widziane']
        
        for i, line in enumerate(lines):
            if len(line) > 20 and any(keyword in line.lower() for keyword in job_keywords):
                # Dodaj tę linię i kilka następnych
                for j in range(max(0, i-1), min(len(lines), i+5)):
                    if lines[j] not in job_related_lines and len(lines[j]) > 10:
                        job_related_lines.append(lines[j])
        
        if job_related_lines:
            existing_info['job_description'] = '\n'.join(job_related_lines[:20])  # Maksymalnie 20 linii
    
    # Jeśli nadal nie ma opisu, weź text z body (z filtrowaniem)
    if not existing_info['job_description'] and soup.body:
        # Usuń niepotrzebne elementy
        for tag in soup.select('nav, header, footer, script, style, iframe, aside, .sidebar, .menu'):
            tag.decompose()
        
        body_text = soup.body.get_text(separator='\n', strip=True)
        
        # Filtruj tekst do najważniejszych części
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        filtered_lines = []
        
        job_keywords = [
            'wymagania', 'requirements', 'obowiązki', 'responsibilities',
            'kwalifikacje', 'qualifications', 'umiejętności', 'skills',
            'doświadczenie', 'experience', 'oferujemy', 'benefits',
            'opis stanowiska', 'job description', 'zakres obowiązków'
        ]
        
        relevant_section = False
        for line in lines:
            if any(keyword.lower() in line.lower() for keyword in job_keywords):
                relevant_section = True
            if relevant_section and len(line) > 20:
                filtered_lines.append(line)
            if len('\n'.join(filtered_lines)) > 2000:  # Limit długości
                break
        
        if filtered_lines:
            existing_info['job_description'] = '\n'.join(filtered_lines)
    
    return existing_info

def enhance_with_ai(job_info, url):
    """Używa AI do poprawy i uzupełnienia wyciągniętych informacji"""
    try:
        # Przygotuj prompt dla AI
        prompt = f"""
Przeanalizuj poniższe informacje wyciągnięte z oferty pracy i popraw je:

URL: {url}
Tytuł stanowiska: {job_info['job_title']}
Firma: {job_info['company']}
Opis (pierwsze 1000 znaków): {job_info['job_description'][:1000]}...

Zadania:
1. Jeśli tytuł stanowiska jest niepełny lub zawiera śmieci - popraw go do czystej formy
2. Jeśli opis jest za długi (>3000 znaków) - skróć do najważniejszych informacji
3. Wyciągnij najważniejsze wymagania i obowiązki
4. Uporządkuj informacje w czytelny sposób

Zwróć TYLKO JSON w formacie:
{{
    "job_title": "poprawiony tytuł stanowiska",
    "job_description": "uporządkowany i skrócony opis stanowiska",
    "company": "nazwa firmy"
}}
"""
        
        # Wywołaj AI
        ai_response = send_api_request(prompt, max_tokens=1000, language='pl')
        
        # Spróbuj sparsować odpowiedź AI
        try:
            # Znajdź JSON w odpowiedzi
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                enhanced_info = json.loads(json_match.group())
                
                # Sprawdź czy AI poprawiło informacje
                if enhanced_info.get('job_title') and len(enhanced_info['job_title']) > 3:
                    job_info['job_title'] = enhanced_info['job_title']
                
                if enhanced_info.get('job_description') and len(enhanced_info['job_description']) > 50:
                    job_info['job_description'] = enhanced_info['job_description']
                
                if enhanced_info.get('company') and len(enhanced_info['company']) > 2:
                    job_info['company'] = enhanced_info['company']
                    
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Nie udało się sparsować odpowiedzi AI: {e}")
            # Jeśli AI nie zwróciło poprawnego JSON, zostaw oryginalne dane
            
    except Exception as e:
        logger.warning(f"Błąd podczas ulepszania z AI: {e}")
        # Jeśli AI nie działa, zostaw oryginalne dane
    
    return job_info