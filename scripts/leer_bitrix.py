"""Lee de Bitrix24 las tareas cuyo nombre contiene "planilla" y las guarda en tareas.json.

Solo lectura: usa tasks.task.list y nunca crea ni modifica nada en Bitrix24.
La URL del webhook llega en la variable de entorno BITRIX_WEBHOOK (secreto de GitHub).
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

ESTADOS = {
    "1": "Nueva", "2": "Pendiente", "3": "En curso", "4": "Pendiente de control",
    "5": "Completada", "6": "Aplazada", "7": "Rechazada",
}
CAMPOS = ["ID", "TITLE", "STATUS", "RESPONSIBLE_ID", "GROUP_ID", "START_DATE_PLAN",
          "DATE_START", "DEADLINE", "CLOSED_DATE", "CREATED_DATE", "PARENT_ID"]


def fallar(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def llamar(base, metodo, params):
    req = urllib.request.Request(
        f"{base}/{metodo}.json",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cuerpo = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        fallar(f"Bitrix24 respondió {e.code}. Revisa que el secreto BITRIX_WEBHOOK sea la URL del webhook entrante (con /rest/, sin barra final).")
    except urllib.error.URLError as e:
        fallar(f"No se pudo conectar con Bitrix24: {e.reason}")
    if cuerpo.lstrip().startswith("<"):
        fallar("Bitrix24 devolvió una página web en vez de datos: la URL del secreto BITRIX_WEBHOOK no es la del webhook entrante.")
    datos = json.loads(cuerpo)
    if "error" in datos:
        fallar(f"Bitrix24: {datos.get('error_description') or datos['error']}")
    return datos


def main():
    crudo = os.environ.get("BITRIX_WEBHOOK", "").strip()
    if not crudo:
        fallar("Falta el secreto BITRIX_WEBHOOK en el repositorio.")
    # Acepta la URL aunque traiga un método de ejemplo al final (p. ej. /profile/ o /user.current.json):
    # se queda solo con https://portal/rest/<usuario>/<código>.
    m = re.match(r"^(https?://[^/\s]+/rest/\d+/[A-Za-z0-9]+)", crudo)
    if not m:
        u = urlparse(crudo)
        partes = [p for p in u.path.split("/") if p]
        fallar(
            "El secreto BITRIX_WEBHOOK no tiene la forma https://<portal>/rest/<número>/<código>. "
            f"Se recibió una dirección de {u.netloc or '(sin dominio)'} con {len(partes)} partes en la ruta"
            f"{' y sin /rest/' if 'rest' not in partes else ''}."
        )
    base = m.group(1)
    portal = "{0.scheme}://{0.netloc}".format(urlparse(base))

    tareas, inicio, total = [], 0, None
    while True:
        d = llamar(base, "tasks.task.list", {
            "filter": {"%TITLE": "planilla"}, "select": CAMPOS,
            "order": {"DEADLINE": "asc"}, "start": inicio,
        })
        tareas += d["result"]["tasks"]
        total = d.get("total", len(tareas))
        if "next" not in d:
            break
        inicio = d["next"]
        time.sleep(0.6)  # bajo el límite de 2 consultas por segundo

    if len(tareas) != total:
        fallar(f"Se leyeron {len(tareas)} tareas pero Bitrix24 informa {total}.")

    filas = []
    for t in tareas:
        g = t.get("group") or {}
        r = t.get("responsible") or {}
        filas.append({
            "id": str(t["id"]),
            "tarea": t.get("title") or "",
            "proyecto": re.sub(r"\s+", " ", g.get("name") or "").strip() or "Sin proyecto",
            "responsable": r.get("name") or "Sin responsable",
            "estado_codigo": str(t.get("status")),
            "estado": ESTADOS.get(str(t.get("status")), str(t.get("status"))),
            "inicio_real": t.get("dateStart") or t.get("startDatePlan"),
            "creada": t.get("createdDate"),
            "limite": t.get("deadline"),
            "cierre": t.get("closedDate"),
            "url": f"{portal}/company/personal/user/{t.get('responsibleId')}/tasks/task/view/{t['id']}/",
        })

    with open("tareas.json", "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    with open("ultima_lectura.json", "w", encoding="utf-8") as f:
        json.dump({"leido": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "total": len(filas)}, f)
    print(f"OK: {len(filas)} tareas guardadas en tareas.json")


if __name__ == "__main__":
    main()
