# ============================================================
# JOB HUNTER - ONE FILE VERSION
# ============================================================
# Standard-library only: NO pip install required.
#
# What this program does:
#
#   1. Stores your Computer Science profile
#   2. Searches public RSS job-search results
#   3. Collects job posts
#   4. Removes duplicates
#   5. Matches roles
#   6. Matches locations
#   7. Matches skills
#   8. Checks education-related requirements
#   9. Detects entry-level-friendly language
#  10. Calculates a transparent score
#  11. Saves jobs into SQLite
#  12. Remembers jobs already seen
#  13. Exports matching jobs to CSV
#  14. Displays the best matches
#  15. Provides a local browser dashboard
#  16. Can automatically repeat searches
#
# IMPORTANT:
# This program finds and ranks jobs.
# It DOES NOT automatically apply for jobs.
# You review the job and apply yourself.
# ============================================================

import csv
import hashlib
import html
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# 1. SETTINGS
# ============================================================

DB_FILE = "job_hunter.db"
CSV_FILE = "matched_jobs.csv"


# ============================================================
# 2. YOUR PROFESSIONAL PROFILE
# ============================================================
# This is the information the matching system uses.
#
# We are keeping this based on your Computer Science
# coursework and skills rather than inventing qualifications.
# ============================================================

PROFILE = {

    "name": "Geofrey Nelson",

    "education": [
        "Diploma in Computer Science",
        "Computer Science",
        "TVET",
        "CBET"
    ],

    "locations": [
        "Kenya",
        "Nairobi",
        "Remote",
        "Work From Home",
        "WFH"
    ],

    "roles": [

        "IT Support",
        "ICT Support",
        "Technical Support",
        "Helpdesk",
        "Service Desk",
        "Application Support",
        "Systems Support",

        "Network Support",
        "Network Technician",
        "NOC Support",

        "IT Assistant",
        "ICT Assistant",
        "Desktop Support",
        "Computer Technician",

        "Web Developer",
        "Backend Developer",
        "Full Stack Developer",
        "Python Developer",

        "Database Support",
        "Database Technician"
    ],

    "skills": [

        "Python",
        "JavaScript",
        "HTML",
        "CSS",

        "Node.js",
        "Express.js",

        "SQL",
        "MySQL",
        "PostgreSQL",
        "MongoDB",

        "Git",
        "GitHub",

        "Networking",
        "DNS",

        "Linux",
        "Windows",

        "Troubleshooting",
        "Hardware",

        "Operating Systems",
        "Database Management",

        "Algorithms",
        "Data Structures",

        "Artificial Intelligence",
        "Machine Learning",

        "REST API",
        "Web Development"
    ]
}


# ============================================================
# 3. JOB SEARCH QUERIES
# ============================================================
# The program searches several different job categories.
#
# You can add or remove searches later.
# ============================================================

SEARCH_QUERIES = [

    "IT support jobs Kenya",
    "ICT support jobs Kenya",
    "technical support jobs Kenya",
    "helpdesk jobs Kenya",
    "service desk jobs Kenya",

    "application support jobs Kenya",
    "systems support jobs Kenya",

    "network support jobs Kenya",
    "network technician jobs Kenya",
    "NOC support jobs Kenya",

    "IT assistant jobs Kenya",
    "ICT assistant jobs Kenya",
    "desktop support jobs Kenya",
    "computer technician jobs Kenya",

    "web developer jobs Kenya",
    "backend developer jobs Kenya",
    "full stack developer jobs Kenya",
    "Python developer jobs Kenya",

    "database support jobs Kenya",
    "database technician jobs Kenya",

    "remote IT support jobs",
    "remote technical support jobs",
    "remote Python developer jobs",
    "remote web developer jobs"
]


# ============================================================
# 4. WORDS USED TO IDENTIFY JOB POSTS
# ============================================================

JOB_WORDS = [

    "job",
    "jobs",
    "vacancy",
    "vacancies",
    "career",
    "careers",
    "hiring",
    "recruitment",
    "position",
    "role",
    "developer",
    "technician",
    "support",
    "engineer",
    "assistant",
    "internship"
]


# ============================================================
# 5. WORDS THAT REDUCE NOISE
# ============================================================

EXCLUDE_WORDS = [

    "senior director",
    "chief technology officer",
    "cto",
    "head of department",
    "professor",
    "lecturer"
]


# ============================================================
# 6. CURRENT DATE/TIME
# ============================================================

