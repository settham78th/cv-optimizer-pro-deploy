
import os
import logging
from tempfile import mkdtemp
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import uuid
import stripe
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64
from datetime import datetime
from models import db, User, CVUpload, AnalysisResult
from forms import LoginForm, RegistrationForm, UserProfileForm, ChangePasswordForm
from utils.pdf_extraction import extract_text_from_pdf
from utils.openrouter_api import (
    optimize_cv, generate_recruiter_feedback,
    generate_cover_letter, analyze_job_url,
    ats_optimization_check, generate_interview_questions,
    analyze_cv_strengths, analyze_cv_score,
    analyze_keywords_match, check_grammar_and_style,
    optimize_for_position, generate_interview_tips
)


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Database configuration for Render
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

# Fix for Render PostgreSQL URL compatibility
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'pool_size': 10,
    'max_overflow': 20
}

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Configuration for file uploads
UPLOAD_FOLDER = mkdtemp()
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def add_watermark_to_cv(cv_text):
    """
    Dodaj znak wodny do CV dla niepłacących użytkowników
    """
    watermark = "\n\n" + "="*60 + "\n"
    watermark += "🔒 WERSJA DEMO - CV OPTIMIZER PRO\n"
    watermark += "Aby otrzymać pełną wersję CV bez znaku wodnego,\n"
    watermark += "dokonaj płatności 9,99 PLN\n"
    watermark += "="*60 + "\n"
    
    # Dodaj znak wodny na początku i na końcu
    watermarked_cv = watermark + cv_text + watermark
    
    return watermarked_cv

@app.route('/')
def index():
    # Enhanced index with user statistics
    user_stats = {
        'total_uploads': 0,
        'total_analyses': 0,
        'user_level': 'Początkujący',
        'improvement_score': 0
    }
    
    if current_user.is_authenticated:
        # Calculate user statistics
        user_cvs = CVUpload.query.filter_by(user_id=current_user.id).all()
        total_analyses = sum(len(cv.analysis_results) for cv in user_cvs)
        
        user_stats = {
            'total_uploads': len(user_cvs),
            'total_analyses': total_analyses,
            'user_level': get_user_level(len(user_cvs)),
            'improvement_score': min(95, 20 + total_analyses * 8)
        }
    
    return render_template('clean-index.html', user_stats=user_stats)

def get_user_level(cv_count):
    """Determine user level based on CV uploads"""
    if cv_count >= 5:
        return 'Diamond 💎'
    elif cv_count >= 3:
        return 'Gold 🥇'
    elif cv_count >= 1:
        return 'Silver 🥈'
    else:
        return 'Bronze 🥉'

