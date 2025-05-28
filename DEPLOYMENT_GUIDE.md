# CV Optimizer Pro - Deployment Guide

## 🚀 Deploy na Render.com

### Krok 1: Przygotowanie repozytorium
1. Stwórz nowe repozytorium na GitHub
2. Wgraj wszystkie pliki z folderu `CV-generator-deploy`
3. Upewnij się, że `render.yaml` jest w głównym katalogu

### Krok 2: Deploy na Render
1. Zaloguj się na [render.com](https://render.com)
2. Kliknij "New +" → "Blueprint"
3. Podłącz swoje repozytorium GitHub
4. Render automatycznie wykryje `render.yaml`
5. Kliknij "Apply"

### Krok 3: Konfiguracja zmiennych środowiskowych
W Render Dashboard ustaw następujące Environment Variables:

```env
OPENROUTER_API_KEY=sk-or-v1-[twój-klucz]
STRIPE_SECRET_KEY=sk_test_[twój-klucz-stripe]
VITE_STRIPE_PUBLIC_KEY=pk_test_[twój-publiczny-klucz-stripe]
SESSION_SECRET=[automatycznie-generowany]
DATABASE_URL=[automatycznie-ustawiony]
```

## 📱 PWA Builder Setup

### Automatyczna konfiguracja PWA
Aplikacja jest już przygotowana jako PWA:
- ✅ `manifest.json` - konfiguracja PWA
- ✅ `service-worker.js` - obsługa offline
- ✅ Meta tagi PWA w `<head>`
- ✅ Ikony aplikacji (wymagane: dodanie prawdziwych ikon PNG)

### Krok 1: Generowanie ikon
1. Idź na [PWABuilder.com](https://pwabuilder.com)
2. Wpisz URL swojej aplikacji na Render
3. Przejdź do "Images" → "Generate Icons"
4. Pobierz wygenerowane ikony
5. Wgraj je do `static/icons/`

### Krok 2: Publikacja PWA
1. Na PWABuilder kliknij "Package For Stores"
2. Wybierz platformy (Google Play, Microsoft Store, App Store)
3. Pobierz pakiety aplikacji
4. Wgraj na wybrane sklepy

## 🔧 Wymagane pliki deployment

### ✅ Pliki już utworzone:
- `render.yaml` - konfiguracja Render
- `Dockerfile` - kontener Docker
- `manifest.json` - manifest PWA
- `service-worker.js` - service worker
- `.gitignore` - ignorowane pliki
- `requirements.txt` - zależności Python

### 📋 Struktura folderów:
```
CV-generator-deploy/
├── app.py              # Główna aplikacja Flask
├── requirements.txt    # Zależności Python
├── render.yaml        # Konfiguracja Render
├── Dockerfile         # Kontener Docker
├── manifest.json      # Manifest PWA
├── service-worker.js  # Service Worker
├── static/
│   ├── css/           # Style CSS
│   ├── js/            # JavaScript
│   └── icons/         # Ikony PWA (wymagane: PNG)
├── templates/         # Szablony HTML
└── utils/             # Narzędzia (AI, PDF)
```

## 🌐 Po deployment

### URL aplikacji:
- Render: `https://[nazwa-aplikacji].onrender.com`
- Custom domain: można skonfigurować w Render

### PWA Features:
- ✅ Instalacja na urządzeniu
- ✅ Tryb offline (podstawowy)
- ✅ Ikona aplikacji
- ✅ Splash screen
- ✅ Responsywny design

## 🔐 Bezpieczeństwo

### Environment Variables (wymagane):
1. `OPENROUTER_API_KEY` - dla AI
2. `STRIPE_SECRET_KEY` - dla płatności
3. `VITE_STRIPE_PUBLIC_KEY` - frontend Stripe
4. `SESSION_SECRET` - sesje użytkowników
5. `DATABASE_URL` - baza danych (auto)

### Uwagi:
- Nigdy nie commituj kluczy API do repozytorium
- Używaj Environment Variables w Render
- Baza danych PostgreSQL automatycznie skonfigurowana

## 📊 Monitoring

### Render Dashboard:
- Logi aplikacji
- Metryki wydajności
- Status deploymentów
- Statystyki bazy danych

### PWA Analytics:
- Google Analytics (już skonfigurowany)
- Service Worker metrics
- Installation tracking