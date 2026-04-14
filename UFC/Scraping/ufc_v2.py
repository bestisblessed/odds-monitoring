"""UFC odds scraper v2 - uses fightodds.io GraphQL API directly instead of Selenium.
Produces the same CSV format as ufc.py for compatibility with the monitoring script.
"""
import os
import requests
import pandas as pd
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))

print("UFC cron script started (v2 - API)")

API_URL = "https://api.fightodds.io/gql"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://fightodds.io/",
    "Origin": "https://fightodds.io",
}

TARGET_PROMOTION_KEYWORDS = ("ufc", "pfl", "lfa", "one", "oktagon", "cwfc", "cage-warriors", "brave", "ksw")

MONTH_NAMES = {
    1: "JANUARY", 2: "FEBRUARY", 3: "MARCH", 4: "APRIL",
    5: "MAY", 6: "JUNE", 7: "JULY", 8: "AUGUST",
    9: "SEPTEMBER", 10: "OCTOBER", 11: "NOVEMBER", 12: "DECEMBER",
}


def gql_query(query, variables=None):
    """Execute a GraphQL query and return the data."""
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "errors" in result:
        print(f"GraphQL errors: {result['errors']}")
    return result.get("data")


def fetch_upcoming_events():
    """Fetch all upcoming events with their PKs and promotion info."""
    query = """
    query {
      upcomingEvents: allEvents(upcoming: true, orderBy: "date", isCancelled: false) {
        edges {
          node {
            pk
            name
            slug
            date
            straightOfferCount
            promotion { shortName }
          }
        }
      }
    }
    """
    data = gql_query(query)
    if not data:
        return []
    return [edge["node"] for edge in data["upcomingEvents"]["edges"]]


def fetch_event_odds(pk):
    """Fetch moneyline odds for a specific event by PK."""
    query = """
    query ($pk: Int) {
      eventOfferTable(pk: $pk, isCancelled: false) {
        name
        pk
        fightOffers {
          edges {
            node {
              fighter1 { firstName lastName }
              fighter2 { firstName lastName }
              isCancelled
              straightOffers {
                edges {
                  node {
                    sportsbook { shortName slug }
                    outcome1 { odds }
                    outcome2 { odds }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    data = gql_query(query, {"pk": pk})
    if not data or not data.get("eventOfferTable"):
        return None
    return data["eventOfferTable"]


def format_event_name(event_name, event_date, fight_count):
    """Format event name to match the Selenium scraper's output.

    The original scraper captures link text which includes 'EVENT NAME MONTH DAY\\nFIGHT_COUNT'.
    The monitoring script extracts 'MONTH DAY NUMBER' from this for date parsing.
    """
    try:
        dt = datetime.strptime(event_date, "%Y-%m-%d")
        month_name = MONTH_NAMES[dt.month]
        day = dt.day
        return f"{event_name} {month_name} {day}\n{fight_count}"
    except (ValueError, KeyError):
        return event_name


def is_target_event(event):
    """Check if an event belongs to a target promotion."""
    promo = event.get("promotion", {}).get("shortName", "").lower()
    name_lower = event.get("name", "").lower()
    for keyword in TARGET_PROMOTION_KEYWORDS:
        if keyword in promo or keyword in name_lower:
            return True
    return False


def scrape_fightodds_v2():
    """Scrape all target events via the GraphQL API and return a DataFrame."""
    events = fetch_upcoming_events()
    target_events = [e for e in events if is_target_event(e) and e["straightOfferCount"] > 0]

    if not target_events:
        print("No target events with odds found.")
        return pd.DataFrame()

    all_rows = []
    all_sportsbooks = set()

    for event in target_events:
        event_name = event["name"]
        event_slug = event.get("slug", "")
        event_url = f"https://fightodds.io/odds/{event_slug}" if event_slug else ""
        print(event_name)

        event_data = fetch_event_odds(event["pk"])
        if not event_data:
            continue

        formatted_name = format_event_name(
            event_name, event["date"], event["straightOfferCount"]
        )

        for fight_edge in event_data["fightOffers"]["edges"]:
            fight = fight_edge["node"]
            if fight["isCancelled"]:
                continue

            f1 = fight["fighter1"]
            f2 = fight["fighter2"]
            fighter1_name = f"{f1['firstName']} {f1['lastName']}".strip()
            fighter2_name = f"{f2['firstName']} {f2['lastName']}".strip()

            fighter1_odds = {}
            fighter2_odds = {}
            for offer_edge in fight["straightOffers"]["edges"]:
                offer = offer_edge["node"]
                slug = offer["sportsbook"]["slug"]
                all_sportsbooks.add(slug)
                o1 = offer["outcome1"]["odds"] if offer["outcome1"] else None
                o2 = offer["outcome2"]["odds"] if offer["outcome2"] else None
                if o1 is not None:
                    fighter1_odds[slug] = str(o1)
                if o2 is not None:
                    fighter2_odds[slug] = str(o2)

            all_rows.append({
                "Event": formatted_name,
                "Event_URL": event_url,
                "Fighters": fighter1_name,
                **fighter1_odds,
            })
            all_rows.append({
                "Event": formatted_name,
                "Event_URL": event_url,
                "Fighters": fighter2_name,
                **fighter2_odds,
            })

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    for sb in all_sportsbooks:
        if sb not in df.columns:
            df[sb] = ""
    df = df.fillna("")

    first_cols = ["Event", "Event_URL", "Fighters"]
    other_cols = [col for col in df.columns if col not in first_cols]
    df = df[first_cols + other_cols]

    return df


# Main execution
try:
    fightodds_data = scrape_fightodds_v2()
    if not fightodds_data.empty:
        fightodds_file = os.path.join(
            script_dir, "data",
            f"ufc_odds_fightoddsio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        )
        os.makedirs(os.path.dirname(fightodds_file), exist_ok=True)
        fightodds_data.to_csv(fightodds_file, index=False)
        print("FightOdds data scraped and saved.")
    else:
        print("FightOdds scrape returned no data.")
except Exception as e:
    print(f"FightOdds scrape failed: {e}")
    import traceback
    traceback.print_exc()

print("UFC cron script finished (v2 - API)")
