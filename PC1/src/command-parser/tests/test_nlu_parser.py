"""
Unit tests for the rule-based NLU command parser.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nlu_parser import parse_command


class TestTakeoff:
    def test_takeoff_basic(self):
        r = parse_command("take off")
        assert r["success"] is True
        assert r["intent"] == "takeoff"
        assert r["altitude"] == 10.0  # default

    def test_takeoff_with_altitude(self):
        r = parse_command("take off to 20 meters")
        assert r["success"] is True
        assert r["intent"] == "takeoff"
        assert r["altitude"] == 20.0

    def test_takeoff_launch(self):
        r = parse_command("launch")
        assert r["intent"] == "takeoff"

    def test_takeoff_ascend(self):
        r = parse_command("ascend to 30m")
        assert r["intent"] == "takeoff"
        assert r["altitude"] == 30.0


class TestLand:
    def test_land_basic(self):
        r = parse_command("land")
        assert r["success"] is True
        assert r["intent"] == "land"

    def test_landing(self):
        r = parse_command("landing")
        assert r["intent"] == "land"

    def test_descend(self):
        r = parse_command("descend")
        assert r["intent"] == "land"

    def test_touch_down(self):
        r = parse_command("touch down")
        assert r["intent"] == "land"


class TestGoto:
    def test_goto_location(self):
        r = parse_command("fly to forest")
        assert r["success"] is True
        assert r["intent"] == "goto"
        assert r["location"] == "forest"
        assert r["target_gps"] is not None

    def test_goto_with_altitude(self):
        r = parse_command("go to building at 15 meters")
        assert r["intent"] == "goto"
        assert r["location"] == "building"
        assert r["altitude"] == 15.0

    def test_goto_gps_coords(self):
        r = parse_command("fly to -6.163, 35.752 at 30m")
        assert r["intent"] == "goto"
        assert r["target_gps"] is not None
        assert abs(r["target_gps"]["lat"] - (-6.163)) < 0.001
        assert abs(r["target_gps"]["lon"] - 35.752) < 0.001

    def test_goto_base(self):
        r = parse_command("go to base")
        assert r["intent"] == "goto"
        assert r["location"] == "base"


class TestRTL:
    def test_rtl(self):
        r = parse_command("rtl")
        assert r["success"] is True
        assert r["intent"] == "rtl"

    def test_return_home(self):
        r = parse_command("return home")
        assert r["intent"] == "rtl"

    def test_go_home(self):
        r = parse_command("go home")
        assert r["intent"] == "rtl"


class TestHover:
    def test_hover(self):
        r = parse_command("hover")
        assert r["success"] is True
        assert r["intent"] == "hover"

    def test_stop(self):
        r = parse_command("stop")
        assert r["intent"] == "hover"

    def test_hold_position(self):
        r = parse_command("hold position")
        assert r["intent"] == "hover"


class TestArmDisarm:
    def test_arm(self):
        r = parse_command("arm")
        assert r["success"] is True
        assert r["intent"] == "arm"

    def test_disarm(self):
        r = parse_command("disarm")
        assert r["intent"] == "disarm"

    def test_shut_down(self):
        r = parse_command("shut down")
        assert r["intent"] == "disarm"


class TestUnknown:
    def test_empty_string(self):
        r = parse_command("")
        assert r["success"] is False
        assert r["intent"] == "unknown"
        assert "Empty" in r["reason"]

    def test_gibberish(self):
        r = parse_command("dance for me please")
        assert r["success"] is False
        assert r["intent"] == "unknown"
        assert "didn't understand" in r["reason"]

    def test_whitespace_only(self):
        r = parse_command("   ")
        assert r["success"] is False
        assert r["intent"] == "unknown"


class TestEdgeCases:
    def test_altitude_various_formats(self):
        cases = [
            ("climb to 50", "takeoff", 50.0),
            ("fly to forest altitude 30", "goto", 30.0),
            ("go to base at 25 meters", "goto", 25.0),
            ("takeoff at 15m", "takeoff", 15.0),
        ]
        for text, expected_intent, expected_alt in cases:
            r = parse_command(text)
            assert r["intent"] == expected_intent, f"Failed for {text!r}"
            assert r["altitude"] == expected_alt, f"Altitude mismatch for {text!r}"

    def test_case_insensitivity(self):
        r = parse_command("TAKE OFF TO 20 METERS")
        assert r["intent"] == "takeoff"
        assert r["altitude"] == 20.0

    def test_mixed_keywords(self):
        r = parse_command("I want to go to the forest area")
        assert r["intent"] == "goto"
        assert r["location"] == "forest"

    def test_confidence_range(self):
        r = parse_command("land")
        assert 0.0 <= r["confidence"] <= 1.0
