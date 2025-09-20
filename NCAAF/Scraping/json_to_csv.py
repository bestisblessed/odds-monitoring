import json
import pandas as pd
import os
import re
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
    
    # Define file paths - use current directory structure
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # Find the most recent JSON files
    json_files = []
    if os.path.exists(base_dir):
        for filename in os.listdir(base_dir):
            if filename.startswith('ncaaf_odds_vsin_') and filename.endswith('.json'):
                json_files.append(os.path.join(base_dir, filename))
    
    if not json_files:
        print(f"❌ No JSON files found in {base_dir}")
        return
    
    # Sort by modification time to get the most recent
    json_files.sort(key=os.path.getmtime, reverse=True)
    
    print("🔄 Converting JSON odds data to CSV format...")
    print(f"📁 Base directory: {base_dir}")
    
    # Process each JSON file
    for json_file in json_files:
        if 'spreads' in json_file:
            odds_type = 'spreads'
        elif 'totals' in json_file:
            odds_type = 'totals'
        else:
            continue
            
        # Extract timestamp from filename
        filename = os.path.basename(json_file)
        timestamp_match = re.search(r'(\d{8}_\d{4})', filename)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Output CSV file
        csv_file = os.path.join(base_dir, f"ncaaf_{odds_type}_{timestamp}.csv")
        
        print(f"\n📊 Processing {odds_type} data: {json_file}")
        try:
            df = convert_json_to_csv(json_file, csv_file)
            print(f"   Columns: {list(df.columns)}")
            print(f"   Sample data:")
            print(df.head(3).to_string(index=False))
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
    
    print(f"\n✅ Conversion complete!")
    print(f"📄 Output files:")
    for json_file in json_files:
        if 'spreads' in json_file:
            odds_type = 'spreads'
        elif 'totals' in json_file:
            odds_type = 'totals'
        else:
            continue
            
        filename = os.path.basename(json_file)
        timestamp_match = re.search(r'(\d{8}_\d{4})', filename)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            csv_file = os.path.join(base_dir, f"ncaaf_{odds_type}_{timestamp}.csv")
            if os.path.exists(csv_file):
                print(f"   {odds_type.capitalize()}: {csv_file}")

if __name__ == "__main__":
    main()
