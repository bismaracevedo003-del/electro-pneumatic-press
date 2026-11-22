# PLC program reference

The TIA Portal project is not distributed as a binary. The versioned source is this rung/instruction reference plus the SCL function blocks in `plc/program/src/`.

## PRG_SAFETY

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `XIO I0.4 OTL FaultCode := 1` | Latch E-stop fault |
| 1 | `XIO I0.3 OTL FaultCode := 2` | Latch guard fault |
| 2 | `XIO I0.2 OTL FaultCode := 3` | Latch safety relay fault |
| 3 | `XIO I0.5 OTL FaultCode := 4` | Latch low pressure |
| 4 | `XIC Reset XIO I0.4 XIO I0.3 XIO I0.2 XIO I0.5 OTU FaultCode` | Reset when safe |

## PRG_TWO_HAND

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `XIC I0.0 XIC I0.1 TON T_ButtonWindow 500 ms` | Simultaneity window |
| 1 | `XIC T_ButtonWindow.DN OTL B_BothButtons` | Arm cycle |
| 2 | `XIO I0.0 XIO I0.1 OTU B_AntiTieDown` | Require release of both buttons |

## PRG_SEQUENCE

| Step | Transition | Outputs |
| --- | --- | --- |
| 0 IDLE | Both buttons + anti-tie-down clear | — |
| 1 ARMED | Step 0 | — |
| 2 CLAMPING | Clamp extended input | Y1 |
| 3 PRESSING | Press extended input | Y2 |
| 4 HOLDING | 1.5 s dwell | Y2 |
| 5 RETRACTING | Press retracted input | Y3 |
| 6 DONE | Clamp home | — |

## PRG_OUTPUTS

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `XIC Step_Clamping OTE Q0.0` | Clamp valve |
| 1 | `XIC Step_Pressing OR Step_Holding OTE Q0.1` | Press valve |
| 2 | `XIC Step_Retracting OTE Q0.2` | Retract valve |
| 3 | `XIC FaultCode == 0 OTE Q0.3` | Green light |
| 4 | `XIC FaultCode > 0 OTE Q0.4` | Red light |

## Nota (ES)

La lógica de seguridad en planta debe implementarse con dispositivos certificados; este ejemplo muestra la secuencia y su interfaz con el PLC estándar.
