# Test plan

## 1. Cases

| ID | Case | Expected | Status |
| --- | --- | --- | --- |
| T-01 | Normal cycle | IDLE → ... → DONE, count +1 | Pass |
| T-02 | Single button | No arm | Pass |
| T-03 | Buttons outside 0.5 s | No arm | Pass |
| T-04 | Anti-tie-down release required | New cycle blocked until both released | Pass |
| T-05 | E-stop during cycle | Fault 1, outputs off | Pass |
| T-06 | Guard open | Cycle inhibited | Pass |
| T-07 | Safety relay fault | Cycle inhibited | Pass |
| T-08 | Low pressure | Fault 4 | Pass |
| T-09 | Clamp timeout | Fault 5 | Pass |
| T-10 | Press timeout | Fault 5 | Pass |
| T-11 | Reset clears faults | State IDLE when conditions OK | Pass |
| T-12 | Cycle counter | Increments only on complete cycles | Pass |
| T-13 | Outputs off in FAULT | Y1/Y2/Y3 all 0 | Pass |
| T-14 | Home sensor required | No cycle if not retracted | Pass |
| T-15 | HMI state endpoint | Tags present | Pass |
| T-16 | HMI button endpoints | Buttons/faults update model | Pass |

## 2. Command

```powershell
python -m unittest discover -s simulation/tests -v
```

## 3. Pending

- Download TIA project to S7-1200.
- Wire safety relay and dual-hand station.
- Validate pneumatic pressure and stroke times on real cylinder.

## 4. Nota (ES)

Todas las pruebas son simuladas; no se presentan como validación de seguridad funcional.
