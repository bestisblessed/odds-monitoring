"""UFC odds scraper v2 - uses fightodds.io GraphQL API directly instead of Selenium.
Produces the same CSV format as ufc.py for compatibility with the monitoring script.
"""
import os
import base64
from pathlib import Path
import re
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

# Exact registered FightOdds profile operation; keep the selection set intact.
FIGHTER_PROFILES_QUERY = """query CappingTableRefetchQuery(
  $eventPk: Int!
) {
  eventOffers: eventOfferTable(pk: $eventPk, allFights: true) {
    ...CappingTable_eventOffers
    id
  }
}

fragment ButtonNotePopover_note on NoteNode {
  note
  ...PopoverNote_note
}

fragment CappingTable_eventOffers on EventOfferTableNode {
  name
  fightOffers {
    edges {
      node {
        fight {
          id
          slug
          isCancelled
          fighter1 {
            id
            pk
            slug
            wikipediaUrl
            instagram
            fightmetricUrl
            tapologyUrl
            sherdogUrl
            firstName
            lastName
            ...FighterFullName_fighter
            ...FighterFlag_fighter
            ...FighterAge_fighter
            ...FighterRecord_fighter
            ...FighterStance_fighter
            ...FighterFightingStyle_fighter
            ...FighterReach_fighter
            ...FighterHeight_fighter
            ...FighterWeight_fighter
            ...FighterCamp_fighter
            ...FighterSapm_fighter
            ...FighterSlpm_fighter
            ...FighterStrAcc_fighter
            ...FighterStrDef_fighter
            ...FighterSubAvg_fighter
            ...FighterTdAcc_fighter
            ...FighterTdAvg_fighter
            ...FighterTdDef_fighter
            ufcDebut
            koLoss
            weightClassChange
            myNotes {
              edges {
                node {
                  ...ButtonNotePopover_note
                  id
                }
              }
            }
            currentCamp {
              name
              id
              myNotes {
                edges {
                  node {
                    ...ButtonNotePopover_note
                    id
                  }
                }
              }
            }
          }
          fighter2 {
            id
            pk
            slug
            wikipediaUrl
            instagram
            fightmetricUrl
            tapologyUrl
            sherdogUrl
            firstName
            lastName
            ...FighterFullName_fighter
            ...FighterFlag_fighter
            ...FighterAge_fighter
            ...FighterRecord_fighter
            ...FighterStance_fighter
            ...FighterFightingStyle_fighter
            ...FighterReach_fighter
            ...FighterHeight_fighter
            ...FighterWeight_fighter
            ...FighterCamp_fighter
            ...FighterSapm_fighter
            ...FighterSlpm_fighter
            ...FighterStrAcc_fighter
            ...FighterStrDef_fighter
            ...FighterSubAvg_fighter
            ...FighterTdAcc_fighter
            ...FighterTdAvg_fighter
            ...FighterTdDef_fighter
            ufcDebut
            koLoss
            weightClassChange
            myNotes {
              edges {
                node {
                  type
                  ...ButtonNotePopover_note
                  id
                }
              }
            }
            currentCamp {
              name
              myNotes {
                edges {
                  node {
                    ...ButtonNotePopover_note
                    id
                  }
                }
              }
              id
            }
          }
          weightClass {
            weightClass
            id
          }
          myNotes {
            edges {
              node {
                type
                ...ButtonNotePopover_note
                id
              }
            }
          }
        }
        bestOdds1
        bestOdds2
        straightOffers {
          edges {
            node {
              sportsbook {
                id
              }
              outcome1 {
                odds
                ...OddsWithArrowButton_outcome
                id
              }
              outcome2 {
                odds
                ...OddsWithArrowButton_outcome
                id
              }
              id
            }
          }
        }
        id
      }
    }
  }
}

fragment FighterAge_fighter on FighterNode {
  birthDate
  age
}

fragment FighterCamp_fighter on FighterNode {
  camps {
    edges {
      node {
        name
        id
      }
    }
  }
}

fragment FighterFightingStyle_fighter on FighterNode {
  fightingStyle
}

fragment FighterFlag_fighter on FighterNode {
  nationality
}

fragment FighterFullName_fighter on FighterNode {
  firstName
  lastName
}

fragment FighterHeight_fighter on FighterNode {
  height
}

fragment FighterReach_fighter on FighterNode {
  reach
}

fragment FighterRecord_fighter on FighterNode {
  koWins
  subWins
  decWins
  dqWins
  koLosses
  subLosses
  decLosses
  dqLosses
  draws
}

fragment FighterSapm_fighter on FighterNode {
  sapm
}

fragment FighterSlpm_fighter on FighterNode {
  slpm
}

fragment FighterStance_fighter on FighterNode {
  stance
}

fragment FighterStrAcc_fighter on FighterNode {
  strAcc
}

fragment FighterStrDef_fighter on FighterNode {
  strDef
}

fragment FighterSubAvg_fighter on FighterNode {
  subAvg
}

fragment FighterTdAcc_fighter on FighterNode {
  tdAcc
}

fragment FighterTdAvg_fighter on FighterNode {
  tdAvg
}

fragment FighterTdDef_fighter on FighterNode {
  tdDef
}

fragment FighterWeight_fighter on FighterNode {
  weight
}

fragment Note_note on NoteNode {
  id
  note
}

fragment OddsWithArrowButton_outcome on OutcomeNode {
  id
  ...OddsWithArrow_outcome
}

fragment OddsWithArrow_outcome on OutcomeNode {
  odds
  oddsPrev
}

fragment PopoverNote_note on NoteNode {
  ...Note_note
}
"""

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
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result.get("data")


