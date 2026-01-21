from fastapi import FastAPI
from pydantic import BaseModel
from croniter import croniter
from datetime import datetime, timedelta

app = FastAPI()

class DateRequest(BaseModel):
    date: str

@app.post("/echo-date")
def echo_date(req: DateRequest):
    try:
        parsed = datetime.fromisoformat(req.date)
        return {
            "status": "ok",
            "date": req.date,
            "weekday": parsed.strftime("%A")
        }
    except ValueError:
        return {
            "status": "invalid-date",
            "date": req.date
        }


# @app.post("/run-cron")
# def run_cron(req: DateRequest):
#     print("REQ ",req)
#     target = datetime.fromisoformat(req.date)
#     start = target.replace(hour=0, minute=0, second=0)
#     end = start + timedelta(days=1)

#     runs = []

#     with open(CRON_FILE) as f:
#         for line_no, line in enumerate(f, start=1):
#             line = line.strip()
#             if not line or line.startswith("#"):
#                 continue

#             parts = line.split(None, 5)
#             if len(parts) < 6:
#                 continue

#             schedule = " ".join(parts[:5])
#             command = parts[5]

#             itr = croniter(schedule, start - timedelta(minutes=1))
#             next_run = itr.get_next(datetime)

#             while next_run < end:
#                 runs.append({
#                     "time": next_run.strftime("%H:%M"),
#                     "line": line_no,
#                     "command": command
#                 })
#                 next_run = itr.get_next(datetime)

#     return {
#         "date": req.date,
#         "count": len(runs),
#         "runs": sorted(runs, key=lambda x: x["time"])
#     }
