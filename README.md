# ⚖️ LexMonitor

Monitor automático de procesos judiciales de la **Rama Judicial de Colombia**.  
Consulta diariamente tus radicados y te envía un correo solo cuando hay novedades.

---

## Archivos del repositorio

```
lexmonitor/
├── monitor_procesos.py          ← Script principal
├── estado_procesos.json         ← Se crea automáticamente (no editar)
├── .github/
│   └── workflows/
│       └── monitor.yml          ← Automatización con GitHub Actions
└── README.md
```

---

## Configuración inicial

### 1. Edita `monitor_procesos.py`

Abre el archivo y ajusta estas líneas al inicio:

```python
EMAIL_FROM = "tu_correo@gmail.com"     # Tu correo remitente
EMAIL_TO   = ["tu_correo@gmail.com"]   # Destinatarios (puede ser más de uno)

RADICADOS = [
    "11001310302420220023100",
    "05001310501220230015600",
    # Agrega todos tus radicados aquí...
]
```

### 2. Crea una contraseña de aplicación en Gmail

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. **Seguridad → Verificación en dos pasos** (debe estar activa)
3. **Seguridad → Contraseñas de aplicaciones**
4. Crea una nueva contraseña → copia los 16 caracteres

### 3. Agrega el secreto en GitHub

1. Ve a tu repositorio → **Settings → Secrets and variables → Actions**
2. Clic en **New repository secret**
3. Nombre: `EMAIL_PASS`
4. Valor: la contraseña de 16 caracteres del paso anterior

---

## Ejecución manual (prueba local)

```bash
pip install requests

# En Windows / Mac / Linux:
export EMAIL_PASS="xxxx xxxx xxxx xxxx"
python monitor_procesos.py
```

En Windows CMD:
```cmd
set EMAIL_PASS=xxxx xxxx xxxx xxxx
python monitor_procesos.py
```

---

## Automatización con GitHub Actions

El archivo `.github/workflows/monitor.yml` ya está configurado para ejecutarse **lunes a viernes a las 7:30am (hora Colombia)**.

Para cambiar la hora, edita la línea `cron` en el workflow.  
El formato es: `"minuto hora * * días"` en hora **UTC** (Colombia = UTC-5).

| Hora Colombia | Hora UTC (cron)     |
|---------------|---------------------|
| 6:00am        | `"0 11 * * 1-5"`    |
| 7:30am        | `"30 12 * * 1-5"`   |
| 8:00am        | `"0 13 * * 1-5"`    |

Para ejecutar manualmente: **Actions → Monitor Procesos Judiciales → Run workflow**

---

## ¿Cuándo envía correo?

- ✅ **Envía** si hay al menos un proceso con novedad o un error de consulta
- 🔕 **No envía** si todos los procesos están sin cambios (para no saturar tu bandeja)
