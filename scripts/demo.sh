#!/usr/bin/env bash
# Demostración obligatoria (PDF p. 5; 05 W-11A/W-11B; 06 §7) con dos procesos reales.
#
# Uso (desde la raíz del repositorio, Linux o Windows con Git Bash):
#   bash scripts/demo.sh ["descripción de la máquina"]
#
# Arranca el Controller (F-01) y el Router en puertos no predeterminados, ejecuta los pasos a–e
# y guarda en demo-evidence/ un archivo .txt por paso con la fecha, cada comando y su salida literal.
# Variables opcionales: CONTROLLER_PORT_DEMO (8100), ROUTER_PORT_DEMO (8101), SILENT_PORT_DEMO (8109),
# ROUTER2_PORT_DEMO (8102), PYTHON (intérprete).
set -u
cd "$(dirname "$0")/.."

MACHINE="${1:-no indicada}"
C_PORT="${CONTROLLER_PORT_DEMO:-8100}"
R_PORT="${ROUTER_PORT_DEMO:-8101}"
R2_PORT="${ROUTER2_PORT_DEMO:-8102}"
S_PORT="${SILENT_PORT_DEMO:-8109}"
OUT="demo-evidence"
LOG_FILE="data/demo-forwarding.jsonl"

if [ -n "${PYTHON:-}" ]; then PY="$PYTHON"
elif [ -x .venv/Scripts/python.exe ]; then PY=".venv/Scripts/python.exe"   # Windows (Git Bash)
elif [ -x .venv/bin/python ]; then PY=".venv/bin/python"                    # Linux / macOS
else PY="python"; fi

C_URL="http://127.0.0.1:$C_PORT"
R_URL="http://127.0.0.1:$R_PORT"
mkdir -p "$OUT" data
rm -f "$LOG_FILE"
PIDS=()
cleanup() { for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null; done; }
trap cleanup EXIT

now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
CURRENT=""
step() {  # step <archivo> <título>
  CURRENT="$OUT/$1"
  { echo "# $2"; echo "Fecha (UTC): $(now)"; echo "Máquina: $MACHINE"
    echo "Atajos: http = curl --noproxy '*' -s -S -w '\\nHTTP %{http_code}\\n'"
    echo "        packet ID = http -X POST \$R_URL/packets -H 'Content-Type: application/json' -d '{\"packet_id\": \"ID\", \"source\": \"A\", \"destination\": \"D\", \"metric\": \"delay\", \"payload\": \"demo\"}'"
    echo "        R_URL=$R_URL  C_URL=$C_URL"; echo; } > "$CURRENT"
  echo "== $2"
}
run() {  # run <comando...>: escribe el comando y su salida literal en el archivo del paso
  { echo "\$ $*"; "$@" 2>&1; echo; echo; } | tee -a "$CURRENT"
}
note() { echo "## $*" | tee -a "$CURRENT"; }
http() { curl --noproxy '*' -s -S -w '\nHTTP %{http_code}\n' "$@"; }
wait_health() {
  for _ in $(seq 1 100); do
    curl --noproxy '*' -s -o /dev/null "$1/health" && return 0
    sleep 0.2
  done
  echo "ERROR: $1 no respondió" >&2; return 1
}
packet() {  # packet <packet_id>
  http -X POST "$R_URL/packets" -H 'Content-Type: application/json' \
    -d "{\"packet_id\": \"$1\", \"source\": \"A\", \"destination\": \"D\", \"metric\": \"delay\", \"payload\": \"demo\"}"
}

# --- 0. Arranque de ambos procesos -----------------------------------------------------------
step "00-arranque.txt" "Paso 0 — Arranque del Controller y del Router en puertos no predeterminados"
note "Controller: $PY -m controller.main --port $C_PORT --topology specs/fixtures/F-01.json"
"$PY" -m controller.main --port "$C_PORT" --topology specs/fixtures/F-01.json > "$OUT/controller-process.log" 2>&1 &
C_PID=$!; PIDS+=("$C_PID")
note "Router: $PY -m router.main --port $R_PORT --controller-url $C_URL --log-file $LOG_FILE"
"$PY" -m router.main --port "$R_PORT" --controller-url "$C_URL" --log-file "$LOG_FILE" > "$OUT/router-process.log" 2>&1 &
R_PID=$!; PIDS+=("$R_PID")
wait_health "$C_URL" && wait_health "$R_URL"
run http "$C_URL/health"
run http "$R_URL/health"
run http "$C_URL/topology"