def now():
    """
    Return the current local date and time.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# 7. TEXT NORMALIZATION
# ============================================================

def normalize(text):
    """
    Convert text to lowercase and remove unnecessary spaces.

    Example:

        " Python   Developer "

    becomes:

        "python developer"
    """

    text = html.unescape(text or "")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().lower()


# ============================================================
# 8. REMOVE HTML FROM DESCRIPTIONS
# ============================================================

def clean_html(text):
    """
    Remove simple HTML/XML tags from job descriptions.
    """

    text = html.unescape(text or "")

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 9. CHECK WHETHER A TERM EXISTS
# ============================================================

def contains_term(text, term):
    """
    Check whether a skill/role/location appears in text.

    We use phrase matching rather than complicated NLP so
    the program stays reliable and dependency-free.
    """

    text_normalized = normalize(text)

    term_normalized = normalize(term)

    if not term_normalized:
        return False

    return term_normalized in text_normalized


# ============================================================
# 10. REMOVE DUPLICATES FROM A LIST
# ============================================================

def unique(items):
    """
    Preserve order while removing duplicate values.
    """

    result = []

    seen = set()

    for item in items:

        key = normalize(item)

        if key and key not in seen:

            seen.add(key)

            result.append(item)

    return result


# ============================================================
# 11. CREATE A UNIQUE ID FOR A JOB
# ============================================================

def job_id(title, link):
    """
    Create a stable SHA-256 identifier from title + URL.

    This allows the database to recognize a job it has already
    seen.
    """

    raw = (
        normalize(title)
        + "|"
        + normalize(link)
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# 12. CREATE / OPEN DATABASE
# ============================================================

def init_database():
    """
    Create the SQLite database if it doesn't exist.

    SQLite is included with Python, so no installation is needed.
    """

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (

            id TEXT PRIMARY KEY,

            title TEXT NOT NULL,

            link TEXT,

            source TEXT,

            published TEXT,

            description TEXT,

            location_match TEXT,

            role_matches TEXT,

            skill_matches TEXT,

            education_match INTEGER,

            experience_match INTEGER,

            score INTEGER,

            status TEXT DEFAULT 'new',

            first_seen TEXT,

            last_seen TEXT
        )
    """)

    conn.commit()

    return conn


# ============================================================
# 13. BUILD GOOGLE NEWS RSS SEARCH URL
# ============================================================

def build_google_news_url(query):
    """
    Build a public RSS search URL.

    Google News provides an RSS search endpoint that can return
    public search results.

    We use it as an aggregation layer rather than pretending
    that every individual job board provides an API.
    """

    params = {

        "q": query,

        "hl": "en",

        "gl": "KE",

        "ceid": "KE:en"
    }

    return (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(params)
    )


# ============================================================
# 14. DOWNLOAD A PUBLIC URL
# ============================================================

def fetch_url(url, timeout=15):
    """
    Download a public RSS resource.

    If the network fails, the exception is handled by the caller.
    """

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "JobHunter/1.0 personal job-search tool"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:

        return response.read()


# ============================================================
# 15. PARSE RSS
# ============================================================

def parse_rss(xml_bytes):
    """
    Convert RSS XML into normal Python dictionaries.
    """

    jobs = []

    try:

        root = ET.fromstring(
            xml_bytes
        )

    except ET.ParseError:

        return jobs


    for item in root.findall(".//item"):

        title = item.findtext(
            "title",
            default=""
        ).strip()

        link = item.findtext(
            "link",
            default=""
        ).strip()

        description = clean_html(
            item.findtext(
                "description",
                default=""
            )
        )

        published = item.findtext(
            "pubDate",
            default=""
        ).strip()


        source_node = item.find(
            "source"
        )


        if (
            source_node is not None
            and source_node.text
        ):

            source = source_node.text.strip()

        else:

            source = "Google News"


        if title or link:

            jobs.append({

                "title": title,

                "link": link,

                "description": description,

                "published": published,

                "source": source
            })


    return jobs


# ============================================================
# 16. COLLECT LIVE JOB POSTS
# ============================================================

