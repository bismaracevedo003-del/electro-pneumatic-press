# I/O list

| Address | Type | Description | State |
| --- | --- | --- | --- |
| `I0.0` | DI | Two-hand button 1 | 1 = pressed |
| `I0.1` | DI | Two-hand button 2 | 1 = pressed |
| `I0.2` | DI | Safety relay OK | 1 = healthy |
| `I0.3` | DI | Guard closed | 1 = closed |
| `I0.4` | DI | E-stop (NC) | 1 = healthy |
| `I0.5` | DI | Pressure OK | 1 = >= 5.5 bar |
| `I0.6` | DI | Clamp extended | 1 = at position |
| `I0.7` | DI | Press extended | 1 = at position |
| `I1.0` | DI | Press retracted | 1 = home |
| `Q0.0` | DO | Clamp valve Y1 | 1 = extend |
| `Q0.1` | DO | Press valve Y2 | 1 = extend |
| `Q0.2` | DO | Retract valve Y3 | 1 = retract |
| `Q0.3` | DO | Green stack light | 1 = ready |
| `Q0.4` | DO | Red stack light | 1 = fault |

## Internal tags

| Tag | Description |
| --- | --- |
| `B_BothButtons` | Two-hand simultaneity latched |
| `B_AntiTieDown` | Requires both buttons released |
| `B_CycleActive` | Cycle in progress |
| `T_ButtonWindow` | 0.5 s simultaneity timer |
| `T_PressTimeout` | 5 s stroke timeout |
| `FaultCode` | 0 none, 1 E-stop, 2 guard, 3 relay, 4 low pressure, 5 timeout, 6 anti-tie-down |

## Nota (ES)

El E-stop y el relé de seguridad se modelan como entradas NC/OK; en planta la cadena de seguridad no debe depender solo del PLC estándar.