# --- a. Paquete: ruta emitida por el Controller y traza devuelta por el Router ----------------
step "a-paquete-ruta-traza.txt" "Paso a — Paquete reenviado: ruta del Controller y traza del Router"
run http "$C_URL/route?src=A&dst=D&metric=delay"
run packet "pkt-a1"

# --- b. Fallo de un enlace de la ruta y nueva ruta ----------------------------------------------
step "b-fallo-enlace.txt" "Paso b — Fallo de B→D (enlace de la ruta): nueva ruta con versión 2"
run http -X POST "$C_URL/links/fail" -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
run packet "pkt-b1"

# --- c. Restauración y repetición ---------------------------------------------------------------
step "c-restauracion.txt" "Paso c — Restauración de B→D (versión 3), repetición idempotente y nueva consulta"
run http -X POST "$C_URL/links/restore" -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
run http -X POST "$C_URL/links/restore" -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
run packet "pkt-c1"
run http "$C_URL/topology"

# --- c2. Destino inalcanzable y recuperación ----------------------------------------------------
step "c2-destino-inalcanzable.txt" "Paso c2 — Fallo de B→D y C→D: destino inalcanzable (404); restauración de ambos"
run http -X POST "$C_URL/links/fail" -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
run http -X POST "$C_URL/links/fail" -H 'Content-Type: application/json' -d '{"source": "C", "target": "D"}'
run packet "pkt-c2"
run http -X POST "$C_URL/links/restore" -H 'Content-Type: application/json' -d '{"source": "C", "target": "D"}'
run http -X POST "$C_URL/links/restore" -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
run packet "pkt-c3"

# --- d. Controller detenido (503) y timeout simulado (504) --------------------------------------
step "d-controller-caido-timeout.txt" "Paso d — Controller detenido (503) y Controller que no responde (504)"
note "Se detiene el proceso Controller (PID $C_PID)"
kill "$C_PID"; wait "$C_PID" 2>/dev/null
run packet "pkt-d1"
run http "$R_URL/health"
note "Servidor de prueba en 127.0.0.1:$S_PORT que acepta la conexión y nunca responde"
"$PY" -c "import socket,time;s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',$S_PORT));s.listen();c=[s.accept() for _ in range(5)];time.sleep(60)" &
S_PID=$!; PIDS+=("$S_PID")
note "Router 2: $PY -m router.main --port $R2_PORT --controller-url http://127.0.0.1:$S_PORT --log-file $LOG_FILE --read-timeout 0.5"
"$PY" -m router.main --port "$R2_PORT" --controller-url "http://127.0.0.1:$S_PORT" --log-file "$LOG_FILE" --read-timeout 0.5 > "$OUT/router2-process.log" 2>&1 &
R2_PID=$!; PIDS+=("$R2_PID")
wait_health "http://127.0.0.1:$R2_PORT"
run http -X POST "http://127.0.0.1:$R2_PORT/packets" -H 'Content-Type: application/json' \
  -d '{"packet_id": "pkt-d2", "source": "A", "destination": "D", "metric": "delay"}'
run http "http://127.0.0.1:$R2_PORT/health"

# --- e. Bitácora JSONL ------------------------------------------------------------------------
step "e-bitacora-jsonl.txt" "Paso e — Bitácora JSONL resultante ($LOG_FILE)"
run cat "$LOG_FILE"
run wc -l "$LOG_FILE"

cleanup
sleep 1
step "f-registro-accesos-controller.txt" "Registro de accesos del Controller (TC-05, parte 3: un GET /route por paquete)"
note "Cada paquete que llega al Controller produce exactamente un GET /route desde el puerto del Router;"
note "la primera línea GET /route es la consulta directa del paso a (curl)."
run cat "$OUT/controller-process.log"
echo "Evidencias en $OUT/"
