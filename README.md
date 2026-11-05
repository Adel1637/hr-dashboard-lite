# HR Dashboard Lite

**Turn an Excel HR export into a secure headcount dashboard — in minutes, on your own server.**

[Website](https://adel1637.github.io/hr-dashboard-lite/) · [Version française](README.fr.md) · [Pro version](#lite-vs-pro)

![Demo: sign in, headcount dashboard, data table and dark theme](docs/demo.gif)

HR Dashboard Lite is a free, self-hosted web app built with **FastAPI, Pandas and Plotly**, with a
framework-free HTML/CSS/JS front end. Drop the employee file you already export from your payroll or
HR software, check the column mapping, and get a headcount dashboard with filters.
No cloud, no internet access required, no data leaves your network.

## Features

- **Excel and CSV import** with automatic header, separator and encoding detection
- **Column-mapping assistant**: recognises French and English headers ("Date d'embauche",
  "Hire date", "CSP", "Department"…) and remembers your mapping for the next import
- **Row-level validation report** with the exact Excel line number of every error
- **Headcount module**: headcount at any date and change over the period, permanent-contract share,
  monthly trend, breakdown by department, site and category
- **Global filters**: reference date, period, site, department, category, contract type, sex
- **Data table** with server-side search, sorting and pagination
- **Security built in**: hashed passwords (scrypt), JWT sessions, login rate limiting,
  strict Content-Security-Policy, no secret in the code
- Light and dark themes, French and English, configurable brand colour and logo, responsive layout

![Column mapping assistant](docs/screenshots/import-en.png)

![Dark theme](docs/screenshots/dashboard-dark-en.png)

## Quick start

You need **Python 3.11 or newer** and Git, or just Docker.

**1. Download and install**

```bash
git clone https://github.com/Adel1637/hr-dashboard-lite.git
cd hr-dashboard-lite
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure** (optional for a first try)

```bash
cp .env.example .env                                  # Windows: copy .env.example .env
```

In `.env`, set `ADMIN_PASSWORD` and, for anything beyond a local test, `JWT_SECRET`
(`python -c "import secrets; print(secrets.token_urlsafe(48))"`). If you leave `ADMIN_PASSWORD`
empty, a random password is generated and printed **once** in the terminal when the app first starts.

**3. Create demo files and start the app**

```bash
python demo_data/generate.py                          # fictional files of 50, 1,000 and 20,000 employees
uvicorn app.main:app --reload
```

**4. Try it**

1. Open <http://localhost:8000> and sign in as `admin`.
2. Go to **Import**, choose `demo_data/personnel_demo_1000.xlsx`, check the column mapping and confirm.
3. Open **Dashboard**: headcount, trend and the breakdowns follow the filters at the top.

With Docker: `docker compose up -d --build`, then open <http://localhost:8000>.

### If something does not work

| Symptom | Fix |
| --- | --- |
| `python: command not found` or a version error | Install Python 3.11+, or use `python3` / `py -3.11`. |
| `uvicorn: command not found` | Activate the virtual environment first (`source .venv/bin/activate`). |
| Port 8000 already in use | Start with `uvicorn app.main:app --port 8001` and open that port. |
| You lost the admin password | Delete `data/users.json`, optionally set `ADMIN_PASSWORD` in `.env`, then restart: the admin account is recreated. |
| The import says a row is rejected | Open the Excel file at the row number shown. The report lists the cause for each row. |
| App refuses to start in production | `APP_ENV=production` needs a `JWT_SECRET` of at least 32 characters. |

### Your own file

One row per employee, current or former. Only two columns are required:

| Field | Required | Example headers recognised |
| --- | :---: | --- |
| Employee ID | yes | Matricule, Employee ID, ID salarié |
| Hire date | yes | Date d'embauche, Hire date, Start date |
| Exit date | | Date de départ, Exit date (empty if still employed) |
| Sex, date of birth, department, site, category, contract type, name, exit reason | | Genre, Gender, Direction, Department, CSP, Grade, Contrat… |

Headcount at any date is computed from hire and exit dates: no need to import one file per month.

## Performance

On a fictional company of 20,000 employees (29,120 rows of history), import and validation take
under a second and the headcount module is computed in about 0.1 s, then served from cache until
the next import.

## Lite vs Pro

The **Pro version** is the complete developer kit, for freelancers and agencies who deliver HR
dashboards to clients, and for in-house IT teams.

| | Lite (free) | Pro |
| --- | :---: | :---: |
| Excel/CSV import, mapping assistant, validation report | ✓ | ✓ |
| Headcount module and global filters | ✓ | ✓ |
| Hires & exits: turnover, exit rate, exit reasons | | ✓ |
| Demographics: age pyramid, tenure, gender balance, 55+ | | ✓ |
| Training: hours, access rate, cost, top courses | | ✓ |
| Data table: column filters, pinned columns, saved views, multi-select | | ✓ |
| CSV and Excel exports | | ✓ |
| Multiple users with roles (admin, HR, viewer) | | ✓ |
| Audit log (logins, imports, exports) | | ✓ |
| Full documentation, module guide, commercial licence, updates and support | | ✓ |

**→ Pro version launching soon. [Follow me on GitHub](https://github.com/Adel1637) to be notified.**

The locked Pro tabs shown in the app can be hidden with `SHOW_PRO_HINTS=false` in `.env`.

## FAQ

**Is it really free?** Yes. It is MIT-licensed: personal and commercial use, modification and delivery
to clients are allowed.

**Does my data leave my server?** No. The app runs on your machine or network, stores imports in its
data folder, bundles its font and needs no internet connection. There is no tracking.

**What does my file need?** An `.xlsx` or `.csv` file with one row per employee, present or departed.
Only an employee ID and a hire date are required; the mapping step matches your headers.

**What happens when a row is wrong?** The import report lists each problem with the Excel row number
and says whether the row was rejected or the value ignored.

**How large can the file be?** 25 MB by default (`MAX_UPLOAD_MB`). 20,000 employees import and
validate in under a second.

**How do I change the colour, logo or language?** `APP_ACCENT`, `APP_LOGO` and `APP_DEFAULT_LANG` in
`.env`, then restart.

**Can I use Lite on a client project?** Yes, the MIT licence allows it. Pro adds the turnover,
demographics and training modules, exports, multiple users and the audit log.

**Where do I report a bug?** [Open an issue](https://github.com/Adel1637/hr-dashboard-lite/issues).
A small sample file that reproduces the problem makes it much faster to fix.

## Project structure

```text
app/
  config.py        all settings, read from .env
  schemas.py       canonical fields and header synonyms used by the mapping assistant
  core/            import, mapping, storage, cache, filters, headcount module
  charts/          reusable Plotly builders
  security/        passwords, JWT, rate limiting
  api/routes/      auth, import, dashboard, data
frontend/          HTML, theme CSS, ES modules
locales/           fr.json, en.json
demo_data/         fictional data generator
tests/             pytest suite
```

## Configuration

Everything lives in `.env` (see `.env.example`): app name, company, accent colour, logo, default
language, admin account, session length, CORS origins, rate limits, upload size, data folder.
In production (`APP_ENV=production`) the app refuses to start without a strong `JWT_SECRET`.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

## License

[MIT](LICENSE) — free for personal and commercial use. The bundled Plus Jakarta Sans font is
licensed under the SIL Open Font License 1.1 (`frontend/fonts/OFL-PlusJakartaSans.txt`).
The Pro version is distributed under a separate commercial licence.
