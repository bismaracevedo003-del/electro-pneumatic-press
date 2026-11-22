import json
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from press_server import PressApplication  # noqa: E402
from press_simulator import (  # noqa: E402
    CLAMPING,
    FAULT,
    IDLE,
    PressSimulator,
)


def advance(press, seconds, dt=0.1):
    for _ in range(int(round(seconds / dt))):
        press.tick(dt)


class PressModelTests(unittest.TestCase):
    def setUp(self):
        self.press = PressSimulator()

    def test_initial_state(self):
        state = self.press.snapshot()
        self.assertEqual(state['State'], IDLE)
        self.assertEqual(state['FaultName'], 'NONE')

    def test_single_button_does_not_arm(self):
        self.press.set_buttons(True, False)
        advance(self.press, 1.0)
        self.assertEqual(self.press.state, IDLE)

    def test_short_simultaneous_press_does_not_arm(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.4)
        self.assertEqual(self.press.state, IDLE)

    def test_two_hand_press_arms(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.6)
        self.assertIn(self.press.state, (1, CLAMPING))

    def test_normal_cycle_completes(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.6)
        self.press.set_buttons(False, False)
        advance(self.press, 12)
        state = self.press.snapshot()
        self.assertEqual(state['State'], IDLE)
        self.assertEqual(state['CycleCount'], 1)
        self.assertEqual(state['PressHome'], 1)

    def test_cylinders_reach_positions(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.6)
        self.press.set_buttons(False, False)
        advance(self.press, 7)
        state = self.press.snapshot()
        self.assertEqual(state['ClampPosition'], 100.0)
        self.assertGreaterEqual(state['PressPosition'], 75.0)

    def test_anti_tie_down_requires_release(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.6)
        self.assertEqual(self.press.snapshot()['AntiTieDown'], 1)
        self.press.set_buttons(False, False)
        advance(self.press, 0.1)
        self.assertEqual(self.press.snapshot()['AntiTieDown'], 0)

    def test_single_button_held_flags_anti_tie_down(self):
        self.press.set_buttons(True, False)
        advance(self.press, 5.1)
        self.assertEqual(self.press.fault_code, 6)

    def test_estop_during_cycle(self):
        self.press.set_buttons(True, True)
        advance(self.press, 1.0)
        self.press.set_fault('estop', True)
        advance(self.press, 0.1)
        state = self.press.snapshot()
        self.assertEqual(state['FaultCode'], 1)
        self.assertEqual(state['State'], FAULT)
        self.assertEqual(state['ClampValve'] + state['PressValve'] + state['RetractValve'], 0)

    def test_guard_open_fault(self):
        self.press.set_fault('guard', True)
        advance(self.press, 0.1)
        self.assertEqual(self.press.fault_code, 2)

    def test_safety_relay_fault(self):
        self.press.set_fault('relay', True)
        advance(self.press, 0.1)
        self.assertEqual(self.press.fault_code, 3)

    def test_low_pressure_fault(self):
        self.press.set_pressure(4.0)
        advance(self.press, 0.1)
        self.assertEqual(self.press.fault_code, 4)

    def test_reset_blocked_while_estop_active(self):
        self.press.set_fault('estop', True)
        advance(self.press, 0.1)
        self.assertFalse(self.press.reset())

    def test_reset_clears_fault(self):
        self.press.set_fault('estop', True)
        advance(self.press, 0.1)
        self.press.set_fault('estop', False)
        self.assertTrue(self.press.reset())
        self.assertEqual(self.press.state, IDLE)
        self.assertEqual(self.press.fault_code, 0)

    def test_stroke_timeout(self):
        self.press.set_buttons(True, True)
        advance(self.press, 0.6)
        self.press.set_buttons(False, False)
        self.press._update_mechanics = lambda dt: None
        advance(self.press, 5.2)
        self.assertEqual(self.press.fault_code, 5)

    def test_unknown_fault_raises(self):
        with self.assertRaises(ValueError):
            self.press.set_fault('bad', True)

    def test_pressure_is_clamped(self):
        self.press.set_pressure(20)
        self.assertEqual(self.press.pressure_bar, 10)
        self.press.set_pressure(-5)
        self.assertEqual(self.press.pressure_bar, 0)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = PressApplication(port=0).start()
        time.sleep(0.4)

    def tearDown(self):
        self.app.stop()

    def get(self, path):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.app.port}{path}') as response:
            return json.loads(response.read())

    def post(self, path, payload):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.app.port}{path}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_hmi_page(self):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.app.port}/') as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b'Electro-Pneumatic Press', response.read())

    def test_api_state(self):
        state = self.get('/api/state')
        self.assertEqual(state['StateName'], 'IDLE')
        self.assertIn('Pressure_bar', state)

    def test_api_buttons_and_fault(self):
        self.post('/api/buttons', {'button1': True, 'button2': True})
        time.sleep(0.6)
        self.assertEqual(self.get('/api/state')['BothButtons'], 1)
        self.post('/api/fault', {'fault': 'guard', 'active': True})
        time.sleep(0.2)
        self.assertEqual(self.get('/api/state')['FaultName'], 'GUARD_OPEN')


if __name__ == '__main__':
    unittest.main()
