// Estado compartido por los workers de Nginx, independiente para cada servicio.
const state = ngx.shared.circuits;

function blocked(r) {
    const key = r.variables.backend;
    const opened = state.get(key + ':opened');
    if (!opened) return '0';
    if (Date.now() - opened < 15000) return '1';
    if (!state.add(key + ':probe', 1, 15000)) return '1';
    r.variables.probing = '1';
    return '0';
}

function observe(r) {
    if (r.parent || !r.variables.circuit_target) return;
    const key = r.variables.circuit_target;
    const failed = r.variables.gateway_failure === '1' || /(?:^|[ ,:])(502|504)$/.test(r.variables.upstream_status);
    if (r.variables.probing === '1') {
        if (failed) state.set(key + ':opened', Date.now());
        else {
            state.delete(key + ':opened');
            state.delete(key + ':sequence');
            for (let i = 0; i < 5; i++) state.delete(key + ':failure' + i);
        }
        state.delete(key + ':probe');
    } else if (failed && !state.get(key + ':opened')) {
        const seq = state.incr(key + ':sequence', 1, 0);
        const slot = seq % 5;
        state.set(key + ':failure' + slot, Date.now(), 30000);
        if (state.get(key + ':failure' + ((slot + 1) % 5))) {
            state.add(key + ':opened', Date.now());
        }
    }
}

export default {blocked, observe};
