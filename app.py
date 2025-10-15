from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_session import Session
import pandas as pd
import io
import requests
import os

app = Flask(__name__)
app.secret_key = 'shadow_path_secret_key_2024'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Supabase connection
base_url = "https://xtowrjjmindefwzeulzd.supabase.co"
service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0b3dyamptaW5kZWZ3emV1bHpkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTg3NzY1OSwiZXhwIjoyMDY3NDUzNjU5fQ.3EyUZ4yhefV1yEDDDZuic_SslMFOJyBCo5aFj9bW0EE"

headers = {'Authorization': f'Bearer {service_role_key}', 'apikey': service_role_key}

def generate_active_matches():
    try:
        matches_url = f"{base_url}/rest/v1/school_company_matches?select=school_id,company_id,match_percentage,created_at"
        matches_response = requests.get(matches_url, headers=headers)
        matches = matches_response.json()
        profiles_url = f"{base_url}/rest/v1/profiles?select=id,email"
        profiles = requests.get(profiles_url, headers=headers).json()
        schools_url = f"{base_url}/rest/v1/schools?select=id,name,contact_person,contact_phone,province,country,contact_email,address_line1,city,num_girls,initiative_day"
        schools = requests.get(schools_url, headers=headers).json()
        companies_url = f"{base_url}/rest/v1/companies?select=id,name,capacity,contact_person,contact_email,phone,location"
        companies = requests.get(companies_url, headers=headers).json()

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
        return active_matches
    except Exception as e:
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
            active_matches = pd.read_json(io.StringIO(session['active_matches']))

    school_filter = request.args.get('school', '')
    if school_filter:
        active_matches = active_matches[active_matches['schoolName'].str.contains(school_filter, case=False)]
    page = int(request.args.get('page', 1))
    per_page = 10
    total = len(active_matches)
    start = (page - 1) * per_page
    end = start + per_page
    data = active_matches.iloc[start:end].to_dict('records')
    has_next = end < total
    has_prev = page > 1
    return render_template('home.html', data=data, page=page, has_next=has_next, has_prev=has_prev, school_filter=school_filter)

@app.route('/export')
def export():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    active_matches = pd.read_json(io.StringIO(session['active_matches']))
    output = io.StringIO()
    active_matches.to_csv(output, index=False)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='active_matches.csv')

@app.route('/participants/<school_id>')
def participants(school_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # Get email from profiles using school_id (which is profile.id)
    profile_url = f"{base_url}/rest/v1/profiles?select=email&id=eq.{school_id}"
    profile_response = requests.get(profile_url, headers=headers)
    profile_data = profile_response.json()
    if profile_data:
        email = profile_data[0]['email']
        # Get school record using email
        school_url = f"{base_url}/rest/v1/schools?select=id,name,address_line1,city,contact_person,contact_phone,contact_email&contact_email=eq.{email}"
        school_response = requests.get(school_url, headers=headers)
        school_data = school_response.json()
        if school_data:
            school_name = school_data[0]['name']
            school_id_real = school_data[0]['id']
            # Get learners using real school_id
            learners_url = f"{base_url}/rest/v1/learners?select=name,surname,grade,subjects,indemnity_file_path&school_id=eq.{school_id_real}"
            learners_response = requests.get(learners_url, headers=headers)
            learners = learners_response.json()
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
    return render_template('participants.html', data=data, school_name=school_name, school_details=school_details)

@app.route('/download/<path:file_path>')
def download(file_path):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    download_url = f"{base_url}/storage/v1/object/indemnity-forms/{file_path}"
    response = requests.get(download_url, headers=headers)
    if response.status_code == 200:
        filename = file_path.split('/')[-1]
        return send_file(io.BytesIO(response.content), mimetype='application/pdf', as_attachment=True, download_name=filename)
    else:
        return "File not found", 404



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)