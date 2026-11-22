# Real-mode integration (electro-pneumatic press)

## 1. Default behaviour

`MODE` is unset by default, which means `simulation`. The existing simulator,
REST server, HMI and tests are unchanged. `simulation/real_adapter.py` is
independent of `press_server.py` and is only returned by the new factory.

## 2. Strictly read-only real adapter

`ReadOnlyPressAdapter` is a **monitor only**. It intentionally has no API to
start a cycle, arm two-hand control, reset a fault or write Y1/Y2/Y3. Calls to
`set_buttons()`, `set_fault()`, `set_pressure()` and `reset()` raise
`ReadOnlyPressError`. `ALLOW_WRITES=true` is rejected outright for this repo:
there is no software path to an actuator.

The safety relay, E-stop, guard switch and two-hand control remain in the
hardware safety chain (see `docs/safety-sequence.md`). Software monitoring
must never be treated as a safety function or as a substitute for
ISO 13849 / IEC 62061 validation.

## 3. Enabling real mode

```powershell
$env:MODE = 'real'
$env:REAL_STRICT = 'true'
$env:ALLOW_WRITES = 'false'
$env:S7_HOST = '192.0.2.11'      # documentation IP: replace with the PLC IP
$env:S7_RACK = '0'
$env:S7_SLOT = '1'
```

`S7_PORT` defaults to 102. `S7_HOST`, `S7_RACK` and `S7_SLOT` are mandatory in
real mode; placeholder values (`<...>`) count as missing. If `snap7` is not
installed, the configuration is incomplete, or the PLC is unreachable, the
adapter raises `RealModeDependencyError`, `RealModeConfigurationError` or
`RealModeError`. It never falls back to simulation. Optional packages are in
`requirements-real.txt`; they are not needed for simulation tests.

## 4. Address map

`S7_ADDRESS_MAP` is an optional JSON object overriding individual tag
addresses. Address format is `AREA:byte[.bit]` where AREA is `DBnn`, `I`, `Q`
or `M`. Defaults mirror `docs/io-list.md`:

| Tag | Default | Tag | Default |
| --- | --- | --- | --- |
| `Button1` | `I:0.0` | `BothButtons` | `M:0.0` |
| `Button2` | `I:0.1` | `AntiTieDown` | `M:0.1` |
| `SafetyOK` | `I:0.2` | `ClampValve` | `Q:0.0` |
| `GuardClosed` | `I:0.3` | `PressValve` | `Q:0.1` |
| `EStopOK` | `I:0.4` | `RetractValve` | `Q:0.2` |
| `PressureOK` | `I:0.5` | `State` | `M:2` |
| `ClampExtended` | `I:0.6` | `FaultCode` | `M:4` |
| `PressExtended` | `I:0.7` | `CycleCount` | `M:6` |
| `PressHome` | `I:1.0` | `Pressure_bar` | `M:10` |

`Pressure_bar` is read as tenths of bar from `M:10`; `PressureOK` (`I:0.5`) is
the authoritative safety signal. `ClampPosition`/`PressPosition` in the
snapshot are coarse values (100 or 0) derived from the limit switches, not
analogue measurements. Verify and override every address against the
downloaded PLC project before use.

## 5. Programmatic use

```python
from real_adapter import create_press_source

source = create_press_source()
try:
    print(source.tick())
finally:
    close = getattr(source, 'close', None)
    if close:
        close()
```

## 6. Verification

```powershell
python -m unittest discover -s simulation/tests -v
```
