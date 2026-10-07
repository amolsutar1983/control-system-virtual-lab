
# Control Systems Virtual Laboratory — Online Edition

A mobile-friendly, multi-student Control Systems virtual laboratory built with Streamlit and Supabase.

## What students get

- Android/iPhone/laptop browser access
- Interactive gain K
- Live pole map
- Pole table
- Stability classification
- General Routh-Hurwitz table
- Digital workbook
- Online submission with UTC timestamp

## What faculty get

- Password-protected dashboard
- Central class submission table
- Student count and submission count
- CSV export

## Architecture

Student browser -> Streamlit Cloud (Python app) -> Supabase Postgres

## Deploy in about 10–15 minutes

### 1. Create a Supabase project
Create a free project at https://supabase.com/

Open SQL Editor and run `supabase_schema.sql`.

Then copy:
- Project URL
- API key appropriate for your deployment

### 2. Upload this folder to GitHub

Create a repository and upload:
- app.py
- requirements.txt
- supabase_schema.sql
- README.md
- .streamlit/config.toml

### 3. Deploy on Streamlit Community Cloud

Create a Streamlit Community Cloud app from the GitHub repository.
Set the main file to:

`app.py`

### 4. Add Streamlit Secrets

In the deployed app settings, add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_API_KEY"
FACULTY_PASSWORD = "CHANGE_THIS_PASSWORD"
```

### 5. Open the generated HTTPS link on Android

Students do not install Python, Streamlit, NumPy, or anything else.

They simply open the lab URL in Chrome.

## Important production note

The included database policies are intentionally simple for an educational MVP. For an institutional deployment, add proper authentication and row-level security so students can only create/read their permitted records and faculty accounts have elevated access.

## Suggested next upgrades

- Student login with college email / Google
- Faculty login
- Multiple experiments: time response, root locus, Bode, Nyquist, PID tuning, state-space
- Auto-marking and rubric
- Question randomization
- Experiment completion certificates
- LMS integration
- Institution branding
