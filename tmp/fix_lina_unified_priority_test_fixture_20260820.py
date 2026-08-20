#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/config/tests/test_lina_home_calendar_agenda_regression.js")
s = p.read_text(encoding="utf-8")
old = """  card._agendaItems = [criticalA, highToday];
  card._calendarEvents = [event90];
  card._lastRenderKey = "";
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  assert(html.includes("Kritický A"), "critical todo must render");
  assert(html.includes("Schůzka za 90 minut"), "imminent calendar row must render");
"""
new = """  const renderNow = Date.now();
  const renderEvent = {
    start:new Date(renderNow + 30 * 60000).toISOString(),
    end:new Date(renderNow + 90 * 60000).toISOString(),
    summary:"Schůzka za 30 minut",
    _calendarEntity:"calendar.hlavni",
  };
  card._agendaItems = [criticalA, highToday];
  card._calendarEvents = [renderEvent];
  card._lastRenderKey = "";
  card._render(true);
  const html = card.shadowRoot.innerHTML;
  assert(html.includes("Kritický A"), "critical todo must render");
  assert(html.includes("Schůzka za 30 minut"), "imminent calendar row must render");
"""
count = s.count(old)
if count != 1:
    raise SystemExit(f"RENDER_FIXTURE_ANCHOR_COUNT={count}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("LINA_UNIFIED_PRIORITY_TEST_FIXTURE_FIXED")
