"""Optional read-only real-mode (Siemens S7) source for the press.

This adapter is strictly a monitor: it has no cycle-start or output-write
API. Two-hand control, guard, E-stop and the safety relay stay in the
hardware safety chain and cannot be bypassed from software.

Address format: ``AREA:byte[.bit]`` where AREA is ``DBnn``, ``I``, ``Q`` or
``M`` (for example ``I0:0`` or ``M2``).
"""

from __future__ import annotations

import json
import os
import re
import struct
from dataclasses import dataclass
from typing import Any

TAG_TYPES = {
    'Button1': 'bool',
    'Button2': 'bool',
    'SafetyOK': 'bool',
    'GuardClosed': 'bool',
    'EStopOK': 'bool',
    'PressureOK': 'bool',
    'ClampExtended': 'bool',
    'PressExtended': 'bool',
    'PressHome': 'bool',
    'BothButtons': 'bool',
    'AntiTieDown': 'bool',
    'ClampValve': 'bool',
    'PressValve': 'bool',
    'RetractValve': 'bool',
    'State': 'int',
    'FaultCode': 'int',
    'CycleCount': 'dint',
    'Pressure_bar': 'scaled10',
}

DEFAULT_S7_ADDRESS_MAP = {
    'Button1': 'I:0.0',
    'Button2': 'I:0.1',
    'SafetyOK': 'I:0.2',
    'GuardClosed': 'I:0.3',
    'EStopOK': 'I:0.4',
    'PressureOK': 'I:0.5',
    'ClampExtended': 'I:0.6',
    'PressExtended': 'I:0.7',
    'PressHome': 'I:1.0',
    'BothButtons': 'M:0.0',
    'AntiTieDown': 'M:0.1',
    'ClampValve': 'Q:0.0',
    'PressValve': 'Q:0.1',
    'RetractValve': 'Q:0.2',
    'State': 'M:2',
    'FaultCode': 'M:4',
    'CycleCount': 'M:6',
    'Pressure_bar': 'M:10',
}

_ADDRESS_RE = re.compile(r'^(?P<area>DB\d+|I|Q|M):(?P<byte>\d+)(?:\.(?P<bit>[0-7]))?$')
_TRUE_VALUES = ('1', 'true', 'yes', 'on')
_FALSE_VALUES = ('0', 'false', 'no', 'off')


class RealModeError(RuntimeError):
    """Base error for the optional real-mode adapter."""


class RealModeConfigurationError(RealModeError):
    """Raised when MODE=real is requested with incomplete or invalid config."""


class RealModeDependencyError(RealModeError):
    """Raised when MODE=real is requested but its optional package is absent."""


class ReadOnlyPressError(RealModeError):
    """Raised for any attempt to command or reset the real press from software."""


@dataclass(frozen=True)
class RealConfig:
    mode: str
    strict: bool
    allow_writes: bool
    log_level: str
    host: str
    port: int
    rack: int
    slot: int
    address_map: dict[str, str]


def _filled(value: Any) -> bool:
    text = '' if value is None else str(value).strip()
    return bool(text) and not text.startswith('<')


