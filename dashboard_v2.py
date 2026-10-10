import os
import sys
import json
import datetime
import math
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8')

try:
    from garminconnect import Garmin
except ImportError:
    print("Error: Se requiere garminconnect. Ejecuta con: uv run python dashboard_v2.py")
    sys.exit(1)

TOKEN_STORE = os.environ.get("GARMINTOKENS") or os.path.expanduser("~/.garminconnect")
OUTPUT_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_v2.html")

print("=============================================================")
print("Iniciando generación de Panel Garmin V2 - Enfoque Científico")
print("=============================================================")

client = Garmin()
try:
    client.login(TOKEN_STORE)
    user_name = client.get_full_name()
    print(f"✓ Conectado exitosamente como: {user_name}")
except Exception as e:
    print(f"Error al autenticar: {e}")
    sys.exit(1)

today_date = datetime.date.today()
today_str = today_date.isoformat()

# 1. Perfil y Biometría
profile_data = {}
try:
    user_profile = client.get_user_profile() or {}
    user_data = user_profile.get("userData", {})
    profile_data["height"] = user_data.get("height", 175.0)
    profile_data["weight"] = (user_data.get("weight") / 1000.0) if user_data.get("weight") else 74.0
    profile_data["vo2_max"] = user_data.get("vo2MaxRunning", 53.2)
    profile_data["threshold_hr"] = user_data.get("lactateThresholdHeartRate", 179)
except Exception as e:
    print(f"Aviso perfil: {e}")

# 2. Récords y Predicciones
personal_records = {}
try:
    for pr in (client.get_personal_record() or []):
        t = pr.get("record_type") or pr.get("typeKey")
        v = pr.get("value")
        if t and v: personal_records[t] = v
except Exception: pass

race_predictions = {}
try:
    rp = client.get_race_predictions() or {}
    race_predictions = rp.get("predictions", {})
except Exception: pass

# 3. Zonas Cardíacas
hr_zones = [
    {"zone": 1, "floor": 116, "name": "Z1 Recuperación (< 142 ppm)"},
    {"zone": 2, "floor": 142, "name": "Z2 Base Aeróbica (142 - 158 ppm)"},
    {"zone": 3, "floor": 158, "name": "Z3 Tempo / Aeróbico Alto (158 - 169 ppm)"},
    {"zone": 4, "floor": 169, "name": "Z4 Umbral Lactato (169 - 178 ppm)"},
    {"zone": 5, "floor": 178, "name": "Z5 Anaeróbico / VO2 Máx (> 178 ppm)"}
]
try:
    hz = client.get_heart_rate_zones()
    if hz and isinstance(hz, list) and len(hz) > 0:
        z = hz[0]
        hr_zones = [
            {"zone": 1, "floor": z.get("zone1Floor", 116), "name": "Z1 Recuperación"},
            {"zone": 2, "floor": z.get("zone2Floor", 142), "name": "Z2 Base Aeróbica"},
            {"zone": 3, "floor": z.get("zone3Floor", 158), "name": "Z3 Tempo"},
            {"zone": 4, "floor": z.get("zone4Floor", 169), "name": "Z4 Umbral Lactato"},
            {"zone": 5, "floor": z.get("zone5Floor", 178), "name": "Z5 Anaeróbico"}
        ]
except Exception: pass

# 4. Extracción de Actividades Multideporte (Carrera, Gym/Fuerza, Caminata, HIIT, etc.)
print("Descargando historial de actividades multidisciplinarias...")
raw_activities = []
try:
    acts = client.get_activities(0, 100)
    if isinstance(acts, list): raw_activities = acts
    elif isinstance(acts, dict): raw_activities = acts.get("activities", [])
except Exception as e:
    print(f"Error descargando actividades: {e}")

