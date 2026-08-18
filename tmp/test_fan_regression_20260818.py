from pathlib import Path
import unittest, yaml

S = yaml.safe_load(Path("/config/scripts.yaml").read_text())
A = yaml.safe_load(Path("/config/automations.yaml").read_text())

def actions(obj):
    if isinstance(obj, dict):
        if "action" in obj:
            yield obj
        for v in obj.values():
            yield from actions(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from actions(v)

def retry_calls(checkpoints):
    n = 1
    for fan_state, minimum, manual in checkpoints:
        if (fan_state, minimum, manual) != ("off", "idle", "idle"):
            break
        n += 1
    return n

class FanRaceRegression(unittest.TestCase):
    def setUp(self):
        self.off = S["loznice_vetrak_vypnout_spolehlive"]["sequence"]
        self.manual = next(x for x in A if str(x.get("id")) == "markvarec_loznice_vetrak_manualni_13min")

    def test_manual_on_cancels_inflight_off_first(self):
        first = self.manual["actions"][0]
        self.assertEqual(first.get("action"), "script.turn_off")
        target = first.get("target", {}).get("entity_id")
        self.assertEqual(target, "script.loznice_vetrak_vypnout_spolehlive")

    def test_each_delayed_retry_has_race_guards(self):
        off_idx = [i for i,x in enumerate(self.off) if isinstance(x,dict) and x.get("action") == "fan.turn_off"]
        self.assertEqual(len(off_idx), 3)
        need = {
            ("fan.loznice_vetrak_loznice_zasuvka_1", "off"),
            ("timer.loznice_vetrak_minimalni_beh", "idle"),
            ("timer.loznice_vetrak_rucni", "idle"),
        }
        for a,b in zip(off_idx, off_idx[1:]):
            got = {(x.get("entity_id"),x.get("state")) for x in self.off[a+1:b]
                   if isinstance(x,dict) and x.get("condition") == "state"}
            self.assertTrue(need <= got, f"missing retry guards: {need-got}")

    def test_manual_protection_timers_remain(self):
        calls = list(actions(self.manual))
        started = {x.get("target",{}).get("entity_id") for x in calls if x.get("action") == "timer.start"}
        self.assertIn("timer.loznice_vetrak_minimalni_beh", started)
        self.assertIn("timer.loznice_vetrak_rucni", started)

    def test_normal_stale_off_still_retries_three_times(self):
        self.assertEqual(retry_calls([("off","idle","idle"),("off","idle","idle")]), 3)

    def test_manual_on_aborts_remaining_retries(self):
        self.assertEqual(retry_calls([("on","active","active"),("off","active","active")]), 1)

    def test_timer_blocks_retry_even_if_fan_looks_off_again(self):
        self.assertEqual(retry_calls([("off","active","idle"),("off","active","idle")]), 1)

    def test_unknown_state_fails_safe(self):
        self.assertEqual(retry_calls([("unknown","idle","idle")]), 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
