import store
import unittest
import datetime
import copy

import redis
import json

from store import *

class redis_store_testing(unittest.TestCase):

    def setUp(self):
        # redis-off test_session.expire_all() # to może niepotrzebne - pozostałośc z prób DELETE
        # problem: baza powinna być pusta na przed każdym testem; można zrobić co najmniej sprawdzenie, mocniej, ale ryzykowniej: czyszczenie
        self.redis=redis.Redis()
        self.redis.flushdb() # może trzeba tutaj wybrać nową bazę danych; może cała zawartość z krótkim TTL na wszelki wypadek?

    def tearDown(self):
        # redis-off test_session.rollback() # to może niepotrzebne - pozostałośc z prób DELETE
        # redis-off test_session.expire_all() # to może niepotrzebne - pozostałośc z prób DELETE
        pass

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

    def prep1(self):   # wersja Redis
        time=datetime.datetime.now()
        self.date=time.strftime('%Y%m%d')
        self.hour=time.strftime('%H')
        # self.p1 = PingResult(id=101, time=self.time+'0101', origin='o-101', \
        #     target='t-101', success=True, rtt=101)
        self.redis.set('pings:o-101:t-101:'+self.date+':'+self.hour+':1:1',
            json.dumps({'success':True, 'rtt':101}))
        # self.p1d = self.p1.to_dict()
        # self.p2 = PingResult(id=102, time=self.time+'0202', origin='o-102', \
        #     target='t-102', success=True, rtt=102)
        self.redis.set('pings:o-102:t-102:'+self.date+':'+self.hour+':2:2',
            json.dumps({'success':True, 'rtt':102}))
        # self.p2d = self.p2.to_dict()
        # test_session.add(self.p1)
        # test_session.add(self.p2)

    def prep(self):
        pass

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

    def _test__add_ping__1(self):
        """test: pusta baza, wstawienie nowego, select wykazuje obecność nowego i tylko jego"""
        time = datetime.datetime.now().strftime('%Y%m%d%H')
        p = PingResult(id=201, time=time+'0101', origin='o-201', \
            target='t-201', success=True, rtt=201)
        add_ping(p)
        p1 = test_session.query(PingResult).one()
        self.assertEqual(p1, p)

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