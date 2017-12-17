import store
import unittest
import datetime
from datetime import timedelta
import copy

import redis
import json

from store import *

class redis_store_testing(unittest.TestCase):

    def setUp(self):
        # redis-off test_session.expire_all() # to może niepotrzebne - pozostałośc z prób DELETE
        # problem: baza powinna być pusta na przed każdym testem; można zrobić co najmniej sprawdzenie, mocniej, ale ryzykowniej: czyszczenie
        # self.redis=redis.Redis()
        # self.redis=redis.StrictRedis(decode_responses=True)
        self.redis=kv # trochę dziwne: na wspólnym obiekcie działa znacznie szybciej
        self.redis.flushdb() # może trzeba tutaj wybrać nową bazę danych; może cała zawartość z krótkim TTL na wszelki wypadek?

    def tearDown(self):
        # redis-off test_session.rollback() # to może niepotrzebne - pozostałośc z prób DELETE
        # redis-off test_session.expire_all() # to może niepotrzebne - pozostałośc z prób DELETE
        pass
        # self.redis.flushdb() sprzątanie po testach

    def _prep1(self):   # wersja SQLAlchemy
        self.time=datetime.datetime.now().strftime('%Y%m%d%H')
        self.p1 = PingResult(id=101, time=self.time+'0101', origin='o-101', \
            target='t-101', success=True, rtt=101)
        self.p1d = self.p1.to_dict()
        self.p2 = PingResult(id=102, time=self.time+'0202', origin='o-102', \
            target='t-102', success=True, rtt=102)
        self.p2d = self.p2.to_dict()
        test_session.add(self.p1)
        test_session.add(self.p2)

    def prep_time(self):
        self.time = datetime.datetime.now()
        self.date = self.time.strftime('%Y%m%d')
        self.hour = self.time.strftime('%H')

    def prep1(self):   # wersja Redis
        self.prep_time()
        add_ping_redis('o-101', 't-101', self.date, self.hour, '01', '01', True, 101)
        add_ping_redis('o-102', 't-102', self.date, self.hour, '02', '02', True, 102)

    def prep(self):
        pass

    def dump_redis(self):
        for k in self.redis.keys():
            print(k, '-> ', end='')
            if self.redis.type(k)=='string':
                print(self.redis.get(k))
            if self.redis.type(k)=='set':
                print(self.redis.smembers(k))

    def test__get(self):                                                # REDIS
        self.prep_time()
        add_ping_redis('o-101', 't-101', self.date, self.hour, '01', '01', True, 10.1)
        add_ping_redis('o-101', 't-101', self.date, self.hour, '02', '02', True, 20.2)
        time_1h = self.time+timedelta(hours=1)
        date_1h = time_1h.strftime('%Y%m%d')
        hour_1h = time_1h.strftime('%H')
        add_ping_redis('o-101', 't-101', date_1h, hour_1h, '03', '03', True, 30.3)
        time_1d = self.time+timedelta(days=1)
        date_1d = time_1d.strftime('%Y%m%d')
        hour_1d = time_1d.strftime('%H')
        add_ping_redis('o-101', 't-101', date_1d, hour_1d, '04', '04', True, 40.4)
        get_pings_redis('o-101', 't-101')
        # TODO assert - ale jak to ładnie sprawdzić?

    # redis: nie ma sensu wg id - pewnie do usunięcia również w wersji db; albo działa w db, a w redis nie - ale jak wtedy ma reagować?
    def _test__get_pings_id__existing(self):
        """test: przykładowa baza danych, wywołanie z id istniejącym, zwrócony wynik wg id"""
        self.prep1()
        r1 = get_pings_id(101)
        r2 = get_pings_id(102)
        self.assertEqual(r1, self.p1)
        self.assertEqual(r2, self.p2)

    # redis: j.w.
    def _test__get_pings_id__nonexistent(self):
        """test: przykładowa baza danych, wywołanie z id nieistniejących, zwrócony wynik pusty"""
        self.prep1()
        r = get_pings_id(103)
        self.assertIsNone(r)

    # redis: j.w.
    def _test__get_pings__id_existing(self):
        """test: przykładowa baza danych, wywołanie z id istniejącym, zwrócony wynik wg id"""
        self.prep1()
        request.args = {'id': 101}
        r = get_pings()
        self.assertEqual(r, [self.p1])

    # redis: j.w.
    def _test__get_pings__id_nonexistent(self):
        """test: przykładowa baza danych, wywołanie z id nieistniejących, zwrócony wynik pusty"""
        self.prep1()
        request.args = {'id': 103}
        r = get_pings()
        self.assertEqual(r, [])

    # czy w Redis to powinno budować całą strukturę wg hierarchii?
    def _test__get_pings__saute(self):
        """test: przykładowa baza danych, wywołanie bez ograniczenia, zwrócony wynik pełny"""
        self.prep1()
        request.args = {}
        r = get_pings()
        self.assertIn(self.p1, r)
        self.assertIn(self.p2, r)

    def _test__git_pings__start(self):
        """test: sprawdzenie stosowania warunku start"""
        self.prep1()
        request.args = {'start': self.time+'02'}
        r = get_pings()
        self.assertEqual(r, [self.p2])

    def _test__git_pings__end(self):
        """test: sprawdzenie stosowania warunku end"""
        self.prep1()
        request.args = {'end': self.time+'02'}
        r = get_pings()
        self.assertEqual(r, [self.p1])

    def _test__git_pings__time_prefix(self):
        """test: sprawdzenie stosowania warunku time_prefix"""
        self.prep1()
        request.args = {'time_prefix': self.time+'02'}
        r = get_pings()
        self.assertEqual(r, [self.p2])

    def _test__get_pings__origin_existing(self):
        """test: przykładowa baza danych, wywołanie z origin istniejącym, zwrócony wynik wg origin"""
        self.prep1()
        request.args = {'origin': 'o-101'}
        r = get_pings()
        self.assertEqual(r, [self.p1])

    def _test__get_pings__origin_non_existent(self):
        """test: przykładowa baza danych, wywołanie z origin nieistniejącym, zwrócony wynik pusty"""
        self.prep1()
        request.args = {'origin': 'o-bla'}
        r = get_pings()
        self.assertEqual(r, [])

    def _test__get_pings__target_existing(self):
        """test: przykładowa baza danych, wywołanie z target istniejącym, zwrócony wynik wg tagret"""
        self.prep1()
        request.args = {'target': 't-102'}
        r = get_pings()
        self.assertEqual(r, [self.p2])

    def _test__get_pings__tagret_non_existent(self):
        """test: przykładowa baza danych, wywołanie z taget nieistniejącym, zwrócony wynik pusty"""
        self.prep1()
        request.args = {'target': 't-bla'}
        r = get_pings()
        self.assertEqual(r, [])

    def _limit_helper(self, n):
        self.prep1()
        request.args = {'limit': str(n)}
        r = get_pings()
        self.assertEqual(len(r), n)

    def _test__get_pings__limit_0(self):
        """test: limit = 0"""
        self.limit_helper(0)

    def _test__get_pings__limit_1(self):
        """test: limit = 1"""
        self.limit_helper(1)

    def _test__get_pings__limit_2(self):
        """test: limit = 2"""
        self.limit_helper(2)

    def _test__pings_delete__all(self):
        """test: kasowanie bez warunków - wszystkiego"""
        self.prep1()
        request.args = {}
        r, code = pings_delete()
        self.assertEqual(code, 204)
        self.assertEqual(r, 'deleted!')
        self.assertEqual(test_session.query(PingResult).count(), 0)

    def _test__add_ping(self):
        """test: pusta baza, wstawienie nowego, select wykazuje obecność nowego i tylko jego"""
        time = datetime.datetime.now().strftime('%Y%m%d%H')
        p = PingResult(id=201, time=time+'0101', origin='o-201', \
            target='t-201', success=True, rtt=201)
        add_ping(p)
        p1 = test_session.query(PingResult).one()
        self.assertEqual(p1, p)

    def test__add_ping(self):                                       # REDIS
        self.prep_time()
        minute = '01'
        second = '01'
        add_ping_redis('o-201', 't-201', self.date, self.hour, minute, second, True, 201)
        self.assertIn('o-201', self.redis.smembers('list_origins'))
        self.assertIn('t-201', self.redis.smembers('list_targets:o-201'))
        self.assertIn(self.date, self.redis.smembers('list_days:o-201:t-201'))
        self.assertIn(self.hour, self.redis.smembers('list_hours:o-201:t-201:'+self.date))
        self.assertIn(minute, self.redis.smembers('list_minutes:o-201:t-201:'+self.date+':'+self.hour))
        # self.dump_redis()
        self.assertEqual(json.loads(self.redis.get('ping_results:o-201:t-201:'+self.date+':'+self.hour+':'+minute)),
            {'second':second, 'success':True, 'rtt':201})

    def _test__pings_delete__id_existing(self):
        """test: kasowanie wg id istniejącego"""
        """
        # coś źle: co najmniej w PostgreSQL zostaje po teście wiersz w bazie
        self.prep1()
        request.args = {'id': '101'}
        r, code = pings_delete()
        self.assertEqual(code, 204)
        self.assertEqual(r, 'deleted!')
        self.assertEqual(test_session.query(PingResult).count(), 1)
        """
        pass

    def _test__pings_delete__id_nonexistent(self):
        """test: kasowanie wg id nieistniejącego"""
        """ TEST NIE DZIAŁA - WYŁĄCZONY :(
        print('aaa1')
        self.prep1()
        print('aaa2')
        request.args = {'id': '103'}
        print('aaa3')
        print(test_session.new)
        r, code = pings_delete()
        print('bbb')
        self.assertEqual(code, 204)
        self.assertEqual(r, 'deleted!')
        self.assertEqual(test_session.query(PingResult).count(), 2)
        """
        pass

if __name__ == '__main__':
    unittest.main()
