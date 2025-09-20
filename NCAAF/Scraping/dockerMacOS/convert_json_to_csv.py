import json
import pandas as pd
import os
from datetime import datetime

def format_team_matchup(teams):
    """Format team names into a proper matchup string"""
    if len(teams) == 1:
        return teams[0]
    elif len(teams) == 2:
        return f"{teams[0]} vs {teams[1]}"
    else:
        return " vs ".join(teams)

def extract_odds_from_sportsbook(sportsbook_data):
    """Extract odds information from sportsbook data"""
    if not sportsbook_data:
        return ""
    
    spread = sportsbook_data.get('spread', '')
    odds = sportsbook_data.get('odds', '')
    
    if spread and odds:
        return f"{spread} ({odds})"
    elif spread:
        return spread
    elif odds:
        return odds
    else:
        return ""

def convert_json_to_csv(json_file_path, output_file_path):
    """Convert JSON odds data to CSV format"""
    
    # Read the JSON file
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Prepare data for CSV
    csv_data = []
    
    for game in data:
        # Format team matchup
        matchup = format_team_matchup(game['teams'])
        
        # Create row data
        row = {'Matchup': matchup}
        
        # Add odds for each sportsbook
        odds_data = game.get('odds', {})
        for sportsbook, odds_info in odds_data.items():
            row[sportsbook] = extract_odds_from_sportsbook(odds_info)
        
        csv_data.append(row)
    
    # Convert to DataFrame
    df = pd.DataFrame(csv_data)
    
    # Save to CSV
    df.to_csv(output_file_path, index=False)
    
    print(f"✅ Converted {len(csv_data)} games to CSV: {output_file_path}")
    return df

def main():
    """Main function to process both spreads and totals data"""
    
    # Define file paths
    base_dir = "/Users/td/Code/odds-monitoring/NCAAF/Scraping/dockerMacOS/data"
    
    spreads_file = os.path.join(base_dir, "ncaaf_odds_vsin_spreads_20250920_0734.json")
    totals_file = os.path.join(base_dir, "ncaaf_odds_vsin_totals_20250920_0734.json")
    
    # Output CSV files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    spreads_csv = os.path.join(base_dir, f"ncaaf_spreads_{timestamp}.csv")
    totals_csv = os.path.join(base_dir, f"ncaaf_totals_{timestamp}.csv")
    
    print("🔄 Converting JSON odds data to CSV format...")
    print(f"📁 Base directory: {base_dir}")
    
    # Convert spreads data
    if os.path.exists(spreads_file):
        print(f"\n📊 Processing spreads data: {spreads_file}")
        spreads_df = convert_json_to_csv(spreads_file, spreads_csv)
        print(f"   Columns: {list(spreads_df.columns)}")
        print(f"   Sample data:")
        print(spreads_df.head(3).to_string(index=False))
    else:
        print(f"❌ Spreads file not found: {spreads_file}")
    
    # Convert totals data
    if os.path.exists(totals_file):
        print(f"\n📊 Processing totals data: {totals_file}")
        totals_df = convert_json_to_csv(totals_file, totals_csv)
        print(f"   Columns: {list(totals_df.columns)}")
        print(f"   Sample data:")
        print(totals_df.head(3).to_string(index=False))
    else:
        print(f"❌ Totals file not found: {totals_file}")
    
    print(f"\n✅ Conversion complete!")
    print(f"📄 Output files:")
    if os.path.exists(spreads_csv):
        print(f"   Spreads: {spreads_csv}")
    if os.path.exists(totals_csv):
        print(f"   Totals: {totals_csv}")

if __name__ == "__main__":
    main()
