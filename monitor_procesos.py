# ============================================================
#  LexMonitor – Monitor de Procesos Rama Judicial Colombia
#  Consulta diaria de actuaciones y envío de reporte por email
# ============================================================

import requests
import json
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

# ── CONFIGURACIÓN ────────────────────────────────────────────
# Edita estos valores con tus datos

EMAIL_FROM = "lexmonitor26@gmail.com"          # Tu correo Gmail remitente
EMAIL_TO   = ["mariaalejandraavendanoquintero@gmail.com"]        # Lista de destinatarios
EMAIL_PASS = os.environ.get("EMAIL_PASS")   # Contraseña de aplicación (viene del secreto de GitHub)

ESTADO_FILE = "estado_procesos.json"        # Archivo donde se guarda el estado anterior

# Lista de radicados a monitorear (agrega o quita los tuyos)
RADICADOS = [
    "05308400300120220023800",
    "05308400300120220055500",
    # Agrega más radicados aquí...
]

# ── CONSULTA RAMA JUDICIAL ───────────────────────────────────

def consultar_proceso(radicado):
    """Consulta un radicado en la API de la Rama Judicial y retorna sus datos."""
    url = (
        f"https://consultaprocesos.ramajudicial.gov.co/api/v2/Proceso/Consulta"
        f"?numero={radicado}&SoloActivos=false&pagina=1"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://consultaprocesos.ramajudicial.gov.co/",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()

        procesos = data.get("procesos", [])
        if not procesos:
            print(f"  ⚠️  Radicado {radicado}: no encontrado en el sistema")
            return None

        p    = procesos[0]
        acts = p.get("actuaciones", [])
        ult  = acts[0] if acts else {}

        # Extraer sujetos procesales
        sujetos = p.get("sujetos", [])
        partes  = ", ".join(
            f"{s.get('nombresRazonSocial', '')} ({s.get('tipoSujeto', '')})"
            for s in sujetos[:4]  # máximo 4 para no inflar el correo
        ) or "—"

        return {
            "radicado":         radicado,
            "despacho":         p.get("despacho", "—"),
            "tipo_proceso":     p.get("tipoProceso", "—"),
            "clase_proceso":    p.get("claseProceso", "—"),
            "partes":           partes,
            "ultima_actuacion": ult.get("actuacion", "—"),
            "fecha":            ult.get("fechaActuacion", "—"),
            "anotacion":        ult.get("anotacion", "—"),
            "todas_actuaciones": acts[:5],  # guardamos las 5 más recientes
        }

    except requests.exceptions.Timeout:
        print(f"  ❌ Radicado {radicado}: timeout al conectar con Rama Judicial")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Radicado {radicado}: error de red – {e}")
        return None
    except Exception as e:
        print(f"  ❌ Radicado {radicado}: error inesperado – {e}")
        return None


# ── MANEJO DEL ESTADO ────────────────────────────────────────

def cargar_estado():
    """Carga el estado guardado del día anterior."""
    if Path(ESTADO_FILE).exists():
        with open(ESTADO_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_estado(estado):
    """Guarda el estado actual para comparar mañana."""
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)


# ── GENERACIÓN DEL CORREO ────────────────────────────────────

def generar_html(novedades, sin_cambio, errores):
    fecha = datetime.now().strftime("%d de %B de %Y")

    # Bloque de novedades
    bloques_novedades = ""
    for p in novedades:
        url_rama = f"https://consultaprocesos.ramajudicial.gov.co/Procesos/Index?numero={p['radicado']}"
        anotacion = (p["anotacion"] or "—")[:400]
        if len(p["anotacion"]) > 400:
            anotacion += "…"

        bloques_novedades += f"""
        <div style="border-left:4px solid #c94040; padding:14px 18px; margin:14px 0;
                    background:#fff8f8; border-radius:0 8px 8px 0;">
          <div style="font-size:12px; color:#c94040; font-weight:700;
                      text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">
            🔴 Novedad detectada
          </div>
          <div style="font-family:monospace; font-size:13px; color:#333; margin-bottom:4px;">
            <b>Radicado:</b> {p['radicado']}
          </div>
          <div style="font-size:13px; color:#333; margin-bottom:2px;">
            <b>Despacho:</b> {p['despacho']}
          </div>
          <div style="font-size:13px; color:#333; margin-bottom:2px;">
            <b>Tipo:</b> {p['tipo_proceso']} – {p['clase_proceso']}
          </div>
          <div style="font-size:13px; color:#333; margin-bottom:8px;">
            <b>Partes:</b> {p['partes']}
          </div>
          <div style="background:#fff; border:1px solid #f5b5b5; border-radius:6px;
                      padding:10px 14px; margin-top:8px;">
            <div style="font-size:12px; color:#888; margin-bottom:4px;">Última actuación</div>
            <div style="font-size:14px; font-weight:600; color:#1a1a2e;">{p['ultima_actuacion']}</div>
            <div style="font-size:12px; color:#888; margin-top:4px;">📅 {p['fecha']}</div>
            <div style="font-size:13px; color:#444; margin-top:8px; line-height:1.5;">{anotacion}</div>
          </div>
          <div style="margin-top:10px;">
            <a href="{url_rama}" style="color:#c94040; font-size:13px; font-weight:500;">
              → Ver proceso completo en Rama Judicial
            </a>
          </div>
        </div>"""

    # Bloque de sin cambios
    filas_sin_cambio = ""
    for rad in sin_cambio:
        filas_sin_cambio += f"""
        <tr>
          <td style="font-family:monospace; font-size:12px; padding:7px 12px;
                     border-bottom:1px solid #eee; color:#555;">{rad}</td>
          <td style="font-size:12px; padding:7px 12px;
                     border-bottom:1px solid #eee; color:#888;">Sin cambios</td>
        </tr>"""

    # Bloque de errores
    bloque_errores = ""
    if errores:
        lista_errores = "".join(f"<li style='font-family:monospace;font-size:12px'>{e}</li>" for e in errores)
        bloque_errores = f"""
        <div style="background:#fff9e6; border:1px solid #ffe082; border-radius:8px;
                    padding:14px 18px; margin-top:20px;">
          <b style="color:#8a6a00;">⚠️ No se pudieron consultar ({len(errores)}):</b>
          <ul style="margin-top:8px; padding-left:18px; color:#8a6a00;">{lista_errores}</ul>
        </div>"""

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
      <div style="max-width:620px; margin:0 auto; background:white; border-radius:12px;
                  overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.1);">

        <!-- HEADER -->
        <div style="background:#1a1a2e; padding:24px 28px;">
          <div style="font-size:22px; color:white; font-weight:700;">⚖️ LexMonitor</div>
          <div style="font-size:13px; color:#9999aa; margin-top:4px;">Reporte diario · {fecha}</div>
        </div>

        <!-- RESUMEN -->
        <div style="display:flex; gap:0; border-bottom:1px solid #eee;">
          <div style="flex:1; padding:16px 20px; text-align:center; border-right:1px solid #eee;">
            <div style="font-size:28px; font-weight:700; color:#c94040;">{len(novedades)}</div>
            <div style="font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Novedades</div>
          </div>
          <div style="flex:1; padding:16px 20px; text-align:center; border-right:1px solid #eee;">
            <div style="font-size:28px; font-weight:700; color:#2d6a4f;">{len(sin_cambio)}</div>
            <div style="font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Sin cambios</div>
          </div>
          <div style="flex:1; padding:16px 20px; text-align:center;">
            <div style="font-size:28px; font-weight:700; color:#1a1a2e;">{len(novedades)+len(sin_cambio)}</div>
            <div style="font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Total consultados</div>
          </div>
        </div>

        <!-- CUERPO -->
        <div style="padding:24px 28px;">

          {"<h3 style='color:#c94040; font-size:15px; margin-bottom:4px;'>🔴 Procesos con novedades</h3>" + bloques_novedades if novedades else
           "<div style='text-align:center; padding:20px; color:#888;'>✅ No hay novedades hoy. Todos los procesos están sin cambios.</div>"}

          {"<h3 style='color:#555; font-size:14px; margin-top:24px; margin-bottom:8px;'>📋 Sin cambios</h3><table style='width:100%; border-collapse:collapse;'>" + filas_sin_cambio + "</table>" if sin_cambio else ""}

          {bloque_errores}

        </div>

        <!-- FOOTER -->
        <div style="background:#f8f6f1; padding:14px 28px; border-top:1px solid #eee;">
          <p style="font-size:11px; color:#aaa; margin:0;">
            Generado automáticamente por LexMonitor · {datetime.now().strftime("%d/%m/%Y %H:%M")}
          </p>
        </div>

      </div>
    </body>
    </html>
    """
    return html


def enviar_email(novedades, sin_cambio, errores):
    """Envía el reporte por correo. Solo envía si hay novedades o errores."""
    if not novedades and not errores:
        print("✅ Sin novedades ni errores. No se envía correo hoy.")
        return

    fecha   = datetime.now().strftime("%d/%m/%Y")
    asunto  = f"[LexMonitor] {len(novedades)} novedad(es) · {fecha}" if novedades \
              else f"[LexMonitor] Sin novedades · {fecha}"

    html    = generar_html(novedades, sin_cambio, errores)
    msg     = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(EMAIL_TO)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"📬 Correo enviado a: {', '.join(EMAIL_TO)}")
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación. Verifica tu contraseña de aplicación.")
        raise
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        raise


# ── MAIN ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  LexMonitor · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")

    estado_anterior = cargar_estado()
    estado_nuevo    = {}
    novedades       = []
    sin_cambio      = []
    errores         = []

    for radicado in RADICADOS:
        print(f"Consultando {radicado}...")
        resultado = consultar_proceso(radicado)
        time.sleep(1)  # pausa para no sobrecargar el servidor

        if resultado is None:
            errores.append(radicado)
            continue

        estado_nuevo[radicado] = resultado
        anterior = estado_anterior.get(radicado, {})

        # Detectar cambio comparando la última actuación y su fecha
        hay_cambio = (
            resultado["ultima_actuacion"] != anterior.get("ultima_actuacion") or
            resultado["fecha"]            != anterior.get("fecha")
        )

        if hay_cambio:
            print(f"  🔴 NOVEDAD: {resultado['ultima_actuacion']} ({resultado['fecha']})")
            novedades.append(resultado)
        else:
            print(f"  ✅ Sin cambios: {resultado['ultima_actuacion']}")
            sin_cambio.append(radicado)

    print(f"\nResumen: {len(novedades)} novedades · {len(sin_cambio)} sin cambios · {len(errores)} errores\n")

    guardar_estado(estado_nuevo)
    enviar_email(novedades, sin_cambio, errores)

    print("\nListo ✓\n")
