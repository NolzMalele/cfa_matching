from flask import Flask, render_template, request, session, redirect, url_for, send_file
import pandas as pd
from supabase import create_client, Client
import io
import requests

app = Flask(__name__)
app.secret_key = 'shadow_path_secret_key_2024'

# Supabase connection
url = "https://xtowrjjmindefwzeulzd.supabase.co"
service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0b3dyamptaW5kZWZ3emV1bHpkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTg3NzY1OSwiZXhwIjoyMDY3NDUzNjU5fQ.3EyUZ4yhefV1yEDDDZuic_SslMFOJyBCo5aFj9bW0EE"

def get_supabase_client():
    return create_client(url, service_role_key)

def generate_active_matches():
    try:
        client = get_supabase_client()
        matches = client.table('school_company_matches').select('school_id', 'company_id', 'match_percentage', 'created_at').execute().data
        profiles = client.table('profiles').select('id', 'email').execute().data
        schools = client.table('schools').select('id', 'name', 'contact_person', 'contact_phone', 'province', 'country', 'contact_email', 'address_line1', 'city', 'num_girls', 'initiative_day').execute().data
        companies = client.table('companies').select('id', 'name', 'capacity', 'contact_person', 'contact_email', 'phone', 'location').execute().data

        matches_df = pd.DataFrame(matches)
        profiles_df = pd.DataFrame(profiles)
        schools_df = pd.DataFrame(schools)
        companies_df = pd.DataFrame(companies)

        # Ensure columns exist even if data is empty
        if matches_df.empty:
            matches_df = pd.DataFrame(columns=['school_id', 'company_id', 'match_percentage', 'created_at'])
        if profiles_df.empty:
            profiles_df = pd.DataFrame(columns=['id', 'email'])
        if schools_df.empty:
            schools_df = pd.DataFrame(columns=['id', 'name', 'contact_person', 'contact_phone', 'province', 'country', 'contact_email', 'address_line1', 'city', 'num_girls', 'initiative_day'])
        if companies_df.empty:
            companies_df = pd.DataFrame(columns=['id', 'name', 'capacity', 'contact_person', 'contact_email', 'phone', 'location'])

        matches_profiles = matches_df.merge(profiles_df, left_on='school_id', right_on='id', suffixes=('', '_profile'))
        matches_schools = matches_profiles.merge(schools_df, left_on='email', right_on='contact_email', suffixes=('', '_school'))
        full_matches = matches_schools.merge(companies_df, left_on='company_id', right_on='id', suffixes=('', '_company'))

        active_matches = full_matches[[
            'id',  # school id
            'name',  # school name
            'contact_person',  # school contact person
            'contact_phone',
            'province',
            'country',
            'name_company',  # company name
            'capacity',
            'num_girls',
            'initiative_day',
            'match_percentage',
            'created_at',
            'contact_email',  # school contact email
            'address_line1',  # school address
            'city',  # school city
            'contact_person_company',  # company contact person
            'contact_email_company',  # company contact email
            'phone',  # company phone
            'location'  # company location
        ]].copy()

        active_matches['schoolLocation'] = active_matches['province'] + ', ' + active_matches['country']
        active_matches = active_matches.drop(columns=['province', 'country'])

        active_matches['dateMatched'] = pd.to_datetime(active_matches['created_at']).dt.strftime('%Y-%m-%d')
        active_matches = active_matches.drop(columns=['created_at'])

        # Reorder columns to match the expected order
        active_matches = active_matches[[
            'id',
            'name',
            'contact_person',
            'contact_phone',
            'schoolLocation',
            'name_company',
            'capacity',
            'num_girls',
            'initiative_day',
            'match_percentage',
            'dateMatched',
            'contact_email',
            'address_line1',
            'city',
            'contact_person_company',
            'contact_email_company',
            'phone',
            'location'
        ]]

        active_matches.columns = [
            'schoolId',
            'schoolName',
            'schoolContact',
            'schoolContactNumber',
            'schoolLocation',
            'company',
            'capacity',
            'participants',
            'initiativeDay',
            'matchPercent',
            'dateMatched',
            'schoolContactEmail',
            'schoolAddress',
            'schoolCity',
            'companyContactPerson',
            'companyContactEmail',
            'companyPhone',
            'companyLocation'
        ]
        print("Fetched active_matches shape:", active_matches.shape)
        return active_matches
    except Exception as e:
        print("Error in generate_active_matches:", e)
        return pd.DataFrame()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin@cfa.org' and password == 'CFA_Admin_2024!':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST' and 'refresh' in request.form:
        active_matches = generate_active_matches()
        session['active_matches'] = active_matches.to_json()
    else:
        if 'active_matches' not in session:
            active_matches = generate_active_matches()
            session['active_matches'] = active_matches.to_json()
        else:
            active_matches = pd.read_json(session['active_matches'])

    page = int(request.args.get('page', 1))
    per_page = 10
    total = len(active_matches)
    start = (page - 1) * per_page
    end = start + per_page
    data = active_matches.iloc[start:end].to_dict('records')
    has_next = end < total
    has_prev = page > 1
    return render_template('home.html', data=data, page=page, has_next=has_next, has_prev=has_prev)

@app.route('/export')
def export():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    active_matches = pd.read_json(session['active_matches'])
    output = io.StringIO()
    active_matches.to_csv(output, index=False)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, attachment_filename='active_matches.csv')

@app.route('/participants/<school_id>')
def participants(school_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    client = get_supabase_client()
    # Get email from profiles using school_id (which is profile.id)
    profile_data = client.table('profiles').select('email').filter('id', 'eq', school_id).execute().data
    if profile_data:
        email = profile_data[0]['email']
        # Get school record using email
        school_data = client.table('schools').select('id', 'name', 'address_line1', 'city', 'contact_person', 'contact_phone', 'contact_email').filter('contact_email', 'eq', email).execute().data
        if school_data:
            school_name = school_data[0]['name']
            school_id_real = school_data[0]['id']
            # Get learners using real school_id
            learners = client.table('learners').select('name', 'surname', 'grade', 'subjects', 'indemnity_file_path').filter('school_id', 'eq', school_id_real).execute().data
        else:
            school_name = 'Unknown School'
            learners = []
    else:
        school_name = 'Unknown School'
        learners = []
    learners_df = pd.DataFrame(learners)
    data = learners_df.to_dict('records')
    if school_data:
        school_details = {
            'address_line1': school_data[0].get('address_line1', ''),
            'city': school_data[0].get('city', ''),
            'contact_person': school_data[0].get('contact_person', ''),
            'contact_phone': school_data[0].get('contact_phone', ''),
            'contact_email': school_data[0].get('contact_email', '')
        }
    else:
        school_details = {}
    return render_template('pa