def fetch_upcoming_events():
    """Fetch all upcoming events with their PKs and promotion info."""
    # Exact public operations shipped by https://fightodds.io/app.61d526cc.js.
    # The API now rejects arbitrary GraphQL selection sets with "Unknown query".
    query = Path(script_dir, "OddsEventMenuQrQuery.graphql").read_text()
    data = gql_query(query)
    if not data:
        raise RuntimeError("FightOdds returned no event data")
    promotions = {edge["node"]["id"]: edge["node"] for edge in data["promotions"]["edges"]}
    events = []
    for edge in data["upcomingEvents"]["edges"]:
        event = dict(edge["node"])
        event["promotion"] = promotions.get(event["promotion"]["id"], {})
        events.append(event)
    return events


def fetch_event_fighter_profiles(pk):
    """Use the public profile operation; the odds-table operation omits Sherdog IDs.

    Keep the operation unchanged from https://fightodds.io/app.b59da1e7.js:
    FightOdds only accepts its registered selection sets.
    """
    query = FIGHTER_PROFILES_QUERY
    data = gql_query(query, {"eventPk": pk})
    if not data or not data.get("eventOffers"):
        raise RuntimeError(f"FightOdds returned no fighter profiles for event {pk}")
    profiles = {}
    for edge in data["eventOffers"]["fightOffers"]["edges"]:
        fight = edge["node"]["fight"]
        for side in ("fighter1", "fighter2"):
            fighter = fight[side]
            source_id = fighter["id"]
            if "sherdogUrl" not in fighter:
                raise RuntimeError("FightOdds profile response omitted sherdogUrl; refusing an ID-less snapshot")
            profile = {"sherdogUrl": fighter.get("sherdogUrl") or ""}
            if source_id in profiles and profiles[source_id] != profile:
                raise ValueError(f"Conflicting profiles for FightOdds fighter {source_id}")
            profiles[source_id] = profile
    return profiles


def fetch_event_odds(pk):
    """Fetch the website's public odds table, retaining canonical FightNode IDs."""
    query = Path(script_dir, "EventOfferTableRefetchQuery.graphql").read_text()
    data = gql_query(query, {"eventPk": pk, "isCancelled": False})
    if not data or not data.get("eventOfferTable"):
        raise RuntimeError(f"FightOdds returned no odds table for event {pk}")
    table = data["eventOfferTable"]
    profiles = fetch_event_fighter_profiles(pk)
    for edge in table["fightOffers"]["edges"]:
        fight = edge["node"]
        for side in ("fighter1", "fighter2"):
            fighter = fight[side]
            if fighter["id"] not in profiles:
                raise RuntimeError(f"Missing source profile for fighter {fighter['id']}")
            fighter.update(profiles[fighter["id"]])
        node_type, fight_pk = base64.b64decode(fight["id"]).decode().split(":", 1)
        if node_type != "FightOfferTableNode" or not fight_pk.isdigit():
            raise ValueError(f"Unexpected FightOdds fight identity: {node_type}")
        fight["fight"] = {"id": base64.b64encode(f"FightNode:{fight_pk}".encode()).decode()}
    return table


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


def sherdog_id_from_url(value):
    """Recover the stable Sherdog ID when FightOdds only returns a profile URL."""
    match = re.search(r"/fighter/[^/?#]*-(\d+)(?:[/?#]|$)", str(value or ""))
    return match.group(1) if match else ""


def fighter_identity_columns(fighter):
    """Build CSV identity fields while preserving FightOdds' raw display name."""
    source_fighter_id = str(fighter.get("id") or "").strip()
    sherdog_fighter_id = str(fighter.get("sherdogId") or "").strip()
    sherdog_fighter_url = str(fighter.get("sherdogUrl") or "").strip()
    if not sherdog_fighter_id:
        sherdog_fighter_id = sherdog_id_from_url(sherdog_fighter_url)

    if sherdog_fighter_id:
        identity_key = f"sherdog:{sherdog_fighter_id}"
    elif source_fighter_id:
        identity_key = f"fightodds:{source_fighter_id}"
    else:
        identity_key = ""

    return {
        "FightOdds_Fighter_ID": source_fighter_id,
        "Sherdog_Fighter_ID": sherdog_fighter_id,
        "Sherdog_Fighter_URL": sherdog_fighter_url,
        "Fighter_Identity_Key": identity_key,
    }


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
        source_event_id = str(event_data.get("pk") or event["pk"])

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
            fight_id = (fight.get("fight") or {}).get("id")

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
                "FightOdds_Event_ID": source_event_id,
                "FightOdds_Fight_ID": fight_id,
                "Fighters": fighter1_name,
                **fighter_identity_columns(f1),
                **fighter1_odds,
            })
            all_rows.append({
                "Event": formatted_name,
                "Event_URL": event_url,
                "FightOdds_Event_ID": source_event_id,
                "FightOdds_Fight_ID": fight_id,
                "Fighters": fighter2_name,
                **fighter_identity_columns(f2),
                **fighter2_odds,
            })

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    for sb in all_sportsbooks:
        if sb not in df.columns:
            df[sb] = ""
    df = df.fillna("")

    first_cols = [
        "Event",
        "Event_URL",
        "FightOdds_Event_ID",
        "FightOdds_Fight_ID",
        "FightOdds_Fighter_ID",
        "Sherdog_Fighter_ID",
        "Sherdog_Fighter_URL",
        "Fighter_Identity_Key",
        "Fighters",
    ]
    other_cols = [col for col in df.columns if col not in first_cols]
    df = df[first_cols + other_cols]

    return df


if __name__ == "__main__":
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
            raise RuntimeError("FightOdds scrape returned no data; no snapshot saved")
    except Exception as e:
        print(f"FightOdds scrape failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    print("UFC cron script finished (v2 - API)")