def collect_jobs():

    print()
    print("=" * 70)
    print("STEP 1 - COLLECTING JOB POSTS")
    print("=" * 70)

    all_jobs = []

    successful = 0


    for query in SEARCH_QUERIES:

        try:

            url = build_google_news_url(
                query
            )

            data = fetch_url(
                url
            )

            jobs = parse_rss(
                data
            )

            all_jobs.extend(
                jobs
            )

            successful += 1

            print(
                f"[OK] {query:<38} "
                f"{len(jobs)} posts"
            )


        except Exception as error:

            print(
                f"[SKIP] {query:<35} "
                f"{type(error).__name__}"
            )


    # --------------------------------------------------------
    # Remove duplicate feed entries.
    # --------------------------------------------------------

    seen = set()

    cleaned = []


    for job in all_jobs:

        key = (
            normalize(job["link"])
            or normalize(job["title"])
        )


        if (
            key
            and key not in seen
        ):

            seen.add(key)

            cleaned.append(
                job
            )


    print()
    print(
        f"Successful searches: "
        f"{successful}/{len(SEARCH_QUERIES)}"
    )

    print(
        f"Unique posts collected: "
        f"{len(cleaned)}"
    )


    return cleaned


# ============================================================
# 17. DETERMINE WHETHER SOMETHING LOOKS LIKE A JOB
# ============================================================

def looks_like_job(job):

    text = normalize(

        job["title"]
        + " "
        + job["description"]
    )


    has_job_word = any(

        word in text

        for word in JOB_WORDS
    )


    has_exclusion = any(

        word in text

        for word in EXCLUDE_WORDS
    )


    return (
        has_job_word
        and not has_exclusion
    )


# ============================================================
# 18. MATCH TARGET ROLES
# ============================================================

def find_role_matches(text):

    return unique([

        role

        for role in PROFILE["roles"]

        if contains_term(
            text,
            role
        )

    ])


# ============================================================
# 19. MATCH SKILLS
# ============================================================

def find_skill_matches(text):

    return unique([

        skill

        for skill in PROFILE["skills"]

        if contains_term(
            text,
            skill
        )

    ])


# ============================================================
# 20. MATCH LOCATIONS
# ============================================================

def find_location_matches(text):

    return unique([

        location

        for location in PROFILE["locations"]

        if contains_term(
            text,
            location
        )

    ])


# ============================================================
# 21. CHECK EDUCATION
# ============================================================

def education_match(text):

    text_normalized = normalize(
        text
    )


    education_terms = [

        "diploma",

        "computer science",

        "computer studies",

        "information technology",

        "information systems",

        "ict",

        "technical diploma"
    ]


    return any(

        term in text_normalized

        for term in education_terms
    )


# ============================================================
# 22. CHECK FOR ENTRY-LEVEL LANGUAGE
# ============================================================

def experience_match(text):

    text_normalized = normalize(
        text
    )


    entry_terms = [

        "entry level",
        "entry-level",

        "no experience",

        "without experience",

        "fresh graduate",

        "fresh graduates",

        "graduate trainee",

        "trainee",

        "intern",

        "internship",

        "0-1 year",

        "0 to 1 year",

        "1 year experience",

        "one year experience"
    ]


    return any(

        term in text_normalized

        for term in entry_terms
    )


# ============================================================
# 23. CALCULATE JOB SCORE
# ============================================================
#
# Maximum = 100 points
#
# Role       = 35
# Location   = 20
# Skills     = 25
# Education  = 10
# Experience = 10
#
# This is NOT an employment probability.
# It is only a matching score.
# ============================================================

def calculate_score(job):

    text = normalize(

        job["title"]
        + " "
        + job["description"]
    )


    roles = find_role_matches(
        text
    )

    locations = find_location_matches(
        text
    )

    skills = find_skill_matches(
        text
    )

    education = education_match(
        text
    )

    experience = experience_match(
        text
    )


    score = 0


    # --------------------------------------------------------
    # ROLE = 35 POINTS
    # --------------------------------------------------------

    if roles:

        score += 35


    # --------------------------------------------------------
    # LOCATION = 20 POINTS
    # --------------------------------------------------------

    if locations:

        score += 20


    # --------------------------------------------------------
    # SKILLS = UP TO 25 POINTS
    # --------------------------------------------------------

    skill_points = min(

        len(skills) * 5,

        25
    )

    score += skill_points


    # --------------------------------------------------------
    # EDUCATION = 10 POINTS
    # --------------------------------------------------------

    if education:

        score += 10


    # --------------------------------------------------------
    # ENTRY LEVEL = 10 POINTS
    # --------------------------------------------------------

    if experience:

        score += 10


    return {

        "score": score,

        "roles": roles,

        "locations": locations,

        "skills": skills,

        "education": education,

        "experience": experience
    }


# ============================================================
# 24. ANALYZE ALL JOBS
# ============================================================