@app.route('/ads.txt')
def ads_txt():
    """Serve ads.txt file for Google AdSense verification"""
    from flask import send_from_directory
    return send_from_directory('static', 'ads.txt', mimetype='text/plain')

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest file"""
    from flask import send_from_directory
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    """Serve service worker file"""
    from flask import send_from_directory
    return send_from_directory('.', 'service-worker.js', mimetype='application/javascript')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Sprawdź czy to email czy nazwa użytkownika
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data)
        ).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Zalogowano pomyślnie!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Nieprawidłowa nazwa użytkownika/email lub hasło.', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Sprawdź czy użytkownik już istnieje
        if User.query.filter_by(username=form.username.data).first():
            flash('Nazwa użytkownika już istnieje.', 'error')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email już jest zarejestrowany.', 'error')
            return render_template('auth/register.html', form=form)
        
        # Utwórz nowego użytkownika
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Rejestracja zakończona pomyślnie! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    # Pobierz ostatnie CV użytkownika
    recent_cvs = CVUpload.query.filter_by(user_id=current_user.id).order_by(CVUpload.uploaded_at.desc()).limit(5).all()
    return render_template('auth/profile.html', user=current_user, recent_cvs=recent_cvs)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = UserProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profil został zaktualizowany.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('auth/edit_profile.html', form=form)

@app.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Hasło zostało zmienione.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Obecne hasło jest nieprawidłowe.', 'error')
    
    return render_template('auth/change_password.html', form=form)

@app.route('/checkout')
def checkout():
    stripe_public_key = os.environ.get('VITE_STRIPE_PUBLIC_KEY')
    return render_template('checkout.html', stripe_public_key=stripe_public_key)

@app.route('/payment-options')
@login_required
def payment_options():
    """Payment options page - choose between one-time CV or Premium subscription"""
    stripe_public_key = os.environ.get('VITE_STRIPE_PUBLIC_KEY')
    return render_template('payment_options.html', stripe_public_key=stripe_public_key)

@app.route('/cv-generator')
@login_required
def cv_generator():
    """CV Generator page"""
    # Sprawdź dostęp do kreatora CV
    cv_builder_access = False
    if current_user.username == 'developer':
        cv_builder_access = True
    elif session.get('cv_builder_paid', False):
        cv_builder_access = True
    elif current_user.is_premium_active():
        cv_builder_access = True  # Premium ma dostęp do wszystkiego
    
    return render_template('cv_generator.html', cv_builder_access=cv_builder_access)

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    from datetime import datetime
    return render_template('privacy.html', moment=datetime.now())

@app.route('/premium-dashboard')
@login_required
def premium_dashboard():
    """Premium Dashboard - proste statystyki użytkowania"""
    if not current_user.is_premium_active():
        flash('Dashboard Premium jest dostępny tylko dla użytkowników Premium.', 'warning')
        return redirect(url_for('premium_subscription'))
    
    # Proste statystyki dla Premium
    user_cvs = CVUpload.query.filter_by(user_id=current_user.id).all()
    total_analyses = sum(len(cv.analysis_results) for cv in user_cvs)
    
    # Uproszczone statystyki
    stats = {
        'total_cvs': len(user_cvs),
        'total_optimizations': total_analyses,
        'user_level': get_user_level(len(user_cvs)),
        'improvement_score': min(95, 20 + total_analyses * 8),
        'cv_score': min(95, 60 + total_analyses * 5),
        'score_improvement': min(25, total_analyses * 2),
        'profile_views': 120 + total_analyses * 8,
        'views_change': min(30, total_analyses * 3),
        'applications_sent': total_analyses * 2,
        'response_rate': min(25, 10 + total_analyses),
        'match_percentage': min(85, 45 + total_analyses * 4),
        'is_premium': hasattr(current_user, 'is_premium') and current_user.is_premium
    }
    
    return render_template('premium_dashboard.html', user_stats=stats)

@app.route('/premium-subscription')
@login_required  
def premium_subscription():
    """Premium subscription page"""
    stripe_public_key = os.environ.get('VITE_STRIPE_PUBLIC_KEY')
    return render_template('premium_subscription.html', stripe_public_key=stripe_public_key)

@app.route('/api/create-cv-builder-payment', methods=['POST'])
@login_required  
def create_cv_builder_payment():
    """Create payment intent for CV Builder access"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=1499,  # 14,99 PLN
            currency='pln',
            metadata={'service': 'cv_builder', 'user_id': current_user.id}
        )
        return jsonify({
            'client_secret': intent.client_secret
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/create-premium-subscription', methods=['POST'])
@login_required
def create_premium_subscription():
    """Create Stripe checkout session for premium subscription"""
    try:
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'pln',
                    'product_data': {
                        'name': 'CV Optimizer Pro Premium',
                        'description': 'Miesięczna subskrypcja Premium z pełnym dostępem do dashboardu i analiz AI',
                    },
                    'unit_amount': 2900,  # 29.00 PLN w groszach
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('premium_success', _external=True),
            cancel_url=url_for('payment_options', _external=True),
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'subscription_type': 'premium'
            }
        )
        
        return jsonify({'url': stripe_session.url})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/premium-success')
