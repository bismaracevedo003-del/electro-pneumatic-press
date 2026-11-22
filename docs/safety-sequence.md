# Safety and operating sequence

## 1. Preconditions

A cycle can start only when:

- E-stop healthy.
- Guard closed.
- Safety relay OK.
- Air pressure >= 5.5 bar.
- Both buttons released (anti-tie-down reset).
- Cylinder at home position.

## 2. Two-hand control

1. Operator presses both buttons within 0.5 s.
2. `B_BothButtons` latches only if the safety preconditions are valid.
3. Buttons must be released before the next cycle; holding a single button for more than 5 s raises an anti-tie-down fault.
4. Both buttons must be released before another cycle can arm.

## 3. Press sequence

| Step | Action | Feedback |
| --- | --- | --- |
| 1 | Energize clamp Y1 | Clamp extended input |
| 2 | Energize press Y2 | Press extended input |
| 3 | Hold pressure for 1.5 s | Pressure OK maintained |
| 4 | Energize retract Y3 | Press retracted input |
| 5 | Retract clamp | Home position |
| 6 | Cycle complete, increment count | Ready state |

## 4. Faults

| Code | Fault | Effect |
| --- | --- | --- |
| 1 | E-stop | Immediate safe stop |
| 2 | Guard open | Cycle inhibited |
| 3 | Safety relay not OK | Cycle inhibited |
| 4 | Low air pressure | Cycle inhibited/aborted |
| 5 | Stroke timeout | Fault latched |
| 6 | Anti-tie-down | Fault latched |

## 5. Nota (ES)

Esta secuencia es didáctica; una máquina real requiere análisis de riesgos, categoría de seguridad y validación por personal calificado.