def analyze_jobs(jobs):

    print()
    print("=" * 70)
    print("STEP 2 - ANALYZING JOBS")
    print("=" * 70)


    results = []


    for job in jobs:

        if not looks_like_job(
            job
        ):

            continue


        match = calculate_score(
            job
        )


        # A job must contain at least one
        # target role to enter our main results.

        if not match["roles"]:

            continue


        result = dict(job)

        result.update(
            match
        )


        results.append(
            result
        )


    # Highest score first.

    results.sort(

        key=lambda x: (

            x["score"],

            len(x["skills"]),

            x["published"]

        ),

        reverse=True
    )


    print(
        f"Relevant role matches: "
        f"{len(results)}"
    )


    return results


# ============================================================
# 25. SAVE JOBS TO DATABASE
# ============================================================

def save_jobs(conn, jobs):

    print()
    print("=" * 70)
    print("STEP 3 - SAVING JOBS")
    print("=" * 70)


    new_count = 0

    updated_count = 0


    for job in jobs:

        jid = job_id(

            job["title"],

            job["link"]
        )


        existing = conn.execute(

            """
            SELECT id
            FROM jobs
            WHERE id = ?
            """,

            (jid,)

        ).fetchone()


        if existing:

            # Job already exists.

            conn.execute(

                """
                UPDATE jobs

                SET title = ?,
                    link = ?,
                    source = ?,
                    published = ?,
                    description = ?,
                    location_match = ?,
                    role_matches = ?,
                    skill_matches = ?,
                    education_match = ?,
                    experience_match = ?,
                    score = ?,
                    last_seen = ?

                WHERE id = ?
                """,

                (

                    job["title"],

                    job["link"],

                    job["source"],

                    job["published"],

                    job["description"],

                    ", ".join(
                        job["locations"]
                    ),

                    ", ".join(
                        job["roles"]
                    ),

                    ", ".join(
                        job["skills"]
                    ),

                    int(
                        job["education"]
                    ),

                    int(
                        job["experience"]
                    ),

                    job["score"],

                    now(),

                    jid
                )
            )


            updated_count += 1


        else:

            # Completely new job.

            conn.execute(

                """
                INSERT INTO jobs (

                    id,
                    title,
                    link,
                    source,
                    published,
                    description,
                    location_match,
                    role_matches,
                    skill_matches,
                    education_match,
                    experience_match,
                    score,
                    status,
                    first_seen,
                    last_seen

                )

                VALUES (

                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?

                )
                """,

                (

                    jid,

                    job["title"],

                    job["link"],

                    job["source"],

                    job["published"],

                    job["description"],

                    ", ".join(
                        job["locations"]
                    ),

                    ", ".join(
                        job["roles"]
                    ),

                    ", ".join(
                        job["skills"]
                    ),

                    int(
                        job["education"]
                    ),

                    int(
                        job["experience"]
                    ),

                    job["score"],

                    "new",

                    now(),

                    now()
                )
            )


            new_count += 1


    conn.commit()


    print(
        f"New jobs: {new_count}"
    )

    print(
        f"Existing jobs updated: "
        f"{updated_count}"
    )


# ============================================================
# 26. EXPORT MATCHES TO CSV
# ============================================================

def export_csv(conn):

    print()
    print("=" * 70)
    print("STEP 4 - EXPORTING CSV")
    print("=" * 70)


    rows = conn.execute(

        """
        SELECT

            title,
            link,
            source,
            published,
            score,
            location_match,
            role_matches,
            skill_matches,
            education_match,
            experience_match,
            status,
            first_seen

        FROM jobs

        WHERE score >= 40

        ORDER BY
            score DESC,
            first_seen DESC
        """
    ).fetchall()


    headers = [

        "title",
        "link",
        "source",
        "published",
        "score",
        "location_matches",
        "role_matches",
        "skill_matches",
        "education_match",
        "entry_level_language",
        "status",
        "first_seen"
    ]


    with open(

        CSV_FILE,

        "w",

        newline="",

        encoding="utf-8-sig"

    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            headers
        )

        writer.writerows(
            rows
        )


    print(
        f"CSV created: {CSV_FILE}"
    )

    print(
        f"Rows exported: {len(rows)}"
    )


# ============================================================
# 27. DISPLAY TOP JOBS
# ============================================================