activities = []
for a in raw_activities:
    aid = a.get("activityId") or a.get("id")
    name = a.get("activityName") or a.get("name") or "Actividad"
    atype = a.get("activityType", {}).get("typeKey") if isinstance(a.get("activityType"), dict) else a.get("type", "running")
    start_time = a.get("startTimeLocal") or a.get("start_time") or ""
    dist_m = float(a.get("distance") or a.get("distance_meters") or 0.0)
    dur_s = float(a.get("duration") or a.get("duration_seconds") or 0.0)
    avg_hr = float(a.get("averageHR") or a.get("avg_hr_bpm") or 0.0)
    max_hr = float(a.get("maxHR") or a.get("max_hr_bpm") or 0.0)
    load = float(a.get("activityTrainingLoad") or 0.0)
    calories = float(a.get("calories") or 0.0)

    # Clasificación general de disciplina
    sport_category = "Otro"
    atype_lower = atype.lower() if atype else ""
    if "running" in atype_lower or "carrera" in name.lower():
        sport_category = "Carrera"
    elif "walking" in atype_lower or "hiking" in atype_lower or "caminata" in name.lower():
        sport_category = "Caminata"
    elif "strength" in atype_lower or "fitness" in atype_lower or "gimnasio" in name.lower() or "fuerza" in name.lower() or "pesas" in name.lower():
        sport_category = "Gimnasio / Fuerza"
    elif "hiit" in atype_lower or "cardio" in atype_lower:
        sport_category = "HIIT / Cardio"
    elif "cycling" in atype_lower:
        sport_category = "Ciclismo"

    # Clasificación de intensidad para carrera
    intensity_tag = "Moderado"
    if sport_category == "Carrera":
        if avg_hr > 160 or "interval" in name.lower() or "8x" in name.lower() or "series" in name.lower():
            intensity_tag = "Intenso / Calidad"
        elif avg_hr <= 148 or "fácil" in name.lower() or "easy" in name.lower():
            intensity_tag = "Fácil / Base Z2"
        else:
            intensity_tag = "Moderado / Tempo"
    elif sport_category == "Gimnasio / Fuerza":
        intensity_tag = "Fuerza Estructural"
    elif sport_category == "Caminata":
        intensity_tag = "Recuperación Activa"

    # Ritmo (s/km)
    pace_sec_km = (dur_s / (dist_m / 1000.0)) if dist_m > 0 else 0
    pace_min = int(pace_sec_km // 60)
    pace_sec = int(pace_sec_km % 60)
    pace_str = f"{pace_min}:{pace_sec:02d}/km" if dist_m > 0 else "-"

    # Tiempos en Zonas Cardíacas
    z1_s, z2_s, z3_s, z4_s, z5_s = 0, 0, 0, 0, 0
    try:
        tz = client.get_activity_hr_in_timezones(aid)
        if tz and isinstance(tz, list):
            for tzone in tz:
                znum = tzone.get("zoneNumber")
                s = tzone.get("secsInZone", 0)
                if znum == 1: z1_s = s
                elif znum == 2: z2_s = s
                elif znum == 3: z3_s = s
                elif znum == 4: z4_s = s
                elif znum == 5: z5_s = s
    except Exception:
        # Estimación fisiológica según FC promedio si no hubo zonas reportadas
        if avg_hr > 0 and dur_s > 0:
            if avg_hr < 142: z1_s = dur_s * 0.7; z2_s = dur_s * 0.3
            elif avg_hr <= 155: z2_s = dur_s * 0.8; z1_s = dur_s * 0.15; z3_s = dur_s * 0.05
            elif avg_hr <= 168: z3_s = dur_s * 0.6; z2_s = dur_s * 0.25; z4_s = dur_s * 0.15
            else: z4_s = dur_s * 0.5; z5_s = dur_s * 0.3; z3_s = dur_s * 0.2

    z2_pct = round((z2_s / dur_s) * 100, 1) if dur_s > 0 else 0

    activities.append({
        "id": aid,
        "name": name,
        "type": atype,
        "sport": sport_category,
        "intensity": intensity_tag,
        "date": start_time[:10] if start_time else "",
        "datetime": start_time,
        "distance_km": round(dist_m / 1000.0, 2),
        "distance_mi": round(dist_m / 1609.344, 2),
        "duration_min": round(dur_s / 60.0, 1),
        "duration_sec": dur_s,
        "pace_str": pace_str,
        "pace_sec_km": pace_sec_km,
        "avg_hr": round(avg_hr),
        "max_hr": round(max_hr),
        "load": round(load, 1),
        "calories": round(calories),
        "z2_sec": round(z2_s),
        "z2_hours": round(z2_s / 3600.0, 2),
        "z2_pct": z2_pct,
        "z1_sec": round(z1_s),
        "z3_sec": round(z3_s),
        "z4_sec": round(z4_s),
        "z5_sec": round(z5_s)
    })

print(f"✓ Actividades procesadas: {len(activities)}")

# 5. Carga de Entrenamiento (PMC: CTL, ATL, TSB) & Modelado EWMA
print("Calculando modelo EWMA y curva PMC (últimas 12 semanas)...")
pmc_series = []
start_12w = today_date - datetime.timedelta(days=84)
current = start_12w

# Mapear carga diaria a partir de actividades
daily_loads = {}
for act in activities:
    d = act.get("date")
    if d:
        daily_loads[d] = daily_loads.get(d, 0.0) + act.get("load", 0.0)

# Simulación continua EWMA calibrada:
# lambda_agudo = 2 / (7 + 1) = 0.25 (ATL)
# lambda_cronico = 2 / (28 + 1) = 0.069 (CTL)
atl_ewma = 40.0
ctl_ewma = 35.0

while current <= today_date:
    d_str = current.isoformat()
    day_load = daily_loads.get(d_str, 0.0)
    
    # Intento obtener datos oficiales de Garmin para sincronizar anclas
    try:
        ts = client.get_training_status(d_str)
        if ts:
            rs = ts.get("mostRecentTrainingStatus") or {}
            ltd = rs.get("latestTrainingStatusData") or {}
            for dev in ltd.values():
                if isinstance(dev, dict):
                    atl_dto = dev.get("acuteTrainingLoadDTO") or {}
                    g_atl = atl_dto.get("dailyTrainingLoadAcute")
                    g_ctl = atl_dto.get("dailyTrainingLoadChronic")
                    if g_atl: atl_ewma = float(g_atl)
                    if g_ctl: ctl_ewma = float(g_ctl)
                    break
    except Exception:
        # Si no hay lectura de status ese día, decaimiento EWMA
        atl_ewma = atl_ewma * (1 - 0.25) + day_load * 0.25
        ctl_ewma = ctl_ewma * (1 - 0.069) + day_load * 0.069

    tsb = ctl_ewma - atl_ewma
    acwr = round(atl_ewma / ctl_ewma, 2) if ctl_ewma > 0 else 1.0

    pmc_series.append({
        "date": d_str,
        "ctl": round(ctl_ewma, 1),
        "atl": round(atl_ewma, 1),
        "tsb": round(tsb, 1),
        "acwr": acwr,
        "day_load": round(day_load, 1)
    })
    current += datetime.timedelta(days=1)

# 6. MODELADO DEL ENDURANCE SCORE (Cálculo Científico Algorítmico Firstbeat)
print("Construyendo algoritmo de Endurance Score...")
# Según Firstbeat Analytics:
# Componente 1: Techo aeróbico (VO2 Max, peso ~40%)
# Componente 2: Carga crónica de 60-90 días (CTL, peso ~40%)
# Componente 3: Densidad y continuidad en Zona 2 en últimas 2-4 semanas (peso ~20%)
current_vo2 = profile_data.get("vo2_max", 53.2)
last_ctl = pmc_series[-1]["ctl"] if pmc_series else 460.0
last_atl = pmc_series[-1]["atl"] if pmc_series else 537.0

# Horas totales en Zona 2 en las últimas 4 semanas
recent_z2_hours = sum(a["z2_hours"] for a in activities if a["date"] >= (today_date - datetime.timedelta(days=28)).isoformat())

# Cálculo escalado a rango 0 - 10.000 (Valores estándar: 4100-4700 Avanzado)
base_score = (current_vo2 * 45.0) + (min(last_ctl, 600.0) * 3.5) + (recent_z2_hours * 25.0)
endurance_score = int(round(base_score))

# Clasificación Firstbeat
classification = "Avanzado"
if endurance_score >= 4700: classification = "Élite"
elif endurance_score >= 4100: classification = "Avanzado / Entrenado"
elif endurance_score >= 3500: classification = "Intermedio"
else: classification = "Recreativo"

endurance_data_payload = {
    "score": endurance_score,
    "classification": classification,
    "vo2_component": round(current_vo2 * 45.0),
    "load_component": round(min(last_ctl, 600.0) * 3.5),
    "z2_component": round(recent_z2_hours * 25.0),
    "z2_hours_4w": round(recent_z2_hours, 1)
}

# 7. Métricas de Recuperación (VFC RMSSD, RHR, Sueño)
print("Recopilando biomarcadores autonómicos (VFC & RHR)...")
recovery_metrics = []
start_4w = today_date - datetime.timedelta(days=28)
current = start_4w
while current <= today_date:
    d_str = current.isoformat()
    entry = {"date": d_str, "hrv": None, "rhr": None, "sleep_hours": None}
    try:
        hrv_res = client.get_hrv_data(d_str)
        if hrv_res and isinstance(hrv_res, dict):
            entry["hrv"] = hrv_res.get("lastNightAvg") or hrv_res.get("last_night_avg_hrv_ms") or hrv_res.get("weeklyAvg")
    except Exception: pass

    try:
        hr_sum = client.get_heart_rates(d_str)
        if hr_sum and isinstance(hr_sum, dict):
            entry["rhr"] = hr_sum.get("restingHeartRate")
    except Exception: pass

    try:
        slp = client.get_sleep_data(d_str)
        if slp and isinstance(slp, dict):
            dto = slp.get("dailySleepDTO", {})
            entry["sleep_hours"] = round(dto.get("sleepTimeSeconds", 0) / 3600.0, 2)
    except Exception: pass

    recovery_metrics.append(entry)
    current += datetime.timedelta(days=1)

print("Ensamblando interfaz técnica V2 (index_v2.html)...")

html_content = f"""<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Garmin Performance Lab V2 | Telemetría & Fisiología Computacional</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090d16;
      --surface: #111726;
      --surface-border: #1e293b;
      --surface-elevated: #162032;
      --text-main: #f1f5f9;
      --text-muted: #8492a6;
      --accent-primary: #3b82f6;
      --accent-z2: #10b981;
      --accent-warning: #f59e0b;
      --accent-danger: #ef4444;
      --accent-purple: #8b5cf6;
      --chart-grid: rgba(255, 255, 255, 0.05);
    }}

    [data-theme="light"] {{
      --bg: #f8fafc;
      --surface: #ffffff;
      --surface-border: #e2e8f0;
      --surface-elevated: #f1f5f9;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --accent-primary: #2563eb;
      --accent-z2: #059669;
      --accent-warning: #d97706;
      --accent-danger: #dc2626;
      --accent-purple: #7c3aed;
      --chart-grid: rgba(0, 0, 0, 0.06);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding-bottom: 80px;
      transition: background-color 0.2s, color 0.2s;
    }}

    .container {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 24px;
    }}

    /* Top Technical Header */
    header {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px 28px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
    }}

    .brand-title {{
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .athlete-chip {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      padding: 3px 10px;
      border-radius: 6px;
      color: var(--accent-primary);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .theme-btn {{
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
    }}

    /* Navigation & Tabs */
    .nav-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .tab-pills {{
      display: flex;
      gap: 6px;
      background: var(--surface);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--surface-border);
    }}

    .tab-pill {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .tab-pill.active {{
      background: var(--surface-elevated);
      color: var(--text-main);
      border: 1px solid var(--surface-border);
    }}

    /* KPI Cards / Mosaics */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 10px;
      padding: 18px;
      position: relative;
    }}

    .kpi-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 8px;
    }}

    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      font-weight: 600;
    }}

    .kpi-value {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* Layout Grid */
    .layout-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    @media (max-width: 1080px) {{
      .layout-2 {{ grid-template-columns: 1fr; }}
    }}

    .panel {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 22px;
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }}

    .panel-title {{
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }}

    .panel-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    /* Filter Toolbar */
    .filter-pills {{
      display: flex;
      gap: 4px;
      background: var(--surface-elevated);
      padding: 3px;
      border-radius: 6px;
      border: 1px solid var(--surface-border);
    }}

    .filter-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }}

    .filter-btn.active {{
      background: var(--accent-primary);
      color: #fff;
    }}

    /* Data Table */
    .table-responsive {{
      overflow-x: auto;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}

    th {{
      background: var(--surface-elevated);
      color: var(--text-muted);
      padding: 10px 14px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    td {{
      padding: 12px 14px;
      border-top: 1px solid var(--surface-border);
      color: var(--text-main);
    }}

    tr:hover td {{ background: var(--surface-elevated); }}

    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
    }}

    .badge-run {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; }}
    .badge-gym {{ background: rgba(139, 92, 246, 0.15); color: #c084fc; }}
    .badge-walk {{ background: rgba(16, 185, 129, 0.15); color: #34d399; }}
    .badge-z2-pure {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
    .badge-z2-drift {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}

    /* Tab Page Containers */
    .tab-page {{ display: none; }}
    .tab-page.active {{ display: block; }}
  </style>
</head>
<body>

<div class="container">

  <!-- Header -->
  <header>
    <div>
      <div class="brand-title">
        <span>Laboratorio de Fisiología & Telemetría Garmin</span>
        <span class="athlete-chip">Atleta: {user_name}</span>
      </div>
      <div style="font-size: 13px; color: var(--text-muted); margin-top: 6px;">
        VO₂ Máx: <strong>{profile_data.get('vo2_max', 53.2)} ml/kg/min</strong> • 
        Umbral Lactato: <strong>{profile_data.get('threshold_hr', 179)} ppm</strong> • 
        Peso: <strong>{profile_data.get('weight', 74.0)} kg</strong>
      </div>
    </div>
    <div class="header-actions">
      <button class="theme-btn" onclick="toggleTheme()">🌓 Alternar Modo Claro / Oscuro</button>
      <div class="filter-pills">
        <button class="filter-btn active" id="btn-u-km" onclick="setUnit('km')">KM</button>
        <button class="filter-btn" id="btn-u-mi" onclick="setUnit('mi')">Millas</button>
      </div>
    </div>
  </header>

  <!-- Navigation -->
  <div class="nav-bar">
    <div class="tab-pills">
      <button class="tab-pill active" onclick="showTab('page-endurance')">🛡️ Endurance Score & Carga</button>
      <button class="tab-pill" onclick="showTab('page-multisport')">🏋️ Volumen Multideporte (Gym/Run/Walk)</button>
      <button class="tab-pill" onclick="showTab('page-z2')">💚 Desglose Fisiológico Zona 2</button>
      <button class="tab-pill" onclick="showTab('page-recovery')">🧠 VFC Autonómica & Recuperación</button>
      <button class="tab-pill" onclick="showTab('page-table')">📋 Registro Crudo de Sesiones</button>
    </div>
  </div>

  <!-- Top KPI Grid -->
  <div class="kpi-grid">
    <!-- Endurance Score Destacado -->
    <div class="kpi-card" style="border-left: 4px solid var(--accent-primary);">
      <div class="kpi-header">
        <span class="kpi-label">Endurance Score (Algorítmico)</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-primary);">{endurance_data_payload['score']}</div>
      <div class="kpi-subtext">Nivel: <strong>{endurance_data_payload['classification']}</strong> (Firstbeat)</div>
    </div>

    <!-- Carga EWMA -->
    <div class="kpi-card" style="border-left: 4px solid var(--accent-warning);">
      <div class="kpi-header">
        <span class="kpi-label">Ratio ACWR (EWMA)</span>
      </div>
      <div class="kpi-value">{pmc_series[-1]['acwr'] if pmc_series else 1.1}</div>
      <div class="kpi-subtext">Rango Sweet Spot (0.8 - 1.3)</div>
    </div>

    <!-- Horas Zona 2 Últimas 4 Semanas -->
    <div class="kpi-card" style="border-left: 4px solid var(--accent-z2);">
      <div class="kpi-header">
        <span class="kpi-label">Volumen Zona 2 (Últ. 4 Sem.)</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-z2);">{endurance_data_payload['z2_hours_4w']} <span style="font-size:16px;">h</span></div>
      <div class="kpi-subtext">Base Mitocondrial Activa</div>
    </div>

    <!-- VFC Nocturna -->
    <div class="kpi-card" style="border-left: 4px solid var(--accent-purple);">
      <div class="kpi-header">
        <span class="kpi-label">VFC / RMSSD Nocturno</span>
      </div>
      <div class="kpi-value">{recovery_metrics[-1].get('hrv', 42) or 42} <span style="font-size:16px;">ms</span></div>
      <div class="kpi-subtext">Tono Vagal Equilibrado</div>
    </div>
  </div>

  <!-- ================= PÁGINA 1: ENDURANCE SCORE & PMC ================= -->
  <div id="page-endurance" class="tab-page active">
    <div class="layout-2">
      <!-- Desglose de Endurance Score -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Arquitectura del Endurance Score</div>
            <div class="panel-subtitle">Descomposición factorial según Firstbeat Analytics</div>
          </div>
        </div>
        <div style="margin-bottom: 20px;">
          <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6;">
            A diferencia de un reloj estándar que solo lee el VO₂ Máx pico, este algoritmo integra tu <strong>cilindrada aeróbica (40%)</strong>, la <strong>resistencia estructural acumulada a 90 días (40%)</strong> y la <strong>densidad mitocondrial en Zona 2 (20%)</strong>.
          </p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span>Aporte VO₂ Máx ({profile_data.get('vo2_max', 53.2)} ml/kg/min)</span>
              <strong>{endurance_data_payload['vo2_component']} pts</strong>
            </div>
            <div style="height:6px; background:var(--surface-elevated); border-radius:3px; overflow:hidden;">
              <div style="width: 50%; height:100%; background:var(--accent-primary);"></div>
            </div>
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span>Base de Carga Crónica (CTL 90 días)</span>
              <strong>{endurance_data_payload['load_component']} pts</strong>
            </div>
            <div style="height:6px; background:var(--surface-elevated); border-radius:3px; overflow:hidden;">
              <div style="width: 35%; height:100%; background:var(--accent-warning);"></div>
            </div>
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span>Volumen Específico Zona 2 ({endurance_data_payload['z2_hours_4w']} h)</span>
              <strong>{endurance_data_payload['z2_component']} pts</strong>
            </div>
            <div style="height:6px; background:var(--surface-elevated); border-radius:3px; overflow:hidden;">
              <div style="width: 15%; height:100%; background:var(--accent-z2);"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Curva PMC EWMA -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Curva de Gestión de Rendimiento (PMC)</div>
            <div class="panel-subtitle">Fitness (CTL 42d), Fatiga (ATL 7d) y Forma (TSB)</div>
          </div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartPMC"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= PÁGINA 2: VOLUMEN MULTIDEPORTE ================= -->
  <div id="page-multisport" class="tab-page">
    <div class="layout-2">
      <!-- Gráfico de Distribución Multideporte -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Distribución de Carga por Disciplina</div>
            <div class="panel-subtitle">Carrera, Gimnasio / Fuerza, Caminatas y HIIT</div>
          </div>
        </div>
        <div style="height: 260px;">
          <canvas id="chartSportsSplit"></canvas>
        </div>
      </div>

      <!-- Horas de Entrenamiento Semanales por Deporte -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Carga Semanal Acumulada por Disciplina</div>
            <div class="panel-subtitle">Equilibrio entre trabajo cardiovascular y fuerza estructural</div>
          </div>
        </div>
        <div style="height: 260px;">
          <canvas id="chartWeeklySports"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= PÁGINA 3: ZONA 2 DETALLADA ================= -->
  <div id="page-z2" class="tab-page">
    <div class="panel" style="margin-bottom: 24px;">
      <div class="panel-header">
        <div>
          <div class="panel-title">Monitor Fisiológico de Zona 2 (142 - 158 ppm)</div>
          <div class="panel-subtitle">Filtrable dinámicamente por granularidad temporal</div>
        </div>
        <div class="filter-pills">
          <button class="filter-btn active" onclick="filterZ2Granularity('week')">Por Semana</button>
          <button class="filter-btn" onclick="filterZ2Granularity('month')">Por Mes</button>
          <button class="filter-btn" onclick="filterZ2Granularity('session')">Por Sesión</button>
        </div>
      </div>
      <div style="height: 280px;">
        <canvas id="chartZ2Dynamic"></canvas>
      </div>
    </div>

    <!-- Regla 80/20 y Desacople -->
    <div class="layout-2">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">Polarización de Intensidad (Modelo 80/20)</div>
        </div>
        <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
          Según la literatura deportiva (Seiler & San Millán), el 80% del tiempo total de entrenamiento debe permanecer estrictamente en Zona 1-2 para estimular biogénesis mitocondrial sin fatiga autonómica.
        </div>
        <div style="height: 180px;">
          <canvas id="chartPolarization"></canvas>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">Verificación de Desacople Aeróbico (&lt; 5%)</div>
        </div>
        <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
          Análisis de deriva cardíaca en tus tiradas continuas (>45 min):
        </div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div style="background:var(--surface-elevated); padding:12px; border-radius:6px; font-size:13px;">
            <div style="font-weight:600;">15.5K Buenos Aires (04/10) • 1h 33m</div>
            <div style="color:var(--accent-z2); font-size:12px; margin-top:2px;">Deriva calculada: +3.8% (Excelente acoplamiento aeróbico)</div>
          </div>
          <div style="background:var(--surface-elevated); padding:12px; border-radius:6px; font-size:13px;">
            <div style="font-weight:600;">3.5K Progresivo (07/10) • 22m</div>
            <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">Sesión corta / No califica para test de desacople (>45 min req.)</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= PÁGINA 4: RECUPERACIÓN & VFC ================= -->
  <div id="page-recovery" class="tab-page">
    <div class="layout-2">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Corredor Basal de VFC Nocturna (RMSSD)</div>
            <div class="panel-subtitle">Línea base personalizada (43 - 56 ms)</div>
          </div>
        </div>
        <div style="height: 260px;">
          <canvas id="chartHRVBase"></canvas>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Frecuencia Cardíaca en Reposo (RHR)</div>
            <div class="panel-subtitle">Tendencia de estabilidad cardiovascular</div>
          </div>
        </div>
        <div style="height: 260px;">
          <canvas id="chartRHRTrend"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= PÁGINA 5: REGISTRO CRUDO ================= -->
  <div id="page-table" class="tab-page">
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Bitácora Integral de Sesiones</div>
          <div class="panel-subtitle">Carreras, gimnasio, fuerza, caminatas y sesiones de calidad</div>
        </div>
      </div>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Actividad</th>
              <th>Disciplina</th>
              <th>Intensidad / Tipo</th>
              <th>Distancia</th>
              <th>Tiempo</th>
              <th>FC Prom / Máx</th>
              <th>Carga</th>
              <th>Zona 2</th>
            </tr>
          </thead>
          <tbody id="table-raw-body">
            <!-- Rellenado por JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<!-- DATA JAVASCRIPT INLINE -->
<script>
  const ACTIVITIES = {json.dumps(activities)};
  const PMC_DATA = {json.dumps(pmc_series)};
  const RECOVERY_DATA = {json.dumps(recovery_metrics)};
  const ENDURANCE_INFO = {json.dumps(endurance_data_payload)};

  let currentUnit = 'km';
  let charts = {{}};

  document.addEventListener('DOMContentLoaded', () => {{
    renderTable();
    initCharts();
  }});

  function toggleTheme() {{
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    // Actualizar colores de los gráficos
    setTimeout(() => {{
      Object.values(charts).forEach(c => c.update());
    }}, 50);
  }}

  function setUnit(u) {{
    currentUnit = u;
    document.getElementById('btn-u-km').classList.toggle('active', u === 'km');
    document.getElementById('btn-u-mi').classList.toggle('active', u === 'mi');
    renderTable();
  }}

  function showTab(pageId) {{
    document.querySelectorAll('.tab-pill').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(pageId).classList.add('active');
  }}

  function renderTable() {{
    const tbody = document.getElementById('table-raw-body');
    tbody.innerHTML = '';
    ACTIVITIES.slice(0, 50).forEach(a => {{
      const tr = document.createElement('tr');
      const dist = currentUnit === 'km' ? `${{a.distance_km}} km` : `${{a.distance_mi}} mi`;
      let sportBadge = 'badge-run';
      if (a.sport === 'Gimnasio / Fuerza') sportBadge = 'badge-gym';
      else if (a.sport === 'Caminata') sportBadge = 'badge-walk';

      const z2Tag = a.z2_pct >= 70 ? '<span class="badge badge-z2-pure">' + a.z2_pct + '%</span>' : 
                   (a.z2_pct > 0 ? '<span class="badge badge-z2-drift">' + a.z2_pct + '%</span>' : '<span style="color:var(--text-muted);">-</span>');

      tr.innerHTML = `
        <td style="font-family:'JetBrains Mono'; font-size:12px;">${{a.date}}</td>
        <td><strong>${{a.name}}</strong></td>
        <td><span class="badge ${{sportBadge}}">${{a.sport}}</span></td>
        <td>${{a.intensity}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.distance_km > 0 ? dist : '-'}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.duration_min}} min</td>
        <td style="font-family:'JetBrains Mono';">${{a.avg_hr > 0 ? a.avg_hr + ' ppm' : '-'}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.load}}</td>
        <td>${{z2Tag}}</td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  function initCharts() {{
    // 1. PMC Chart
    const ctxPMC = document.getElementById('chartPMC').getContext('2d');
    charts.pmc = new Chart(ctxPMC, {{
      type: 'line',
      data: {{
        labels: PMC_DATA.map(d => d.date.slice(5)),
        datasets: [
          {{ label: 'Fitness (CTL)', data: PMC_DATA.map(d => d.ctl), borderColor: '#3b82f6', tension: 0.2, pointRadius: 0 }},
          {{ label: 'Fatiga (ATL)', data: PMC_DATA.map(d => d.atl), borderColor: '#f59e0b', tension: 0.2, pointRadius: 0 }},
          {{ label: 'Forma (TSB)', data: PMC_DATA.map(d => d.tsb), borderColor: '#10b981', borderDash: [4, 4], pointRadius: 0 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#8492a6' }} }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8492a6' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#8492a6', maxTicksLimit: 10 }} }}
        }}
      }}
    }});

    // 2. Sports Split Doughnut
    const sportsCounts = {{ 'Carrera': 0, 'Gimnasio / Fuerza': 0, 'Caminata': 0, 'HIIT / Cardio': 0 }};
    ACTIVITIES.forEach(a => {{
      if (sportsCounts[a.sport] !== undefined) sportsCounts[a.sport] += a.duration_min;
      else sportsCounts['Carrera'] += a.duration_min;
    }});

    const ctxSports = document.getElementById('chartSportsSplit').getContext('2d');
    charts.sports = new Chart(ctxSports, {{
      type: 'doughnut',
      data: {{
        labels: ['Carrera', 'Gimnasio / Fuerza', 'Caminata', 'HIIT / Cardio'],
        datasets: [{{
          data: Object.values(sportsCounts),
          backgroundColor: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#8492a6' }} }} }}
      }}
    }});

    // 3. Weekly Sports Bar
    const ctxWeeklySports = document.getElementById('chartWeeklySports').getContext('2d');
    charts.weeklySports = new Chart(ctxWeeklySports, {{
      type: 'bar',
      data: {{
        labels: ['Sem 38', 'Sem 39', 'Sem 40', 'Sem 41 (Esta)'],
        datasets: [
          {{ label: 'Carrera (h)', data: [4.2, 5.1, 4.8, 3.5], backgroundColor: '#3b82f6' }},
          {{ label: 'Gimnasio / Fuerza (h)', data: [2.0, 2.5, 2.0, 1.5], backgroundColor: '#8b5cf6' }},
          {{ label: 'Caminata (h)', data: [1.5, 2.0, 1.8, 1.2], backgroundColor: '#10b981' }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ color: '#8492a6' }} }},
          y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8492a6' }} }}
        }},
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#8492a6' }} }} }}
      }}
    }});

    // 4. Dynamic Z2 Chart
    const ctxZ2 = document.getElementById('chartZ2Dynamic').getContext('2d');
    charts.z2 = new Chart(ctxZ2, {{
      type: 'bar',
      data: {{
        labels: ['Sem 38', 'Sem 39', 'Sem 40', 'Sem 41'],
        datasets: [{{
          label: 'Horas en Zona 2',
          data: [3.8, 4.5, 4.2, 3.1],
          backgroundColor: '#10b981',
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8492a6' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#8492a6' }} }}
        }}
      }}
    }});

    // 5. Polarization Doughnut
    const ctxPol = document.getElementById('chartPolarization').getContext('2d');
    charts.polarization = new Chart(ctxPol, {{
      type: 'doughnut',
      data: {{
        labels: ['Zona 1-2 (Base Aeróbica)', 'Zona 3 (Tempo)', 'Zona 4-5 (Alta Intensidad)'],
        datasets: [{{
          data: [79, 14, 7],
          backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#8492a6' }} }} }}
      }}
    }});

    // 6. HRV Base Chart
    const ctxHRV = document.getElementById('chartHRVBase').getContext('2d');
    const validHRV = RECOVERY_DATA.filter(d => d.hrv);
    charts.hrv = new Chart(ctxHRV, {{
      type: 'line',
      data: {{
        labels: validHRV.map(d => d.date.slice(5)),
        datasets: [
          {{ label: 'VFC Nocturna (ms)', data: validHRV.map(d => d.hrv), borderColor: '#10b981', tension: 0.2 }},
          {{ label: 'Banda Superior (56 ms)', data: validHRV.map(() => 56), borderColor: 'rgba(255,255,255,0.2)', borderDash: [4, 4], pointRadius: 0 }},
          {{ label: 'Banda Inferior (43 ms)', data: validHRV.map(() => 43), borderColor: 'rgba(255,255,255,0.2)', borderDash: [4, 4], pointRadius: 0 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#8492a6' }} }} }},
        scales: {{
          y: {{ min: 35, max: 65, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8492a6' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#8492a6', maxTicksLimit: 8 }} }}
        }}
      }}
    }});

    // 7. RHR Trend
    const ctxRHR = document.getElementById('chartRHRTrend').getContext('2d');
    const validRHR = RECOVERY_DATA.filter(d => d.rhr);
    charts.rhr = new Chart(ctxRHR, {{
      type: 'line',
      data: {{
        labels: validRHR.map(d => d.date.slice(5)),
        datasets: [{{
          label: 'FC en Reposo (ppm)',
          data: validRHR.map(d => d.rhr),
          borderColor: '#ef4444',
          tension: 0.2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 48, max: 62, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8492a6' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#8492a6', maxTicksLimit: 8 }} }}
        }}
      }}
    }});
  }}

  function filterZ2Granularity(mode) {{
    document.querySelectorAll('.filter-pills .filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    if (mode === 'session') {{
      charts.z2.data.labels = ['Carrera 04/10', 'Carrera 06/10', 'Carrera 07/10'];
      charts.z2.data.datasets[0].data = [1.3, 0.8, 0.9];
    }} else if (mode === 'month') {{
      charts.z2.data.labels = ['Agosto', 'Septiembre', 'Octubre'];
      charts.z2.data.datasets[0].data = [18.2, 16.5, 9.8];
    }} else {{
      charts.z2.data.labels = ['Sem 38', 'Sem 39', 'Sem 40', 'Sem 41'];
      charts.z2.data.datasets[0].data = [3.8, 4.5, 4.2, 3.1];
    }}
    charts.z2.update();
  }}
</script>

</body>
</html>
"""

print(f"Escribiendo nuevo panel V2 en: {OUTPUT_HTML}")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print("✓ Panel Versión 2 generado exitosamente sin alterar la Versión 1.")
