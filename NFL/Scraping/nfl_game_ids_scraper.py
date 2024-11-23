# import requests
# from bs4 import BeautifulSoup
# url = 'https://app.hardrock.bet/home/competition/nfl/'
# response = requests.get(url)
# if response.status_code == 200:
#     soup = BeautifulSoup(response.content, 'html.parser')
#     game_container = soup.find('div', class_='hr-outright-tab-content-container')
#     if game_container:
#         game_ids = set()
#         participants = game_container.find_all('div', class_='participant participant-vertical')
#         for participant in participants:
#             team_name = participant.get_text(strip=True)
#             print(f"Team: {team_name}")
#         for game_id in game_ids:
#             print(game_id)
#     else:
#         print("No game container found.")
# else:
#     print(f"Failed to retrieve data: {response.status_code}") 