def print_results(conn, limit=20):

    print()
    print("=" * 70)
    print("STEP 5 - TOP JOB MATCHES")
    print("=" * 70)


    rows = conn.execute(

        """
        SELECT

            title,
            score,
            source,
            location_match,
            role_matches,
            skill_matches,
            link

        FROM jobs

        WHERE score >= 40

        ORDER BY
            score DESC,
            first_seen DESC

        LIMIT ?
        """,

        (limit,)

    ).fetchall()


    if not rows:

        print(
            "No matching jobs are currently stored."
        )

        print(
            "Try another search later."
        )

        return


    for number, row in enumerate(
        rows,
        1
    ):

        (
            title,
            score,
            source,
            locations,
            roles,
            skills,
            link
        ) = row


        print()
        print(
            f"{number}. {title}"
        )

        print(
            f"   Score: {score}/100"
        )

        print(
            f"   Source: {source}"
        )

        print(
            "   Location: "
            f"{locations or 'Not detected'}"
        )

        print(
            "   Role: "
            f"{roles or 'None'}"
        )

        print(
            "   Skills: "
            f"{skills or 'None'}"
        )

        print(
            f"   Link: {link}"
        )


# ============================================================
# 28. DATABASE SUMMARY
# ============================================================

def database_summary(conn):

    print()
    print("=" * 70)
    print("STEP 6 - DATABASE SUMMARY")
    print("=" * 70)


    total = conn.execute(

        """
        SELECT COUNT(*)
        FROM jobs
        """
    ).fetchone()[0]


    strong = conn.execute(

        """
        SELECT COUNT(*)
        FROM jobs
        WHERE score >= 70
        """
    ).fetchone()[0]


    possible = conn.execute(

        """
        SELECT COUNT(*)
        FROM jobs
        WHERE score BETWEEN 40 AND 69
        """
    ).fetchone()[0]


    print(
        f"All stored jobs: {total}"
    )

    print(
        f"Strong matches: {strong}"
    )

    print(
        f"Possible matches: {possible}"
    )

    print(
        f"Database: {DB_FILE}"
    )

    print(
        f"CSV: {CSV_FILE}"
    )


# ============================================================
# 29. RUN ONE COMPLETE SEARCH
# ============================================================

def run_once():

    print()
    print("#" * 70)
    print("#              JOB HUNTER STARTING")
    print("#" * 70)


    conn = init_database()


    jobs = collect_jobs()


    if jobs:

        analyzed = analyze_jobs(
            jobs
        )

        save_jobs(
            conn,
            analyzed
        )

    else:

        print()
        print(
            "No live posts were collected."
        )

        print(
            "The local program is still functioning."
        )

        print(
            "Check your internet connection and try again."
        )


    export_csv(
        conn
    )


    print_results(
        conn
    )


    database_summary(
        conn
    )


    conn.close()


    print()
    print("#" * 70)
    print("#              SEARCH COMPLETE")
    print("#" * 70)


# ============================================================
# 30. LOCAL WEB DASHBOARD
# ============================================================

class DashboardHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        conn = init_database()


        rows = conn.execute(

            """
            SELECT

                title,
                score,
                source,
                location_match,
                role_matches,
                skill_matches,
                link

            FROM jobs

            WHERE score >= 40

            ORDER BY
                score DESC,
                first_seen DESC

            LIMIT 100
            """
        ).fetchall()


        conn.close()


        html_rows = []


        for row in rows:

            (
                title,
                score,
                source,
                locations,
                roles,
                skills,
                link

            ) = row


            safe_title = html.escape(
                title
            )

            safe_source = html.escape(
                source or ""
            )

            safe_locations = html.escape(
                locations or
                "Not detected"
            )

            safe_roles = html.escape(
                roles or "None"
            )

            safe_skills = html.escape(
                skills or "None"
            )

            safe_link = html.escape(
                link or "",
                quote=True
            )


            html_rows.append(

                f"""
                <tr>

                    <td>
                        <a
                            href="{safe_link}"
                            target="_blank"
                        >
                            {safe_title}
                        </a>
                    </td>

                    <td>
                        <strong>
                            {score}
                        </strong>/100
                    </td>

                    <td>
                        {safe_source}
                    </td>

                    <td>
                        {safe_locations}
                    </td>

                    <td>
                        {safe_roles}
                    </td>

                    <td>
                        {safe_skills}
                    </td>

                </tr>
                """
            )


        if html_rows:

            table_content = "".join(
                html_rows
            )

        else:

            table_content = """
                <tr>
                    <td colspan="6">
                        No matches yet.
                    </td>
                </tr>
            """


        page = f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>