@login_required
def premium_success():
    """Premium subscription success page - automatically activate premium for 1 month"""
    session_id = request.args.get('session_id')
    
    try:
        # Activate premium subscription for exactly 1 month
        current_user.activate_premium(months=1)
        current_user.stripe_session_id = session_id
        db.session.commit()
        
        flash('🎉 Subskrypcja Premium została aktywowana na dokładnie 1 miesiąc!', 'success')
        
    except Exception as e:
        flash(f'Wystąpił błąd podczas aktywacji premium: {str(e)}', 'error')
    
    return render_template('premium_success.html', session_id=session_id)

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/compare-cv-versions')
def compare_cv_versions():
    original_cv = session.get('original_cv_text', 'Brak oryginalnego CV')
    optimized_cv = session.get('last_optimized_cv', 'Brak zoptymalizowanego CV')
    
    return jsonify({
        'success': True,
        'original': original_cv,
        'optimized': optimized_cv,
        'has_both_versions': bool(session.get('original_cv_text') and session.get('last_optimized_cv'))
    })

@app.route('/upload-cv', methods=['POST'])
@login_required
def upload_cv():
    if 'cv_file' not in request.files:
        return jsonify({'success': False, 'message': 'Nie wybrano pliku'}), 400

    file = request.files['cv_file']
    cv_text = request.form.get('cv_text', '')
    
    if file.filename == '':
        if not cv_text.strip():
            return jsonify({'success': False, 'message': 'Nie wybrano pliku ani nie wprowadzono tekstu CV'}), 400
    
    try:
        original_filename = file.filename if file and file.filename else 'wklejone_cv.txt'
        
        if file and file.filename and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save the file
            file.save(file_path)
            
            try:
                # Extract text from PDF
                cv_text = extract_text_from_pdf(file_path)
                # Remove the file after extraction
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({
                    'success': False,
                    'message': f"Błąd podczas przetwarzania PDF: {str(e)}"
                }), 500
                
        elif file and file.filename != '':
            return jsonify({
                'success': False,
                'message': 'Nieprawidłowy format pliku. Obsługiwane formaty: PDF'
            }), 400
        
        if not cv_text.strip():
            return jsonify({'success': False, 'message': 'CV jest puste lub nie udało się wyodrębnić tekstu'}), 400
        
        # Zapisz CV w bazie danych
        cv_upload = CVUpload(
            user_id=current_user.id,
            filename=original_filename,
            original_text=cv_text,
            job_title=request.form.get('job_title', ''),
            job_description=request.form.get('job_description', '')
        )
        db.session.add(cv_upload)
        db.session.commit()
        
        # Store CV data in session for processing
        session['cv_text'] = cv_text
        session['original_cv_text'] = cv_text  # Store original for comparison
        session['original_filename'] = original_filename
        session['job_title'] = request.form.get('job_title', '')
        session['job_description'] = request.form.get('job_description', '')
        session['cv_upload_id'] = cv_upload.id

        return jsonify({
            'success': True,
            'cv_text': cv_text,
            'message': 'CV zostało pomyślnie przesłane i zapisane.'
        })

    except Exception as e:
        logger.error(f"Error in upload_cv: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd podczas przesyłania pliku: {str(e)}'
        }), 500

@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        # Cena za generowanie CV: 9.99 PLN (999 groszy)
        amount = 999  # w groszach
        
        # Tworzenie Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='pln',
            metadata={
                'service': 'cv_optimization'
            }
        )
        
        return jsonify({
            'success': True,
            'client_secret': intent.client_secret,
            'amount': amount
        })
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Błąd podczas tworzenia płatności: {str(e)}"
        }), 500

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.get_json()
        payment_intent_id = data.get('payment_intent_id')
        
        if not payment_intent_id:
            return jsonify({
                'success': False,
                'message': 'Brak ID płatności'
            }), 400
        
        # Sprawdzenie statusu płatności
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Płatność zakończona sukcesem - zapisz w sesji
            session['payment_verified'] = True
            session['payment_intent_id'] = payment_intent_id
            
            return jsonify({
                'success': True,
                'message': 'Płatność zakończona sukcesem! Możesz teraz wygenerować CV.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Płatność nie została zakończona'
            }), 400
            
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Błąd podczas weryfikacji płatności: {str(e)}"
        }), 500

