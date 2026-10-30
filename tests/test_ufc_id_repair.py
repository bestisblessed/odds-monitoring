import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from test_supabase_odds_publisher import load_module, FakeSession

ROOT = Path(__file__).resolve().parents[1]

def scraper():
    spec = importlib.util.spec_from_file_location('ufc_v2', ROOT / 'UFC/Scraping/ufc_v2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class IdentityRepairTests(unittest.TestCase):
    def test_profiles_join_by_source_id_not_name_or_position(self):
        m = scraper()
        odds = {'eventOfferTable': {'fightOffers': {'edges': [{'node': {
            'id': 'RmlnaHRPZmZlclRhYmxlTm9kZTox',
            'fighter1': {'id': 'a', 'firstName': 'Alias'},
            'fighter2': {'id': 'b', 'firstName': 'Same Name'},
        }}]}}}
        profiles = {'eventOffers': {'fightOffers': {'edges': [{'node': {'fight': {
            'fighter1': {'id': 'b', 'sherdogUrl': 'https://www.sherdog.com/fighter/B-22'},
            'fighter2': {'id': 'a', 'sherdogUrl': 'https://www.sherdog.com/fighter/A-11'},
        }}}]}}}
        with patch.object(m, 'gql_query', side_effect=[odds, profiles]):
            result = m.fetch_event_odds(1)['fightOffers']['edges'][0]['node']
        self.assertEqual(m.fighter_identity_columns(result['fighter1'])['Sherdog_Fighter_ID'], '11')
        self.assertEqual(m.fighter_identity_columns(result['fighter2'])['Sherdog_Fighter_ID'], '22')

    def test_profile_failure_stops_snapshot(self):
        m = scraper()
        with patch.object(m, 'gql_query', return_value=None):
            with self.assertRaises(RuntimeError):
                m.fetch_event_fighter_profiles(1)

    def test_omitted_identity_field_is_not_treated_as_unresolved(self):
        m = scraper()
        response = {'eventOffers': {'fightOffers': {'edges': [{'node': {'fight': {
            'fighter1': {'id': 'a'}, 'fighter2': {'id': 'b'},
        }}}]}}}
        with patch.object(m, 'gql_query', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'omitted sherdogUrl'):
                m.fetch_event_fighter_profiles(1)

    def rows(self):
        return [dict(source='fightoddsio', market='moneyline', source_event_id='1',
                     event_name='Event', fight_id='fight', source_fighter_id=source_id,
                     fighter='Alias '+source_id, sherdog_fighter_id=None,
                     fighter_identity_key='fightodds:'+source_id, sportsbook='draftkings',
                     odds_american=odds, source_file='ufc_odds_fightoddsio_20261030_1400.csv',
                     scraped_at='2026-10-30T14:00:00+00:00')
                for source_id, odds in [('a', -110), ('b', 100)]]

    def maps(self):
        return [dict(source='fightoddsio', source_fighter_id=sid, sherdog_fighter_id=fid,
                     resolution_method='source_sherdog_id', resolution_status='resolved',
                     first_seen_at='2026-10-29T14:00:00+00:00', last_seen_at='2026-10-29T14:00:00+00:00')
                for sid,fid in [('a',11),('b',22)]]

    def test_saved_ids_reach_odds_and_both_source_fight_sides(self):
        m=load_module(); session=FakeSession(get_payloads=[self.maps(), [], []])
        m.publish_line_rows(m.SupabaseConfig('https://example.test','key'), self.rows(),
                            session=session,dry_run=False,retain_days=0)
        posts={x['url'].split('/')[-1]:x['json'] for x in session.posts}
        self.assertEqual([r['sherdog_fighter_id'] for r in posts['ufc_odds_line_history']], [11,22])
        self.assertEqual([r['fighter_identity_key'] for r in posts['ufc_odds_line_history']], ['sherdog:11','sherdog:22'])
        fight=posts['ufc_source_fights'][0]
        self.assertEqual((fight['fighter_1_sherdog_id'],fight['fighter_2_sherdog_id']), (11,22))
        self.assertEqual(fight['resolution_status'],'resolved')

    def test_conflicting_source_id_aborts_before_writes(self):
        m=load_module(); session=FakeSession(get_payloads=[self.maps()]); rows=self.rows()
        rows[0]['sherdog_fighter_id']=999
        with self.assertRaises(ValueError):
            m.publish_line_rows(m.SupabaseConfig('https://example.test','key'),rows,
                                session=session,dry_run=False,retain_days=0)
        self.assertEqual(session.posts,[])

if __name__=='__main__': unittest.main()
