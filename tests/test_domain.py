import copy
import random
import unittest
from app import domain as d

def fixture(n=8):
    c=d.new_competition("Coupe test","2026-11-01",2026,"organizer")
    c["open"]=[]
    c["people"]=[dict(id=str(i),name=f"Athlète {i}",club=str(i%3),birth="2000-01-01",grade=i%6,sex="M",weight=65,disciplines=["Combat"],status="approved") for i in range(n)]
    c["areas"]=[dict(id="area",name="Aire 1",assistant="assistant")]
    c["officials"]=[dict(id=str(i),name=f"Officiel {i}") for i in range(4)]
    d.generate(c)
    t=c["tables"][0]
    t.update(area="area",judges=["0","1","2"],referee="3")
    d.draw(c,t)
    d.start_table(c,t)
    return c,t

def win(m,side="a",margin=1):
    m.update(sa=margin if side=="a" else 0,sb=margin if side=="b" else 0)
    d.finish(m,m[side],"points")

class CombatTests(unittest.TestCase):
    def test_all_sizes_terminate_without_duplicate_places(self):
        for n in range(2,33):
            with self.subTest(size=n):
                c,t=fixture(n)
                for _ in range(20):
                    for m in t["matches"]:
                        if m["state"]!="done":
                            win(m)
                    if t["status"]=="closed":
                        break
                    d.advance(c,t)
                self.assertEqual(t["status"],"closed")
                self.assertEqual(len(t["places"].values()),len(set(t["places"].values())))
                self.assertEqual(set(t["places"].values())-set(t["members"]),set())
                self.assertIn("1",t["places"])
                self.assertIn("2",t["places"])
                if n>=4:
                    self.assertIn("3",t["places"])
                    self.assertIn("4",t["places"])
                if n>=5:
                    self.assertIn("5",t["places"])

    def test_seven_has_complementary_fight(self):
        c,t=fixture(7)
        spare=t["spare"]
        self.assertEqual(len(t["matches"]),3)
        self.assertTrue(all(spare not in (m["a"],m["b"]) for m in t["matches"]))
        for i,m in enumerate(t["matches"]):
            win(m,margin=i+1)
        expected=t["matches"][0]["loser"]
        d.advance(c,t)
        extra=t["matches"][-1]
        self.assertEqual((extra["a"],extra["b"],extra["kind"]),(spare,expected,"odd"))
        win(extra)
        d.advance(c,t)
        self.assertEqual(t["turn"],2)
        self.assertEqual(len([m for m in t["matches"] if m["turn"]==2]),2)

    def test_six_repechage_when_three_winners(self):
        c,t=fixture(6)
        for i,m in enumerate(t["matches"]):
            win(m,margin=i+1)
        loser=t["matches"][0]["loser"]
        d.advance(c,t)
        self.assertIn(loser,[v for m in t["matches"] if m["turn"]==2 for v in (m["a"],m["b"])])
        self.assertEqual(t["repechages"][0]["participant"],loser)

    def test_clubs_minimum_clashes(self):
        people={str(i):dict(club="A" if i<6 else "B") for i in range(10)}
        pairs,spare=d.pair(list(people),people,random.Random(8))
        self.assertIsNone(spare)
        self.assertEqual(sum(people[a]["club"]==people[b]["club"] for a,b in pairs),1)

    def test_grade_age_and_disqualification(self):
        c,t=fixture(8)
        for m in t["matches"]:
            win(m)
        for m in t["matches"]:
            p=next(p for p in c["people"] if p["id"]==m["loser"])
            p["grade"]=1
        selected=t["matches"][1]["loser"]
        next(p for p in c["people"] if p["id"]==selected)["birth"]="2007-02-01"
        self.assertEqual(d.best_loser(c,t["matches"]),selected)
        t["matches"][1]["reason"]="disqualification"
        self.assertNotEqual(d.best_loser(c,t["matches"]),selected)
        for m in t["matches"]:
            m["reason"]="forfait"
        with self.assertRaises(d.RuleError):
            d.best_loser(c,t["matches"])

    def test_scores_sum_three_judges_all_rounds(self):
        c,t=fixture(2)
        m=t["matches"][0]
        d.start_round(c,t,m)
        with self.assertRaises(d.RuleError):
            d.score(t,m,[[1,2,3],[0,0,0]])
        m["timer"]["elapsed"]=60
        d.score(t,m,[[1,2,3],[0,1,1]])
        self.assertEqual((m["sa"],m["sb"],m["state"]),(6,2,"rest"))
        m["timer"]["elapsed"]=30
        d.start_round(c,t,m)
        m["timer"]["elapsed"]=60
        d.score(t,m,[[0,1,1],[1,1,1]])
        self.assertEqual((m["sa"],m["sb"],m["winner"]),(8,5,m["a"]))

    def test_two_extensions_then_majority_sudden_death(self):
        c,t=fixture(2)
        m=t["matches"][0]
        for duration in (60,60,15,15):
            if m["timer"]:
                m["timer"]["elapsed"]=30
            d.start_round(c,t,m)
            self.assertEqual(m["timer"]["duration"],duration)
            m["timer"]["elapsed"]=duration
            d.score(t,m,[[1,1,1],[1,1,1]])
        m["timer"]["elapsed"]=30
        d.start_round(c,t,m)
        self.assertIsNone(m["timer"]["duration"])
        with self.assertRaises(d.RuleError):
            d.sudden(m,["a","b","none"])
        d.sudden(m,["a","a","b"])
        self.assertEqual((m["winner"],m["sa"],m["sb"]),(m["a"],13,12))

    def test_pause_does_not_count_interruption(self):
        timer=dict(elapsed=3,since=100,running=True,duration=60)
        self.assertEqual(d.elapsed(timer,105),8)
        timer.update(elapsed=8,running=False)
        self.assertEqual(d.elapsed(timer,999),8)

    def test_duplicate_score_and_round_rejected(self):
        c,t=fixture(2)
        m=t["matches"][0]
        d.start_round(c,t,m)
        with self.assertRaises(d.RuleError):
            d.start_round(c,t,m)
        m["timer"]["elapsed"]=60
        d.score(t,m,[[1,1,1],[0,0,0]])
        with self.assertRaises(d.RuleError):
            d.score(t,m,[[1,1,1],[0,0,0]])

    def test_double_engagement_blocked(self):
        c,t=fixture(4)
        first=t["matches"][0]
        d.start_round(c,t,first)
        with self.assertRaises(d.RuleError):
            d.start_round(c,t,t["matches"][1])
        other=copy.deepcopy(t)
        other.update(id="other",area="other-area",matches=[d.match(first["a"],"extra",1)])
        c["tables"].append(other)
        with self.assertRaises(d.RuleError):
            d.start_round(c,other,other["matches"][0])

    def test_correction_removes_unstarted_descendants(self):
        c,t=fixture(4)
        for m in t["matches"]:
            win(m)
        original=t["matches"][0]
        d.advance(c,t)
        d.correct(t,original,[[[0,0,0],[1,1,1]]],original["b"],"points")
        self.assertEqual(t["turn"],1)
        self.assertEqual(len(t["matches"]),2)
        self.assertEqual(original["winner"],original["b"])

    def test_correction_rejects_started_descendant(self):
        c,t=fixture(4)
        for m in t["matches"]:
            win(m)
        original=t["matches"][0]
        d.advance(c,t)
        d.start_round(c,t,t["matches"][-1])
        with self.assertRaises(d.RuleError):
            d.correct(t,original,[[[0,0,0],[1,1,1]]],original["b"],"points")

    def test_barème_five_five_and_club_ties(self):
        c,t=fixture(2)
        win(t["matches"][0])
        d.advance(c,t)
        r=d.rankings(c)
        self.assertEqual([x["points"] for x in r["Adultes"]],[5,5])
        self.assertEqual([x["rank"] for x in r["Clubs"]],[1,1])

    def test_rank_ties_same_grade_birth(self):
        c,t=fixture(2)
        for p in c["people"]:
            p["grade"]=0
        win(t["matches"][0]);d.advance(c,t)
        self.assertEqual([x["rank"] for x in d.rankings(c)["Adultes"]],[1,1])

    def test_weights_and_season_boundary(self):
        c,t=fixture(2)
        p=c["people"][0]
        p.update(birth="2014-12-31",weight=40)
        self.assertEqual(d.age_index(p,c),4)
        self.assertIn("−45 kg",d.category(p,c))
        p["birth"]="2015-01-01"
        self.assertEqual(d.age_index(p,c),3)

    def test_draw_cannot_be_repeated(self):
        c,t=fixture(2)
        with self.assertRaises(d.RuleError):
            d.draw(c,t)

