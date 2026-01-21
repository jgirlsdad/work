from fastapi import FastAPI
from pydantic import BaseModel
from croniter import croniter
from datetime import datetime, timedelta

from datetime import datetime, timedelta
from croniter import croniter

CRON_LINES = [
    "30 2 * * * job_daily_0230",
    "0 9 * * 1 job_monday_0900",
    "15 14 10 * * job_monthly_10th_1415",
]

@app.post("/echo-date")
def echo_date(req: DateRequest):
    try:
        target = datetime.fromisoformat(req.date)
    except ValueError:
        return {"status": "invalid-date", "date": req.date}

    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    results = []

    for idx, line in enumerate(CRON_LINES, start=1):
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue

        schedule = " ".join(parts[:5])
        command = parts[5]

        itr = croniter(schedule, start - timedelta(minutes=1))
        runs = []

        next_run = itr.get_next(datetime)
        while next_run < end:
            runs.append(next_run.strftime("%H:%M"))
            next_run = itr.get_next(datetime)

        if runs:
            results.append({
                "line": idx,
                "schedule": schedule,
                "command": command,
                "runs": runs
            })

    return {
        "status": "ok",
        "date": req.date,
        "count": len(results),
        "results": results
    }