def _env_bool(env: Any, name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    text = str(raw).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise RealModeConfigurationError(f'{name} must be true or false, got {raw!r}')


def _env_int(env: Any, name: str, default: int, minimum: int, maximum: int) -> int:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise RealModeConfigurationError(f'{name} must be an integer, got {raw!r}') from exc
    if not minimum <= value <= maximum:
        raise RealModeConfigurationError(f'{name} must be between {minimum} and {maximum}, got {value}')
    return value


def _parse_address(address: str) -> tuple[str, int, int, int | None]:
    text = '' if address is None else str(address).strip().upper()
    match = _ADDRESS_RE.fullmatch(text)
    if not match:
        raise RealModeConfigurationError(
            f'Invalid S7 address {address!r}; expected AREA:byte[.bit] '
            f'(AREA = DBnn, I, Q or M)'
        )
    area = match.group('area')
    db_number = int(area[2:]) if area.startswith('DB') else 0
    area_kind = 'DB' if area.startswith('DB') else area
    bit = match.group('bit')
    return area_kind, db_number, int(match.group('byte')), int(bit) if bit is not None else None


def _load_address_map(env: Any) -> dict[str, str]:
    result = dict(DEFAULT_S7_ADDRESS_MAP)
    raw = env.get('S7_ADDRESS_MAP')
    if raw is None or not str(raw).strip():
        return result
    try:
        overrides = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise RealModeConfigurationError(f'S7_ADDRESS_MAP must be valid JSON: {exc}') from exc
    if not isinstance(overrides, dict):
        raise RealModeConfigurationError('S7_ADDRESS_MAP must be a JSON object of tag -> address')
    unknown = sorted(set(overrides) - set(result))
    if unknown:
        raise RealModeConfigurationError(f'S7_ADDRESS_MAP contains unknown tags: {", ".join(unknown)}')
    for tag, address in overrides.items():
        _, _, _, bit = _parse_address(str(address))
        if TAG_TYPES[tag] != 'bool' and bit is not None:
            raise RealModeConfigurationError(f'S7_ADDRESS_MAP tag {tag} is not bool; remove the bit suffix')
        if TAG_TYPES[tag] == 'bool' and bit is None:
            raise RealModeConfigurationError(f'S7_ADDRESS_MAP tag {tag} is bool; add a .bit suffix')
        result[tag] = str(address).strip().upper()
    return result


def load_real_config(env: Any = None) -> RealConfig:
    """Validate MODE=real settings. Never supplies simulation defaults for missing values."""
    env = os.environ if env is None else env
    mode = str(env.get('MODE', 'simulation')).strip().lower() or 'simulation'
    if mode not in ('simulation', 'real'):
        raise RealModeConfigurationError(f'MODE must be "simulation" or "real", got {mode!r}')

    strict = _env_bool(env, 'REAL_STRICT', True)
    allow_writes = _env_bool(env, 'ALLOW_WRITES', False)
    log_level = str(env.get('LOG_LEVEL', 'INFO')).strip().upper() or 'INFO'

    if mode == 'simulation':
        return RealConfig(mode, strict, allow_writes, log_level, '', 102, 0, 1, dict(DEFAULT_S7_ADDRESS_MAP))

    if not strict:
        raise RealModeConfigurationError(
            'REAL_STRICT=false is not allowed with MODE=real; silent fallback to simulation is forbidden'
        )
    missing = [name for name in ('S7_HOST', 'S7_RACK', 'S7_SLOT') if not _filled(env.get(name))]
    if missing:
        raise RealModeConfigurationError(
            'MODE=real requires explicit configuration; missing or placeholder values: ' + ', '.join(missing)
        )
    return RealConfig(
        mode=mode,
        strict=strict,
        allow_writes=allow_writes,
        log_level=log_level,
        host=str(env['S7_HOST']).strip(),
        port=_env_int(env, 'S7_PORT', 102, 1, 65535),
        rack=_env_int(env, 'S7_RACK', 0, 0, 7),
        slot=_env_int(env, 'S7_SLOT', 1, 0, 7),
        address_map=_load_address_map(env),
    )


class ReadOnlyPressAdapter:
    """Read-only S7 monitor. No cycle start, reset or output write is available."""

    writable = False

    def __init__(self, env: Any = None):
        self.config = load_real_config(env)
        if self.config.mode != 'real':
            raise RealModeConfigurationError('ReadOnlyPressAdapter requires MODE=real')
        if self.config.allow_writes:
            raise ReadOnlyPressError(
                'ALLOW_WRITES=true is rejected by the press adapter: this monitor is read-only for safety'
            )
        self.address_map = self.config.address_map
        self._client = None
        self._area_codes: dict[str, Any] = {}

    def connect(self) -> 'ReadOnlyPressAdapter':
        try:
            import snap7
        except ImportError as exc:
            raise RealModeDependencyError(
                'MODE=real requires python-snap7; install requirements-real.txt on the target host. '
                'No simulation fallback is available.'
            ) from exc
        areas = snap7.types.Areas
        self._area_codes = {'DB': areas.DB, 'I': areas.PE, 'Q': areas.PA, 'M': areas.MK}
        client = snap7.client.Client()
        try:
            client.connect(self.config.host, self.config.rack, self.config.slot, self.config.port)
        except Exception as exc:
            raise RealModeError(
                f'Cannot connect to S7 PLC at {self.config.host} '
                f'rack={self.config.rack} slot={self.config.slot} port={self.config.port}: {exc}'
            ) from exc
        self._client = client
        return self

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            finally:
                self._client = None

    def _read_tag(self, tag: str) -> Any:
        if self._client is None:
            raise RealModeError('S7 client is not connected; call connect() first')
        if tag not in self.address_map:
            raise RealModeConfigurationError(f'No address configured for tag {tag!r}')
        area_kind, db_number, byte, bit = _parse_address(self.address_map[tag])
        size = 1 if bit is not None else {'int': 2, 'dint': 4, 'scaled10': 2}[TAG_TYPES[tag]]
        try:
            data = self._client.read_area(self._area_codes[area_kind], db_number, byte, size)
        except Exception as exc:
            raise RealModeError(f'S7 read failed for {tag} at {self.address_map[tag]}: {exc}') from exc
        kind = TAG_TYPES[tag]
        if kind == 'bool':
            if bit is None:
                raise RealModeConfigurationError(f'Bool tag {tag} needs a .bit suffix')
            return bool(data[0] & (1 << bit))
        if kind == 'int':
            return struct.unpack('>h', data)[0]
        if kind == 'dint':
            return struct.unpack('>i', data)[0]
        return round(struct.unpack('>h', data)[0] / 10.0, 2)

    def snapshot(self) -> dict[str, Any]:
        from press_simulator import FAULT_NAMES, STATE_NAMES

        values = {tag: self._read_tag(tag) for tag in TAG_TYPES}
        values['StateName'] = STATE_NAMES.get(values['State'], 'UNKNOWN')
        values['FaultName'] = FAULT_NAMES.get(values['FaultCode'], 'UNKNOWN')
        values['ClampPosition'] = 100.0 if values['ClampExtended'] else 0.0
        values['PressPosition'] = 100.0 if values['PressExtended'] else 0.0
        values['source'] = 'real-s7-readonly'
        return values

    def tick(self, dt: float = 0.1) -> dict[str, Any]:
        del dt
        return self.snapshot()

    def set_buttons(self, button1: bool, button2: bool) -> None:
        del button1, button2
        raise ReadOnlyPressError(
            'Two-hand buttons must be operated physically; the real adapter cannot command a cycle'
        )

    def set_fault(self, fault: str, active: bool) -> None:
        del fault, active
        raise ReadOnlyPressError('Fault injection is simulation-only on the real press')

    def set_pressure(self, bar: float) -> None:
        del bar
        raise ReadOnlyPressError('Air pressure is a field signal; the real adapter is read-only')

    def reset(self) -> None:
        raise ReadOnlyPressError(
            'Reset must be performed on the physical safety reset circuit after the fault is cleared'
        )


def create_press_source(env: Any = None, source: str | None = None):
    """Factory: PressSimulator by default, connected read-only S7 monitor for real mode."""
    env = os.environ if env is None else env
    mode_env = str(env.get('MODE', 'simulation')).strip().lower() or 'simulation'
    requested = source if source is not None else mode_env
    mode = str(requested).strip().lower()
    if mode not in ('simulation', 'real'):
        raise RealModeConfigurationError(f'source must be "simulation" or "real", got {requested!r}')
    if mode == 'simulation':
        from press_simulator import PressSimulator

        return PressSimulator()
    if mode_env != 'real':
        raise RealModeConfigurationError(
            'MODE=real must be set in the environment before the real source can be selected'
        )
    return ReadOnlyPressAdapter(env=env).connect()
