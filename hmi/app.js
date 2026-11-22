const $ = (id) => document.getElementById(id);
let b1 = false;
let b2 = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return response.json();
}

function render(state) {
  $('state').textContent = state.StateName;
  $('state').className = `state state-${state.State}`;
  $('fault').textContent = state.FaultName;
  $('fault').className = state.FaultCode ? 'fault alarm' : 'fault ok';
  $('clampPos').textContent = `${state.ClampPosition} mm`;
  $('pressPos').textContent = `${state.PressPosition} mm`;
  $('clampBar').style.width = `${state.ClampPosition}%`;
  $('pressBar').style.width = `${state.PressPosition}%`;
  $('cycles').textContent = state.CycleCount;
  $('pressure').textContent = `${state.Pressure_bar} bar`;
  const valves = [state.ClampValve ? 'Y1' : '', state.PressValve ? 'Y2' : '', state.RetractValve ? 'Y3' : ''].filter(Boolean);
  $('valves').textContent = valves.join(' ') || '—';
  $('feedback').textContent = state.PressHome ? 'HOME' : state.PressExtended ? 'PRESS END' : 'IN MOTION';
  $('b1').className = state.Button1 ? 'hand active' : 'hand';
  $('b2').className = state.Button2 ? 'hand active' : 'hand';
  $('pressureInput').value = state.Pressure_bar;
}

async function refresh() {
  render(await api('/api/state'));
}

async function setButtons() {
  render(await api('/api/buttons', { method: 'POST', body: { button1: b1, button2: b2 } }));
}

function bindHand(id, setter) {
  const element = $(id);
  const down = (event) => { event.preventDefault(); setter(true); setButtons(); };
  const up = (event) => { event.preventDefault(); setter(false); setButtons(); };
  element.onmousedown = down;
  element.onmouseup = up;
  element.onmouseleave = up;
  element.ontouchstart = down;
  element.ontouchend = up;
}

bindHand('b1', (value) => { b1 = value; });
bindHand('b2', (value) => { b2 = value; });

const toggleFault = (fault) => api('/api/state').then((state) => {
  const active = fault === 'estop' ? !state.EStopOK
    : fault === 'guard' ? !state.GuardClosed
      : fault === 'relay' ? !state.SafetyOK
        : state.PressureOK;
  return api('/api/fault', { method: 'POST', body: { fault, active } });
}).then(render);

$('estop').onclick = () => toggleFault('estop');
$('guard').onclick = () => toggleFault('guard');
$('relay').onclick = () => toggleFault('relay');
$('lowPressure').onclick = () => toggleFault('pressure');
$('reset').onclick = () => api('/api/reset', { method: 'POST', body: {} }).then(render);
$('pressureInput').oninput = (event) => api('/api/pressure', { method: 'POST', body: { bar: Number(event.target.value) } }).then(render);

refresh();
setInterval(refresh, 200);
