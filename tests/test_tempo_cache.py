"""Tests of the Tempo colour cache. Run: python3 -m unittest discover tests"""
import importlib.util
import unittest
from datetime import date, time
from pathlib import Path

# Loaded by path: importing the package would need Home Assistant.
_spec = importlib.util.spec_from_file_location(
    "tempo_cache",
    Path(__file__).parents[1] / "custom_components" / "tarif_edf" / "tempo_cache.py",
)
tempo_cache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tempo_cache)

AVAILABLE_AT = time(11, 0)
MON, TUE, WED = date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25)


def answer(day, code):
    return {"dateJour": day.isoformat(), "codeJour": code}


class TempoDayCacheTest(unittest.TestCase):
    def setUp(self):
        self.cache = tempo_cache.TempoDayCache(AVAILABLE_AT)

    def test_unknown_day_is_fetched(self):
        self.assertIsNone(self.cache.get(TUE, today=MON, now=time(9, 0)))

    def test_known_colour_is_reused(self):
        self.cache.put(answer(TUE, 3), today=MON)
        self.assertEqual(self.cache.get(TUE, today=TUE, now=time(5, 0))["codeJour"], 3)

    def test_tomorrow_undetermined_is_reused_until_11_the_same_day(self):
        self.cache.put(answer(TUE, 0), today=MON)
        self.assertEqual(self.cache.get(TUE, today=MON, now=time(10, 59))["codeJour"], 0)

    def test_tomorrow_undetermined_is_fetched_again_after_11(self):
        self.cache.put(answer(TUE, 0), today=MON)
        self.assertIsNone(self.cache.get(TUE, today=MON, now=time(11, 0)))

    def test_undetermined_answer_from_the_day_before_is_not_reused(self):
        # Monday 09:00: tomorrow (Tuesday) is not published yet.
        self.cache.put(answer(TUE, 0), today=MON)
        # Tuesday 05:00: Tuesday is today, its colour is known since Monday 11:00.
        self.assertIsNone(self.cache.get(TUE, today=TUE, now=time(5, 0)))

    def test_newer_answer_replaces_the_older_one(self):
        self.cache.put(answer(TUE, 0), today=MON)
        self.cache.put(answer(TUE, 3), today=MON)
        self.assertEqual(self.cache.get(TUE, today=TUE, now=time(5, 0))["codeJour"], 3)

    def test_today_undetermined_is_fetched_again(self):
        self.cache.put(answer(TUE, 0), today=TUE)
        self.assertIsNone(self.cache.get(TUE, today=TUE, now=time(5, 0)))

    def test_old_days_are_dropped(self):
        for day in (MON, TUE, WED):
            self.cache.put(answer(day, 1), today=day)
        self.cache.put(answer(date(2026, 11, 26), 1), today=WED)
        self.assertIsNone(self.cache.get(MON, today=date(2026, 11, 26), now=time(5, 0)))

    def test_caches_are_not_shared_between_instances(self):
        self.cache.put(answer(TUE, 3), today=MON)
        other = tempo_cache.TempoDayCache(AVAILABLE_AT)
        self.assertIsNone(other.get(TUE, today=TUE, now=time(5, 0)))


if __name__ == "__main__":
    unittest.main()
