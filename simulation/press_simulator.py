import json

IDLE = 0
ARMED = 1
CLAMPING = 2
PRESSING = 3
HOLDING = 4
RETRACTING = 5
DONE = 6
FAULT = 99

STATE_NAMES = {
    IDLE: 'IDLE', ARMED: 'ARMED', CLAMPING: 'CLAMPING', PRESSING: 'PRESSING',
    HOLDING: 'HOLDING', RETRACTING: 'RETRACTING', DONE: 'DONE', FAULT: 'FAULT',
}

FAULT_NAMES = {
    0: 'NONE', 1: 'E_STOP', 2: 'GUARD_OPEN', 3: 'SAFETY_RELAY',
    4: 'LOW_PRESSURE', 5: 'STROKE_TIMEOUT', 6: 'ANTI_TIE_DOWN',
}


class PressSimulator:
    def __init__(self, dt=0.1):
        self.dt = float(dt)
        self.state = IDLE
        self.fault_code = 0
        self.cycle_count = 0
        self.button1 = False
        self.button2 = False
        self.both_buttons = False
        self.anti_tie_down = False
        self.button_timer = 0.0
        self.single_button_timer = 0.0
        self.hold_timer = 0.0
        self.stroke_timer = 0.0
        self.last_state = IDLE
        self.safety_ok = True
        self.guard_closed = True
        self.e_stop_ok = True
        self.pressure_bar = 6.5
        self.clamp_position = 0.0
        self.press_position = 0.0
        self.clamp_valve = False
        self.press_valve = False
        self.retract_valve = False

    @property
    def pressure_ok(self):
        return self.pressure_bar >= 5.5

    @property
    def clamp_extended(self):
        return self.clamp_position >= 95.0

    @property
    def press_extended(self):
        return self.press_position >= 95.0

    @property
    def press_home(self):
        return self.press_position <= 5.0 and self.clamp_position <= 5.0

    def set_buttons(self, button1, button2):
        self.button1 = bool(button1)
        self.button2 = bool(button2)

    def set_pressure(self, bar):
        self.pressure_bar = max(0.0, min(10.0, float(bar)))

    def set_fault(self, fault, active):
        active = bool(active)
        if fault == 'estop':
            self.e_stop_ok = not active
        elif fault == 'guard':
            self.guard_closed = not active
        elif fault == 'relay':
            self.safety_ok = not active
        elif fault == 'pressure':
            self.pressure_bar = 4.0 if active else 6.5
        else:
            raise ValueError(f'unknown fault: {fault}')

    def reset(self):
        if not (self.e_stop_ok and self.guard_closed and self.safety_ok and self.pressure_ok):
            return False
        self.fault_code = 0
        self.state = IDLE
        self.button_timer = 0.0
        self.single_button_timer = 0.0
        self.hold_timer = 0.0
        self.stroke_timer = 0.0
        self.last_state = IDLE
        self.clamp_valve = False
        self.press_valve = False
        self.retract_valve = False
        return True

    def tick(self, dt=None):
        dt = self.dt if dt is None else float(dt)
        self._update_safety()
        if self.fault_code:
            self._all_valves_off()
            return self.snapshot()
        self._update_two_hand(dt)
        if self.fault_code:
            self._all_valves_off()
            return self.snapshot()
        self._update_sequence(dt)
        self._update_mechanics(dt)
        self._update_stroke_timer(dt)
        return self.snapshot()

    def _update_safety(self):
        if not self.e_stop_ok:
            self.fault_code = 1
        elif not self.guard_closed:
            self.fault_code = 2
        elif not self.safety_ok:
            self.fault_code = 3
        elif not self.pressure_ok:
            self.fault_code = 4

    def _update_two_hand(self, dt):
        if self.button1 and self.button2:
            self.button_timer += dt
            self.single_button_timer = 0.0
        else:
            self.button_timer = 0.0
        if self.button1 != self.button2:
            self.single_button_timer += dt
        else:
            self.single_button_timer = 0.0
        if self.button_timer >= 0.5 and not self.anti_tie_down:
            self.both_buttons = True
        if self.single_button_timer >= 5.0:
            self.fault_code = 6
        if not self.button1 and not self.button2:
            self.anti_tie_down = False
            if self.state in (IDLE, DONE, FAULT):
                self.both_buttons = False

    def _update_sequence(self, dt):
        if self.state == IDLE and self.both_buttons and self.press_home:
            self.state = ARMED
            self.anti_tie_down = True
            return
        if self.state == ARMED:
            self.state = CLAMPING
            return
        if self.state == CLAMPING:
            self.clamp_valve = True
            if self.clamp_extended:
                self.state = PRESSING
            return
        if self.state == PRESSING:
            self.press_valve = True
            if self.press_extended:
                self.state = HOLDING
            return
        if self.state == HOLDING:
            self.hold_timer += dt
            self.press_valve = True
            if self.hold_timer >= 1.5:
                self.state = RETRACTING
                self.hold_timer = 0.0
            return
        if self.state == RETRACTING:
            self.retract_valve = True
            if self.press_home:
                self.state = DONE
                self.cycle_count += 1
                self.both_buttons = False
            return
        if self.state == DONE:
            self.state = IDLE

    def _update_mechanics(self, dt):
        if self.clamp_valve and not self.retract_valve:
            self.clamp_position = min(100.0, self.clamp_position + 50.0 * dt)
        if self.press_valve and not self.retract_valve:
            self.press_position = min(100.0, self.press_position + 25.0 * dt)
        if self.retract_valve:
            self.press_position = max(0.0, self.press_position - 50.0 * dt)
            self.clamp_position = max(0.0, self.clamp_position - 50.0 * dt)

    def _update_stroke_timer(self, dt):
        if self.state != self.last_state:
            self.stroke_timer = 0.0
            self.last_state = self.state
        if self.state in (CLAMPING, PRESSING, RETRACTING):
            self.stroke_timer += dt
        if self.stroke_timer >= 5.0:
            self.fault_code = 5

    def _all_valves_off(self):
        self.clamp_valve = False
        self.press_valve = False
        self.retract_valve = False
        self.state = FAULT

    def snapshot(self):
        return {
            'State': self.state,
            'StateName': STATE_NAMES.get(self.state, 'UNKNOWN'),
            'FaultCode': self.fault_code,
            'FaultName': FAULT_NAMES.get(self.fault_code, 'UNKNOWN'),
            'CycleCount': self.cycle_count,
            'Button1': int(self.button1),
            'Button2': int(self.button2),
            'BothButtons': int(self.both_buttons),
            'AntiTieDown': int(self.anti_tie_down),
            'SafetyOK': int(self.safety_ok),
            'GuardClosed': int(self.guard_closed),
            'EStopOK': int(self.e_stop_ok),
            'PressureOK': int(self.pressure_ok),
            'Pressure_bar': round(self.pressure_bar, 2),
            'ClampPosition': round(self.clamp_position, 1),
            'PressPosition': round(self.press_position, 1),
            'ClampExtended': int(self.clamp_extended),
            'PressExtended': int(self.press_extended),
            'PressHome': int(self.press_home),
            'ClampValve': int(self.clamp_valve),
            'PressValve': int(self.press_valve),
            'RetractValve': int(self.retract_valve),
            'source': 'simulator',
        }


def run_demo(seconds=15):
    press = PressSimulator()
    press.set_buttons(True, True)
    for index in range(int(seconds / 0.1)):
        if index == 6:
            press.set_buttons(False, False)
        state = press.tick()
        if index % 50 == 0:
            print(json.dumps(state, sort_keys=True))


if __name__ == '__main__':
    run_demo()