Job Hunter
</title>

<style>

body {{

    font-family:
        Arial,
        sans-serif;

    margin: 30px;

    background: #f5f5f5;

    color: #222;
}}

h1 {{

    margin-bottom: 5px;
}}

p {{

    color: #555;
}}

table {{

    width: 100%;

    border-collapse:
        collapse;

    background: white;
}}

th,
td {{

    padding: 10px;

    border:
        1px solid #ddd;

    text-align: left;

    vertical-align: top;
}}

th {{

    background: #eee;
}}

a {{

    color: #0645ad;
}}

</style>

</head>


<body>

<h1>
Job Hunter
</h1>

<p>
Computer Science job matches —
highest scores first.
</p>


<table>

<thead>

<tr>

<th>
Job
</th>

<th>
Score
</th>

<th>
Source
</th>

<th>
Location
</th>

<th>
Role
</th>

<th>
Skills
</th>

</tr>

</thead>


<tbody>

{table_content}

</tbody>

</table>

</body>

</html>

"""


        data = page.encode(
            "utf-8"
        )


        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(data))
        )

        self.end_headers()


        self.wfile.write(
            data
        )


    def log_message(
        self,
        format,
        *args
    ):

        # Keep the terminal clean.
        return


# ============================================================
# 31. START DASHBOARD
# ============================================================

def start_dashboard(
    port=8000
):

    server = HTTPServer(

        (
            "127.0.0.1",
            port
        ),

        DashboardHandler
    )


    print()
    print("=" * 70)
    print("JOB HUNTER DASHBOARD")
    print("=" * 70)

    print()
    print(
        "Open this in your browser:"
    )

    print(
        f"http://127.0.0.1:{port}"
    )

    print()
    print(
        "Press Ctrl+C to stop."
    )


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print(
            "\nDashboard stopped."
        )


    finally:

        server.server_close()


# ============================================================
# 32. AUTOMATIC SCHEDULER
# ============================================================

def schedule(
    interval_hours
):

    seconds = (
        interval_hours
        * 60
        * 60
    )


    print()
    print("=" * 70)
    print("SCHEDULED JOB SEARCH")
    print("=" * 70)

    print(
        f"Searching every "
        f"{interval_hours} hour(s)."
    )

    print(
        "Press Ctrl+C to stop."
    )


    while True:

        try:

            run_once()


            print()

            print(
                f"Next search in "
                f"{interval_hours} hour(s)..."
            )


            time.sleep(
                seconds
            )


        except KeyboardInterrupt:

            print(
                "\nScheduler stopped."
            )

            break


        except Exception as error:

            print()
            print(
                "Unexpected error:"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "The scheduler will try again."
            )


            time.sleep(
                seconds
            )


# ============================================================
# 33. HELP
# ============================================================

def show_help():

    print("""

============================================================
JOB HUNTER COMMANDS
============================================================

Run one complete search:

    python job_hunter.py


Show help:

    python job_hunter.py help


Start local dashboard:

    python job_hunter.py dashboard


Search every 6 hours:

    python job_hunter.py schedule 6


Search every 12 hours:

    python job_hunter.py schedule 12


Search every 24 hours:

    python job_hunter.py schedule 24


============================================================
FILES CREATED AUTOMATICALLY
============================================================

job_hunter.db
    SQLite database containing discovered jobs.

matched_jobs.csv
    Spreadsheet-compatible list of matching jobs.

============================================================
IMPORTANT
============================================================

The program finds and ranks jobs.

It does NOT automatically submit applications.

You review the vacancy and apply yourself.

""")


# ============================================================
# 34. MAIN PROGRAM
# ============================================================

def main():

    # No command = perform one search.

    if len(sys.argv) == 1:

        run_once()

        return


    command = (
        sys.argv[1]
        .lower()
    )


    if command == "help":

        show_help()


    elif command == "dashboard":

        start_dashboard()


    elif command == "schedule":

        if len(sys.argv) < 3:

            print(
                "Example:"
            )

            print(
                "python job_hunter.py schedule 6"
            )

            return


        try:

            hours = float(
                sys.argv[2]
            )


            if hours <= 0:

                raise ValueError


        except ValueError:

            print(
                "The schedule must be "
                "a positive number of hours."
            )

            return


        schedule(
            hours
        )


    else:

        print(
            f"Unknown command: {command}"
        )

        show_help()


# ============================================================
# 35. START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()