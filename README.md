# Electro-Pneumatic Press Automation

**Siemens S7-1200 · TIA Portal · Safety relay · Two-hand control · Pneumatic cylinder**

Electro-pneumatic press with safety relay, two-hand actuation, anti-tie-down logic, clamping and pressing sequence, pressure/limit feedback and fault diagnostics. Includes a Python pneumatic simulator with a web HMI.

> **Nota (ES):** Proyecto de demostración. La lógica de seguridad se modeló en simulador; no sustituye una validación de seguridad conforme a ISO 13849/IEC 62061.

---

## 1. Industrial problem

A pneumatic press must only move when both operator buttons are pressed simultaneously, the guard is closed and the safety relay is healthy. It must clamp, press, hold and retract with pressure and position feedback, and stop safely on faults.

## 2. Objectives

- Implement two-hand control with 0.5 s simultaneity window.
- Anti-tie-down: both buttons must be released before a new cycle.
- Monitor safety relay, E-stop, guard switch and air pressure.
- Control clamp and press solenoid valves with stroke feedback.
- Detect low pressure, stuck button, timeout and cylinder not reaching position.
- Expose cycle count, state and faults to a web HMI.

## 3. Architecture

```text
Two-hand buttons + safety relay + limit/pressure switches
                    |
              S7-1200 (SCL/Ladder)
                    |
       Solenoid valves Y1/Y2/Y3 + stack light
                    |
        Python pneumatic simulator + HMI
```

See [docs/architecture.md](docs/architecture.md), [docs/safety-sequence.md](docs/safety-sequence.md), [docs/io-list.md](docs/io-list.md) and [docs/test-plan.md](docs/test-plan.md).

## 4. Components

| Layer | Technology |
| --- | --- |
| PLC | Siemens S7-1200, TIA Portal V19 |
| Safety | Safety relay feedback E-stop/guard |
| Simulation | Python state machine + pneumatic model |
| HMI | Static HTML/JS served by Python |
| Tests | Python `unittest` |

## 5. Run

```powershell
cd "C:\Users\Bismarck Acevedo\Documents\Github\electro-pneumatic-press"
python -m unittest discover -s simulation/tests -v
python simulation/press_server.py
```

Open `http://127.0.0.1:4040`.

Verified: **20 Python tests OK**; HMI smoke `Page=200`, two-hand arming, guard fault and reset confirmed.

## 6. Documents

- [Architecture](docs/architecture.md)
- [I/O list](docs/io-list.md)
- [Safety sequence](docs/safety-sequence.md)
- [Ladder/SCL reference](plc/documentation/ladder-reference.md)
- [Test plan](docs/test-plan.md)

## 7. Screenshots

- [Press HMI](screenshots/hmi.svg)
- [Pneumatic circuit](screenshots/pneumatic-circuit.svg)

## 8. Evidence matrix

| Item | Status |
| --- | --- |
| Two-hand and anti-tie-down logic | Simulated and unit tested |
| Press state machine | Simulated and unit tested |
| Pressure/limit feedback | Simulated and unit tested |
| Safety relay and E-stop priority | Simulated and unit tested |
| PLC SCL/Ladder | Designed and documented, not downloaded |

## 9. Limitations and future work

- No real safety relay or pneumatic valves connected.
- Safety validation requires qualified personnel and risk assessment.
- Add force monitoring and data logging in a later revision.

## 10. Quality checklist

- [x] Industrial problem and safety context defined
- [x] I/O list and sequence documentation
- [x] PLC source reference
- [x] Pneumatic simulator
- [x] Web HMI
- [x] Automated tests
- [x] Screenshots and docs
- [x] Repository on `main`

---

**Author:** Bismarck Acevedo — Electronic Engineer, Industrial Automation & PLC Programming.
