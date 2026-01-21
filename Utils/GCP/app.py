from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
from croniter import croniter
from statistics import mean
from pathlib import Path, PurePosixPath
import shlex
import csv
from io import StringIO
from fastapi.responses import PlainTextResponse


app = FastAPI()

def format_time_ampm(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


class DateRequest(BaseModel):
    date: str  # YYYY-MM-DD

CRON_FILE = Path("cron_file")


def read_cron_lines():
    lines = []
    with CRON_FILE.open() as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append((lineno, line))
    print(lines)
    return lines


def infer_cadence(schedule: str, anchor: datetime, samples: int = 5) -> str:
    itr = croniter(schedule, anchor)
    runs = [itr.get_next(datetime) for _ in range(samples)]

    if len(runs) < 2:
        return "one-off"

    deltas = [(runs[i + 1] - runs[i]).days for i in range(len(runs) - 1)]
    avg = round(mean(deltas))

    if avg == 1:
        return "daily"
    if avg == 7:
        return "weekly"
    if avg == 14:
        return "bi-weekly"
    if 28 <= avg <= 31:
        return "monthly"
    if 60 <= avg <= 62:
        return "bi-monthly"
    if 89 <= avg <= 92:
        return "quarterly"
    if 360 <= avg <= 366:
        return "yearly"
    return "irregular"


def extract_bic_etl_job(command: str):
    # Detect bic_etl.js usage anywhere in the command
    if "bic_etl.js" not in command:
        return None

    tokens = shlex.split(command)

    job = {
        "type": "bic_etl",
        "processor": "bic_etl.js",
        "p": None,
        "scope": "all",  # default
        "t": None
    }

    for i, tok in enumerate(tokens):
        if tok == "-p" and i + 1 < len(tokens):
            job["p"] = tokens[i + 1]
        if tok == "-t" and i + 1 < len(tokens):
            job["t"] = tokens[i + 1]
            job["scope"] = "single"

    # -p is mandatory for bic_etl.js jobs
    if job["p"] is None:
        return None

    return job


def extract_script_job(command: str):
    """
    For non-bic_etl lines: extract the actual script being invoked.
    Preference:
      1) If token contains $bic_etl_home/... extract the relative path after it
      2) Else take the last path-like token with a typical script extension
      3) Else fall back to the last token that looks like a path
    """
    tokens = shlex.split(command)

    # Helper to strip wrappers like "node", "bash", "python", etc.
    # We don't actually need the interpreter; we want the script target.
    script_exts = (".js", ".py", ".sh", ".bash", ".ps1", ".rb", ".pl")

    # 1) Look for $bic_etl_home/<path>
    marker = "$bic_etl_home/"
    for tok in tokens:
        if marker in tok:
            tail = tok.split(marker, 1)[1]
            # Normalize path; keep relative-after-home
            rel = str(PurePosixPath(tail))
            return {"type": "script", "script": rel}

    # 2) Look for a token that ends with a script extension
    for tok in tokens:
        if tok.endswith(script_exts):
            return {"type": "script", "script": PurePosixPath(tok).name}

    # 3) Fallback: last token that looks like a path (contains '/')
    for tok in reversed(tokens):
        if "/" in tok:
            return {"type": "script", "script": PurePosixPath(tok).name}

    return None


@app.post("/run-cron")
def run_cron(req: DateRequest):
    target = datetime.fromisoformat(req.date)

    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    results = []

    for lineno, line in read_cron_lines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            print("SHORT ",line)
            continue

        schedule = " ".join(parts[:5])
        command = parts[5]

        itr = croniter(schedule, start - timedelta(minutes=1))
        runs_today = []

        next_run = itr.get_next(datetime)
        while next_run < end:
            runs_today.append(next_run)
            next_run = itr.get_next(datetime)

        if not runs_today:
            continue

        cadence = infer_cadence(schedule, start)

        job = extract_bic_etl_job(command)
        if job is None:
            job = extract_script_job(command)

        results.append((cadence, job, runs_today))

    # ---- CSV OUTPUT ONLY ----
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["date", "time", "cadence", "script", "p", "dataset"])

    for cadence, job, runs in results:
        for run_dt in runs:
            writer.writerow([
                req.date,
                format_time_ampm(run_dt),
                cadence,
                job.get("script") if job["type"] == "script" else "bic_etl.js",
                job.get("p"),
                job.get("t") if job.get("t") else ("all" if job.get("p") else "")
            ])

    return PlainTextResponse(output.getvalue(), media_type="text/csv")

