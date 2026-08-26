"""Registry of the fixed open web job feeds this tool checks.

Unlike saved sources (arbitrary company URLs the user adds), these are the
same handful of free public feeds every run - so they're a fixed list here
rather than something added via the CLI. `seed-feeds` inserts them into the
sources table once; fetch picks them up like any other active source.
"""

from jobsearch.feeds import arbeitnow, himalayas, hn_hiring, jobicy, remoteok, remotive, weworkremotely

FEEDS = [
    {"key": "himalayas", "name": "Himalayas", "url": "https://himalayas.app/jobs/api", "fetch": himalayas.fetch_jobs},
    {
        "key": "arbeitnow",
        "name": "Arbeitnow",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "fetch": arbeitnow.fetch_jobs,
    },
    {"key": "jobicy", "name": "Jobicy", "url": "https://jobicy.com/api/v2/remote-jobs", "fetch": jobicy.fetch_jobs},
    {"key": "remoteok", "name": "RemoteOK", "url": "https://remoteok.com/api", "fetch": remoteok.fetch_jobs},
    {
        "key": "remotive",
        "name": "Remotive",
        "url": "https://remotive.com/api/remote-jobs",
        "fetch": remotive.fetch_jobs,
    },
    {
        "key": "weworkremotely",
        "name": "We Work Remotely",
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "fetch": weworkremotely.fetch_jobs,
    },
    {
        "key": "hn_hiring",
        "name": "HN Who is Hiring",
        "url": "https://news.ycombinator.com/",
        "fetch": hn_hiring.fetch_jobs,
    },
]

FEED_ADAPTERS = {f["key"]: f["fetch"] for f in FEEDS}
