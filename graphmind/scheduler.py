from __future__ import annotations

import os
import time

import schedule
from dotenv import load_dotenv
from rich.console import Console

from .spec.refresher import refresh

load_dotenv()
console = Console()


def job():
    refresh(os.getenv("SPEC_REPO_PATH", "./msgraph-metadata"))


def main():
    freq = os.getenv("SPEC_REFRESH_SCHEDULE", "daily")
    if freq == "daily":
        schedule.every().day.at("02:00").do(job)
        console.print("[green]Scheduler: daily at 02:00[/green]")
    elif freq == "weekly":
        schedule.every().sunday.at("02:00").do(job)
        console.print("[green]Weekly Sunday 02:00[/green]")
    else:
        schedule.every(int(freq)).hours.do(job)
        console.print(f"[green]Scheduler: every {freq} hours[/green]")
    job()
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