@app.route('/create-cv-payment', methods=['POST'])
@login_required
def create_cv_payment():
    """Create payment intent for CV generator"""
    try:
        cv_data = request.get_json()
        
        # Store CV data in session for later use
        session['cv_data'] = cv_data
        
        # Create payment intent for CV generation (9.99 PLN)
        intent = stripe.PaymentIntent.create(
            amount=999,  # 9.99 PLN in grosze
            currency='pln',
            metadata={
                'service': 'cv_generator',
                'user_id': current_user.id
            }
        )
        
        return jsonify({
            'success': True,
            'client_secret': intent.client_secret,
            'checkout_url': f'/checkout?client_secret={intent.client_secret}&service=cv_generator'
        })
        
    except Exception as e:
        logger.error(f"Error creating CV payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Błąd podczas tworzenia płatności: {str(e)}"
        }), 500

@app.route('/generate-cv-pdf', methods=['POST'])
@login_required
def generate_cv_pdf():
    """Generate PDF from CV data after payment verification"""
    try:
        data = request.get_json()
        payment_intent_id = data.get('payment_intent_id')
        
        if not payment_intent_id:
            return jsonify({
                'success': False,
                'message': 'Brak ID płatności'
            }), 400
        
        # Verify payment
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status != 'succeeded':
            return jsonify({
                'success': False,
                'message': 'Płatność nie została zakończona'
            }), 400
        
        # Get CV data from session
        cv_data = session.get('cv_data')
        if not cv_data:
            return jsonify({
                'success': False,
                'message': 'Brak danych CV do wygenerowania'
            }), 400
        
        # Generate PDF
        pdf_buffer = generate_cv_pdf_file(cv_data)
        
        # Encode as base64 for frontend
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'pdf_data': pdf_base64,
            'filename': f"CV_{cv_data.get('firstName', 'CV')}_{cv_data.get('lastName', '')}.pdf"
        })
        
    except Exception as e:
        logger.error(f"Error generating CV PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Błąd podczas generowania PDF: {str(e)}"
        }), 500

def generate_cv_pdf_file(cv_data):
    """Generate PDF file from CV data"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=20
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12
    )
    
    # Header
    name = f"{cv_data.get('firstName', '')} {cv_data.get('lastName', '')}".strip()
    story.append(Paragraph(name, title_style))
    
    job_title = cv_data.get('jobTitle', '')
    if job_title:
        story.append(Paragraph(job_title, styles['Heading3']))
    
    # Contact info
    contact_info = []
    if cv_data.get('email'):
        contact_info.append(cv_data['email'])
    if cv_data.get('phone'):
        contact_info.append(cv_data['phone'])
    if cv_data.get('city'):
        contact_info.append(cv_data['city'])
    if cv_data.get('linkedin'):
        contact_info.append(cv_data['linkedin'])
    
    if contact_info:
        story.append(Paragraph(' | '.join(contact_info), normal_style))
    
    story.append(Spacer(1, 20))
    
    # Summary
    if cv_data.get('summary'):
        story.append(Paragraph("O mnie", subtitle_style))
        story.append(Paragraph(cv_data['summary'], normal_style))
        story.append(Spacer(1, 15))
    
    # Experience
    experiences = cv_data.get('experiences', [])
    if experiences and any(exp.get('title') or exp.get('company') for exp in experiences):
        story.append(Paragraph("Doświadczenie zawodowe", subtitle_style))
        for exp in experiences:
            if exp.get('title') or exp.get('company'):
                # Title and company
                exp_header = f"<b>{exp.get('title', 'Stanowisko')}</b> - {exp.get('company', 'Firma')}"
                story.append(Paragraph(exp_header, normal_style))
                
                # Dates
                start_date = exp.get('startDate', '')
                end_date = exp.get('endDate', 'obecnie')
                if start_date:
                    date_range = f"{start_date} - {end_date}"
                    story.append(Paragraph(date_range, normal_style))
                
                # Description
                if exp.get('description'):
                    story.append(Paragraph(exp['description'], normal_style))
                
                story.append(Spacer(1, 10))
    
    # Education
    education = cv_data.get('education', [])
    if education and any(edu.get('degree') or edu.get('school') for edu in education):
        story.append(Paragraph("Wykształcenie", subtitle_style))
        for edu in education:
            if edu.get('degree') or edu.get('school'):
                # Degree and school
                edu_header = f"<b>{edu.get('degree', 'Kierunek')}</b> - {edu.get('school', 'Uczelnia')}"
                story.append(Paragraph(edu_header, normal_style))
                
                # Years
                start_year = edu.get('startYear', '')
                end_year = edu.get('endYear', '')
                if start_year or end_year:
                    year_range = f"{start_year} - {end_year}"
                    story.append(Paragraph(year_range, normal_style))
                
                story.append(Spacer(1, 10))
    
    # Skills
    skills = cv_data.get('skills', '')
    if skills:
        story.append(Paragraph("Umiejętności", subtitle_style))
        skills_list = [skill.strip() for skill in skills.split(',') if skill.strip()]
        skills_text = ' • '.join(skills_list)
        story.append(Paragraph(skills_text, normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route('/process-cv', methods=['POST'])
@login_required
def process_cv():
    # PRODUCTION MODE - Payment required except for developer account
    # Sprawdzenie czy to konto developer (darmowy dostęp)
    if current_user.username == 'developer':
        # Developer account - free access
        pass
    elif not session.get('payment_verified'):
        return jsonify({
            'success': False,
            'message': 'Aby wygenerować CV, musisz najpierw dokonać płatności 9,99 PLN.',
            'payment_required': True
        }), 402  # Payment Required
    
    data = request.json
    cv_text = data.get('cv_text') or session.get('cv_text')
    job_url = data.get('job_url', '')
    selected_option = data.get('selected_option', '')
    roles = data.get('roles', [])
    language = data.get('language', 'pl')  # Default to Polish

    if not cv_text:
        return jsonify({
            'success': False,
            'message': 'No CV text found. Please upload a CV first.'
        }), 400

    # Process Job URL if provided
    extracted_job_description = ''
    if job_url:
        try:
            extracted_job_description = analyze_job_url(job_url)
        except Exception as e:
            logger.error(f"Error extracting job description from URL: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error extracting job description from URL: {str(e)}"
            }), 500

    try:
        job_description = data.get('job_description', extracted_job_description)
        result = None

        options_handlers = {
            'optimize': optimize_cv,
            'feedback': generate_recruiter_feedback,
            'cover_letter': generate_cover_letter,
            'ats_check': ats_optimization_check,
            'interview_questions': generate_interview_questions,
            'cv_score': analyze_cv_score,
            'keyword_analysis': analyze_keywords_match,
            'grammar_check': check_grammar_and_style,
            'position_optimization': optimize_for_position,
            'interview_tips': generate_interview_tips
        }

        if selected_option not in options_handlers:
            return jsonify({
                'success': False,
                'message': 'Invalid option selected.'
            }), 400

        # Sprawdź status płatności i dostępu
        payment_verified = session.get('payment_verified', False)  # 9,99 PLN - jednorazowe CV
        is_developer = current_user.username == 'developer'
        is_premium_active = current_user.is_premium_active()  # 29,99 PLN - Premium
        
        # Definicja funkcji według poziomów dostępu - zgodnie ze screenem
        basic_paid_functions = ['optimize', 'ats_optimization_check', 'grammar_check']  # Za 9,99 PLN - 3 funkcje podstawowe
        premium_functions = ['recruiter_feedback', 'cover_letter', 'cv_score', 'interview_tips', 'keyword_analysis', 'position_optimization']  # Premium 29,99 PLN/miesiąc - wszystkie funkcje ze screena
        cv_builder_functions = ['cv_builder']  # STWÓRZ CV SAMEMU - oddzielna płatna usługa
        free_functions = []  # Tylko podgląd ze znakiem wodnym dla bezpłatnych
        
        logger.info(f"Processing CV with language: {language}, option: {selected_option}")
        
        # Sprawdź dostęp do funkcji według poziomów płatności
        if selected_option in premium_functions:
            # Funkcje tylko dla Premium (29,99 PLN/miesiąc)
            if not is_developer and not is_premium_active:
                return jsonify({
                    'success': False,
                    'message': 'Ta funkcja jest dostępna tylko dla użytkowników Premium. Wykup subskrypcję za 29,99 PLN/miesiąc.',
                    'premium_required': True
                }), 403
                
        elif selected_option in basic_paid_functions:
            # Funkcje za 9,99 PLN lub Premium
            if not is_developer and not payment_verified and not is_premium_active:
                return jsonify({
                    'success': False,
                    'message': 'Ta funkcja wymaga płatności. Zapłać 9,99 PLN za jednorazowe CV lub 29,99 PLN za Premium.',
                    'payment_required': True
                }), 403
                
        elif selected_option in cv_builder_functions:
            # STWÓRZ CV SAMEMU - oddzielna płatna usługa
            cv_builder_paid = session.get('cv_builder_paid', False)
            if not is_developer and not cv_builder_paid:
                return jsonify({
                    'success': False,
                    'message': 'Funkcja STWÓRZ CV SAMEMU wymaga oddzielnej płatności.',
                    'cv_builder_payment_required': True
                }), 403

        # Obsługa funkcji według poziomów dostępu
        if selected_option == 'optimize':
            # Funkcja za 9,99 PLN lub Premium
            if not is_developer and not payment_verified and not is_premium_active:
                result = optimize_cv(cv_text, job_description, language, is_premium=False, payment_verified=False)
                result = add_watermark_to_cv(result)
            else:
                # Pełne CV dla płacących lub Premium
                result = optimize_cv(cv_text, job_description, language, is_premium=is_premium_active, payment_verified=True)
                
        elif selected_option == 'ats_optimization_check':
            # Funkcja za 9,99 PLN lub Premium
            result = options_handlers[selected_option](cv_text, job_description, language)
            
        elif selected_option == 'position_optimization':
            # Funkcja tylko Premium
            job_title = data.get('job_title', 'Specjalista')
            result = optimize_for_position(cv_text, job_title, job_description, language)
            
        elif selected_option in ['cover_letter', 'interview_tips', 'recruiter_feedback']:
            # Funkcje tylko Premium
            if selected_option == 'cover_letter':
                result = options_handlers[selected_option](cv_text, job_description, language)
            else:
                result = options_handlers[selected_option](cv_text, job_description, language)
                
        else:
            # Pozostałe funkcje
            result = options_handlers[selected_option](cv_text, job_description, language)

        # Store optimized CV for comparison (only for optimization options)
        if selected_option in ['optimize', 'position_optimization']:
            session['last_optimized_cv'] = result

        # Zapisz wynik analizy w bazie danych
        cv_upload_id = session.get('cv_upload_id')
        if cv_upload_id:
            try:
                analysis_result = AnalysisResult(
                    cv_upload_id=cv_upload_id,
                    analysis_type=selected_option,
                    result_data=json.dumps({
                        'result': result,
                        'job_description': extracted_job_description if extracted_job_description else job_description,
                        'job_url': job_url,
                        'timestamp': datetime.utcnow().isoformat()
                    }, ensure_ascii=False)
                )
                db.session.add(analysis_result)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving analysis result: {str(e)}")
                # Nie blokujemy odpowiedzi, tylko logujemy błąd

        return jsonify({
            'success': True,
            'result': result,
            'job_description': extracted_job_description if extracted_job_description else None
        })

    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error processing request: {str(e)}"
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create developer account for management
        dev_user = User.query.filter_by(username='developer').first()
        if not dev_user:
            dev_user = User(
                username='developer',
                email='dev@cvoptimizer.pro',
                first_name='Developer',
                last_name='Admin'
            )
            dev_user.set_password('DevAdmin2024!')
            db.session.add(dev_user)
            db.session.commit()
            print("✅ Developer account created successfully!")
            print("🔑 Username: developer")
            print("🔑 Password: DevAdmin2024!")
        else:
            print("✅ Developer account already exists")
            
    app.run(host='0.0.0.0', port=5000, debug=True)
