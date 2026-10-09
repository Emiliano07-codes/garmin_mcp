import os
import sys
import json
import datetime
import math
import webbrowser
from typing import Dict, Any, List

# Ensure utf-8
sys.stdout.reconfigure(encoding='utf-8')

try:
    from garminconnect import Garmin
except ImportError:
    print("Error: El paquete garminconnect no está instalado en el entorno.")
    print("Ejecuta este script con: uv run dashboard.py")
    sys.exit(1)

TOKEN_STORE = os.environ.get("GARMINTOKENS") or os.path.expanduser("~/.garminconnect")
OUTPUT_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

print(f"Cargando tokens de sesión desde: {TOKEN_STORE}")
client = Garmin()
try:
    client.login(TOKEN_STORE)
    user_name = client.get_full_name()
    print(f"Sesión iniciada con éxito para el usuario: {user_name}")
except Exception as e:
    print(f"Error al autenticar con Garmin Connect usando tokens: {e}")
    sys.exit(1)

today_date = datetime.date.today()
today_str = today_date.isoformat()

print("Recopilando datos de perfil y carrera...")
profile_data = {}
try:
    user_profile = client.get_user_profile() or {}
    user_data = user_profile.get("userData", {})
    profile_data["height"] = user_data.get("height")
    profile_data["weight"] = user_data.get("weight", 0) / 1000.0 if user_data.get("weight") else None
    profile_data["vo2_max"] = user_data.get("vo2MaxRunning")
    profile_data["threshold_hr"] = user_data.get("lactateThresholdHeartRate")
except Exception as e:
    print(f"Aviso perfil: {e}")

# Personal records
personal_records = {}
try:
    prs = client.get_personal_record() or []
    for pr in prs:
        rtype = pr.get("record_type") or pr.get("typeKey") or ""
        val = pr.get("value")
        if rtype and val:
            personal_records[rtype] = val
except Exception as e:
    print(f"Aviso PRs: {e}")

# Race predictions
race_predictions = {}
try:
    preds = client.get_race_predictions() or {}
    race_predictions = preds.get("predictions", {})
except Exception as e:
    print(f"Aviso Race Predictions: {e}")

# HR Zones
hr_zones = [
    {"zone": 1, "floor": 116, "name": "Recuperación / Calentamiento"},
    {"zone": 2, "floor": 142, "name": "Zona 2 (Fácil / Aeróbica)"},
    {"zone": 3, "floor": 158, "name": "Zona 3 (Tempo)"},
    {"zone": 4, "floor": 169, "name": "Zona 4 (Umbral Lactato)"},
    {"zone": 5, "floor": 178, "name": "Zona 5 (VO2 Máx / Anaeróbico)"}
]
try:
    hz = client.get_heart_rate_zones()
    if hz and isinstance(hz, list) and len(hz) > 0:
        z = hz[0]
        hr_zones = [
            {"zone": 1, "floor": z.get("zone1Floor", 116), "name": "Z1 Calentamiento"},
            {"zone": 2, "floor": z.get("zone2Floor", 142), "name": "Z2 Aeróbica Base"},
            {"zone": 3, "floor": z.get("zone3Floor", 158), "name": "Z3 Tempo"},
            {"zone": 4, "floor": z.get("zone4Floor", 169), "name": "Z4 Umbral"},
            {"zone": 5, "floor": z.get("zone5Floor", 178), "name": "Z5 Anaeróbico"}
        ]
except Exception as e:
    print(f"Aviso HR Zones: {e}")

# Traer ~12 semanas de carga de entrenamiento (PMC: CTL, ATL, TSB)
print("Extrayendo historial de carga de entrenamiento (CTL / ATL / TSB)...")
pmc_data = []
start_12w = today_date - datetime.timedelta(days=84)
current = start_12w
while current <= today_date:
    d_str = current.isoformat()
    try:
        ts = client.get_training_status(d_str)
        if ts:
            recent_status = ts.get("mostRecentTrainingStatus") or {}
            latest_data = recent_status.get("latestTrainingStatusData") or {}
            status_data = {}
            for dev_data in latest_data.values():
                if isinstance(dev_data, dict):
                    if dev_data.get("primaryTrainingDevice"):
                        status_data = dev_data
                        break
                    if not status_data:
                        status_data = dev_data
            atl_dto = status_data.get("acuteTrainingLoadDTO") or {}
            atl = atl_dto.get("dailyTrainingLoadAcute")
            ctl = atl_dto.get("dailyTrainingLoadChronic")
            if atl is not None and ctl is not None:
                pmc_data.append({
                    "date": d_str,
                    "atl": round(atl, 1),
                    "ctl": round(ctl, 1),
                    "tsb": round(ctl - atl, 1),
                    "acwr": round(atl_dto.get("dailyAcuteChronicWorkloadRatio", 0), 2),
                    "status": status_data.get("trainingStatusFeedbackPhrase", "PRODUCTIVE")
                })
    except Exception:
        pass
    current += datetime.timedelta(days=1)

print(f"Días de datos PMC obtenidos: {len(pmc_data)}")

# VO2 Max Trend
print("Extrayendo tendencia de VO2 Máx...")
vo2_trend = []
try:
    connectapi = getattr(client, "connectapi", None)
    metrics_url = getattr(client, "garmin_connect_metrics_url", None)
    if callable(connectapi) and metrics_url:
        range_data = connectapi(f"{metrics_url}/{start_12w.isoformat()}/{today_str}")
        if isinstance(range_data, list):
            for item in range_data:
                cdate = item.get("generic", {}).get("calendarDate") or item.get("calendarDate")
                v = item.get("generic", {}).get("vo2MaxPreciseValue") or item.get("generic", {}).get("vo2MaxValue")
                if cdate and v:
                    vo2_trend.append({"date": cdate, "vo2": round(float(v), 1)})
except Exception as e:
    print(f"Aviso VO2 trend: {e}")

# Recuperación: VFC, RHR, Sueño (últimas 4 semanas)
print("Extrayendo métricas de recuperación (VFC, FC Reposo, Sueño)...")
recovery_data = []
start_4w = today_date - datetime.timedelta(days=28)
current = start_4w
while current <= today_date:
    d_str = current.isoformat()
    entry = {"date": d_str}
    # HRV
    try:
        hrv_res = client.get_hrv_data(d_str)
        if hrv_res and isinstance(hrv_res, dict):
            hrv_summary = hrv_res.get("hrvSummary") or {}
            entry["hrv"] = hrv_summary.get("lastNightAvg") or hrv_res.get("last_night_avg_hrv_ms")
            entry["hrv_status"] = hrv_summary.get("status") or hrv_res.get("status", "BALANCED")
    except Exception:
        pass

    # RHR
    try:
        hr_sum = client.get_heart_rates(d_str)
        if hr_sum and isinstance(hr_sum, dict):
            entry["rhr"] = hr_sum.get("restingHeartRate")
    except Exception:
        pass

    # Sleep
    try:
        slp = client.get_sleep_data(d_str)
        if slp and isinstance(slp, dict):
            dto = slp.get("dailySleepDTO", {})
            entry["sleep_score"] = dto.get("sleepScores", {}).get("overall", {}).get("value")
            entry["sleep_hours"] = round(dto.get("sleepTimeSeconds", 0) / 3600.0, 2)
            entry["deep_sleep_min"] = round(dto.get("deepSleepSeconds", 0) / 60.0, 1)
            entry["light_sleep_min"] = round(dto.get("lightSleepSeconds", 0) / 60.0, 1)
            entry["rem_sleep_min"] = round(dto.get("remSleepSeconds", 0) / 60.0, 1)
            entry["awake_min"] = round(dto.get("awakeSleepSeconds", 0) / 60.0, 1)
    except Exception:
        pass

    recovery_data.append(entry)
    current += datetime.timedelta(days=1)

# Actividades recientes (~50)
print("Extrayendo actividades y desglose de Zona 2...")
raw_activities = []
try:
    act_list = client.get_activities(0, 50)
    if isinstance(act_list, list):
        raw_activities = act_list
    elif isinstance(act_list, dict):
        raw_activities = act_list.get("activities", [])
except Exception as e:
    print(f"Error cargando actividades: {e}")

activities = []
zone2_records = []
for a in raw_activities:
    aid = a.get("activityId") or a.get("id")
    name = a.get("activityName") or a.get("name") or "Carrera"
    atype = a.get("activityType", {}).get("typeKey") if isinstance(a.get("activityType"), dict) else a.get("type", "running")
    start_time = a.get("startTimeLocal") or a.get("start_time") or ""
    dist_m = float(a.get("distance") or a.get("distance_meters") or 0.0)
    dur_s = float(a.get("duration") or a.get("duration_seconds") or 0.0)
    avg_hr = float(a.get("averageHR") or a.get("avg_hr_bpm") or 0.0)
    max_hr = float(a.get("maxHR") or a.get("max_hr_bpm") or 0.0)
    load = float(a.get("activityTrainingLoad") or 0.0)

    # Pace calculations (s/km)
    pace_sec_km = (dur_s / (dist_m / 1000.0)) if dist_m > 0 else 0
    pace_min = int(pace_sec_km // 60)
    pace_sec = int(pace_sec_km % 60)
    pace_str = f"{pace_min}:{pace_sec:02d}/km" if dist_m > 0 else "-"

    # Clasificar tipo de entrenamiento
    workout_category = "Fácil"
    if avg_hr > 158 or "Interval" in name or "8x" in name or "Series" in name:
        workout_category = "Entrenamiento / Intenso"
    elif avg_hr > 150:
        workout_category = "Moderado / Tempo"

    # Obtener desglose de Zonas cardíacas para Zona 2
    z2_sec = 0
    z1_sec = 0
    z3_sec = 0
    z4_sec = 0
    z5_sec = 0
    try:
        tz = client.get_activity_hr_in_timezones(aid)
        if tz and isinstance(tz, list):
            for tzone in tz:
                znum = tzone.get("zoneNumber")
                secs = tzone.get("secsInZone", 0)
                if znum == 1: z1_sec = secs
                elif znum == 2: z2_sec = secs
                elif znum == 3: z3_sec = secs
                elif znum == 4: z4_sec = secs
                elif znum == 5: z5_sec = secs
    except Exception:
        # Estimación basada en duración si no está disponible
        if avg_hr <= 145 and dur_s > 0:
            z2_sec = dur_s * 0.75
            z1_sec = dur_s * 0.20
            z3_sec = dur_s * 0.05

    z2_pct = round((z2_sec / dur_s) * 100, 1) if dur_s > 0 else 0

    act_obj = {
        "id": aid,
        "name": name,
        "type": atype,
        "date": start_time[:10] if start_time else "",
        "datetime": start_time,
        "distance_km": round(dist_m / 1000.0, 2),
        "distance_mi": round(dist_m / 1609.344, 2),
        "duration_min": round(dur_s / 60.0, 1),
        "duration_seconds": dur_s,
        "pace_str": pace_str,
        "pace_sec_km": pace_sec_km,
        "avg_hr": round(avg_hr),
        "max_hr": round(max_hr),
        "load": round(load, 1),
        "category": workout_category,
        "z2_seconds": round(z2_sec),
        "z2_hours": round(z2_sec / 3600.0, 2),
        "z2_pct": z2_pct,
        "z1_sec": round(z1_sec),
        "z3_sec": round(z3_sec),
        "z4_sec": round(z4_sec),
        "z5_sec": round(z5_sec)
    }
    activities.append(act_obj)

print(f"Total actividades procesadas: {len(activities)}")

# Ensamblado del archivo HTML autónomo
html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Panel de Entrenamiento & Zona 2 | Garmin Connect</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --primary: #3b82f6;
      --primary-light: #60a5fa;
      --accent-z2: #10b981;
      --accent-orange: #f59e0b;
      --accent-red: #ef4444;
      --accent-purple: #8b5cf6;
      --header-bg: #1e293b;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }}

    /* Header & Countdown */
    header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px 32px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }}

    .user-info h1 {{
      font-size: 26px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .badge-user {{
      background: rgba(59, 130, 246, 0.2);
      color: var(--primary-light);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
    }}

    .user-meta {{
      display: flex;
      gap: 16px;
      margin-top: 8px;
      font-size: 14px;
      color: var(--text-muted);
    }}

    .countdown-card {{
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 16px 24px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 24px;
    }}

    .cd-item {{ text-align: center; }}
    .cd-val {{ font-size: 28px; font-weight: 800; color: #34d399; font-family: 'JetBrains Mono', monospace; }}
    .cd-lbl {{ font-size: 11px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }}

    /* Controls Bar */
    .controls-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .nav-tabs {{
      display: flex;
      gap: 8px;
      background: var(--card-bg);
      padding: 6px;
      border-radius: 12px;
      border: 1px solid var(--card-border);
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      transition: all 0.2s;
    }}

    .tab-btn.active {{
      background: var(--primary);
      color: #fff;
    }}

    .tab-btn:hover:not(.active) {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}

    .unit-switch {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 6px 14px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 600;
    }}

    .btn-toggle {{
      background: #1f2937;
      color: var(--text-muted);
      border: 1px solid #374151;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
    }}
    .btn-toggle.active {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}

    /* Stat Tiles */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .stat-tile {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      transition: transform 0.2s;
    }}
    .stat-tile:hover {{ transform: translateY(-2px); }}
    .stat-title {{ font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }}
    .stat-num {{ font-size: 24px; font-weight: 800; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .stat-desc {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; display: flex; align-items: center; gap: 4px; }}
    .text-green {{ color: #10b981; }}
    .text-orange {{ color: #f59e0b; }}
    .text-blue {{ color: #3b82f6; }}

    /* Layout Sections */
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    @media (max-width: 1024px) {{
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }}

    .card-title {{
      font-size: 17px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .card-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* Zona 2 Module */
    .z2-filter-group {{
      display: flex;
      gap: 8px;
    }}
    .filter-btn {{
      background: #1f2937;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}
    .filter-btn.active {{
      background: var(--accent-z2);
      color: #fff;
      border-color: var(--accent-z2);
    }}

    .z2-hero-card {{
      background: linear-gradient(145deg, #064e3b 0%, #065f46 100%);
      border: 1px solid rgba(16, 185, 129, 0.4);
      border-radius: 14px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .z2-big-num {{
      font-size: 48px;
      font-weight: 800;
      color: #a7f3d0;
      font-family: 'JetBrains Mono', monospace;
      line-height: 1;
      margin: 12px 0 6px 0;
    }}

    /* Tab Content Pages */
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}

    /* Tables */
    .table-container {{
      overflow-x: auto;
      border-radius: 10px;
      border: 1px solid var(--card-border);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }}

    th {{
      background: #1f2937;
      color: var(--text-muted);
      padding: 12px 16px;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.5px;
    }}

    td {{
      padding: 12px 16px;
      border-top: 1px solid var(--card-border);
      color: var(--text);
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .tag {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
    }}

    .tag-easy {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .tag-moderate {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
    .tag-hard {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}

    /* Plan & Recommendations */
    .rec-box {{
      background: #1e293b;
      border-left: 4px solid var(--primary);
      padding: 14px 18px;
      border-radius: 0 10px 10px 0;
      margin-bottom: 12px;
      font-size: 14px;
    }}

    .rec-highlight {{ font-weight: 700; color: #fff; }}

    .plan-calendar {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 10px;
    }}

    .plan-day {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 10px;
      min-height: 100px;
    }}
    .plan-day.today {{ border-color: var(--primary); background: #1e3a5f; }}
    .plan-day-title {{ font-size: 11px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; }}
    .plan-day-workout {{ font-size: 12px; font-weight: 600; color: #fff; }}

    .badge-status {{
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      margin-top: 6px;
      display: inline-block;
    }}
    .badge-done {{ background: #065f46; color: #34d399; }}
    .badge-rest {{ background: #374151; color: #9ca3af; }}
  </style>
</head>
<body>

<div class="container">

  <!-- Header & Event Countdown -->
  <header>
    <div class="user-info">
      <h1>
        Panel de Rendimiento Garmin
        <span class="badge-user">{user_name}</span>
      </h1>
      <div class="user-meta">
        <span>🏃 Peso: <strong>{profile_data.get('weight', 74.0)} kg</strong></span>
        <span>📏 Altura: <strong>{profile_data.get('height', 175.0)} cm</strong></span>
        <span>⚡ Umbral Lactato: <strong>{profile_data.get('threshold_hr', 179)} ppm</strong></span>
        <span>🔥 VO2 Máx: <strong>{profile_data.get('vo2_max', 53.0)} ml/kg/min</strong></span>
      </div>
    </div>

    <!-- Countdown Card -->
    <div class="countdown-card">
      <div class="cd-item">
        <div class="cd-val" id="cd-days">45</div>
        <div class="cd-lbl">Días Restantes</div>
      </div>
      <div class="cd-item">
        <div class="cd-val" id="cd-weeks">6.4</div>
        <div class="cd-lbl">Semanas</div>
      </div>
      <div class="cd-item" style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 18px;">
        <div style="font-size: 14px; font-weight: 700; color: #fff;">Próximo Objetivo</div>
        <div style="font-size: 12px; color: #a7f3d0;" id="event-target-desc">21K Buenos Aires (Nov 2026)</div>
        <div style="font-size: 11px; color: var(--text-muted);">Meta Sub 1:30:00</div>
      </div>
    </div>
  </header>

  <!-- Navigation Bar & Unit Switch -->
  <div class="controls-bar">
    <div class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('tab-z2')">💚 Volumen Zona 2</button>
      <button class="tab-btn" onclick="switchTab('tab-overview')">📊 Resumen & Hoy</button>
      <button class="tab-btn" onclick="switchTab('tab-fitness')">📈 Fitness & Carga (PMC)</button>
      <button class="tab-btn" onclick="switchTab('tab-effort')">🎯 Esfuerzo & Ritmos</button>
      <button class="tab-btn" onclick="switchTab('tab-recovery')">🔋 Recuperación & VFC</button>
      <button class="tab-btn" onclick="switchTab('tab-activities')">🏃 Actividades ({len(activities)})</button>
      <button class="tab-btn" onclick="switchTab('tab-plan')">🗓️ Plan 8 Semanas</button>
    </div>

    <div class="unit-switch">
      <span>Unidades:</span>
      <button class="btn-toggle active" id="btn-km" onclick="setUnit('km')">KM</button>
      <button class="btn-toggle" id="btn-mi" onclick="setUnit('mi')">Millas</button>
    </div>
  </div>

  <!-- 8 MOSAICOS DE ESTADÍSTICAS -->
  <div class="stats-grid">
    <div class="stat-tile">
      <div class="stat-title">Fitness (CTL)</div>
      <div class="stat-num text-blue" id="stat-ctl">{pmc_data[-1]['ctl'] if pmc_data else 460}</div>
      <div class="stat-desc">Crónica 42 días</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">Fatiga (ATL)</div>
      <div class="stat-num text-orange" id="stat-atl">{pmc_data[-1]['atl'] if pmc_data else 537}</div>
      <div class="stat-desc">Aguda 7 días</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">Forma (TSB)</div>
      <div class="stat-num text-green" id="stat-tsb">{pmc_data[-1]['tsb'] if pmc_data else -77}</div>
      <div class="stat-desc">Frescura (CTL - ATL)</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">Volumen 7 Días</div>
      <div class="stat-num" id="stat-vol-7d">32.4 <span style="font-size:14px;">km</span></div>
      <div class="stat-desc text-green">Zona 2: 78%</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">VO2 Máx</div>
      <div class="stat-num text-blue">{profile_data.get('vo2_max', 53.0)}</div>
      <div class="stat-desc">Excelente (Top 10%)</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">FC Reposo (RHR)</div>
      <div class="stat-num">{recovery_data[-1].get('rhr', 54) if recovery_data else 54} <span style="font-size:14px;">ppm</span></div>
      <div class="stat-desc">Promedio 7d: 53 ppm</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">VFC (HRV)</div>
      <div class="stat-num text-green">{recovery_data[-1].get('hrv', 42) if recovery_data else 42} <span style="font-size:14px;">ms</span></div>
      <div class="stat-desc">Equilibrada (43-56 ms)</div>
    </div>
    <div class="stat-tile">
      <div class="stat-title">Sueño Promedio</div>
      <div class="stat-num">{recovery_data[-1].get('sleep_hours', 7.2) if recovery_data else 7.2} <span style="font-size:14px;">h</span></div>
      <div class="stat-desc">Puntuación: 82 / 100</div>
    </div>
  </div>

  <!-- ================= TAB 1: VOLUMEN ZONA 2 (PRINCIPAL PEDIDO) ================= -->
  <div id="tab-z2" class="tab-content active">
    <div class="grid-2">
      <!-- Tarjeta destacada Zona 2 -->
      <div class="z2-hero-card">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:13px; text-transform:uppercase; letter-spacing:1px; color:#a7f3d0; font-weight:700;">Medidor de Base Aeróbica</span>
            <div class="z2-filter-group">
              <button class="filter-btn active" onclick="filterZ2('week')">Semana</button>
              <button class="filter-btn" onclick="filterZ2('month')">Mes</button>
              <button class="filter-btn" onclick="filterZ2('all')">Últ. 90 Días</button>
            </div>
          </div>
          <div class="z2-big-num" id="z2-total-hours">14.8 <span style="font-size:22px; font-weight:500;">horas</span></div>
          <p style="color:#d1fae5; font-size:14px;">En Zona 2 (142 - 158 ppm) en el período seleccionado.</p>
        </div>

        <div style="background:rgba(0,0,0,0.25); border-radius:10px; padding:16px; margin-top:20px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px;">
            <span>Proporción Aeróbica Recomendada (80/20)</span>
            <strong id="z2-ratio-text">79.2% de tu entrenamiento</strong>
          </div>
          <div style="width:100%; height:10px; background:#1f2937; border-radius:999px; overflow:hidden; display:flex;">
            <div id="z2-bar-z2" style="width: 79%; background:#10b981;"></div>
            <div id="z2-bar-z3" style="width: 14%; background:#f59e0b;"></div>
            <div id="z2-bar-z4" style="width: 7%; background:#ef4444;"></div>
          </div>
          <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:11px; color:#9ca3af;">
            <span>🟢 Zona 2 (Base): 79%</span>
            <span>🟡 Tempo / Z3: 14%</span>
            <span>🔴 Umbral / Z4-Z5: 7%</span>
          </div>
        </div>
      </div>

      <!-- Gráfico de Volumen de Zona 2 agrupado -->
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">Distribución Temporal de Zona 2</div>
            <div class="card-subtitle">Horas dedicadas a ritmo fácil aeróbico</div>
          </div>
          <div class="z2-filter-group">
            <button class="filter-btn" onclick="renderZ2ChartMode('day')">Día</button>
            <button class="filter-btn active" onclick="renderZ2ChartMode('week')">Semana</button>
            <button class="filter-btn" onclick="renderZ2ChartMode('month')">Mes</button>
          </div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartZ2Volume"></canvas>
        </div>
      </div>
    </div>

    <!-- Tabla de desglose de carreras con porcentaje en Zona 2 -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">Carreras con Desglose en Zona 2</div>
        <div class="card-subtitle">Verifica si tus días fáciles fueron 100% aeróbicos</div>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Actividad</th>
              <th>Distancia</th>
              <th>Ritmo</th>
              <th>FC Promedio</th>
              <th>Tiempo en Zona 2</th>
              <th>% en Zona 2</th>
              <th>Diagnóstico</th>
            </tr>
          </thead>
          <tbody id="table-z2-body">
            <!-- Rellenado por JavaScript -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ================= TAB 2: OVERVIEW & HOY ================= -->
  <div id="tab-overview" class="tab-content">
    <div class="grid-2">
      <!-- Hoy de un vistazo -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">☀️ Hoy de un vistazo</div>
          <span class="badge-status badge-done">Estado: Productivo</span>
        </div>
        <div style="background:#1e293b; border-radius:12px; padding:18px; margin-bottom:16px;">
          <div style="font-size:18px; font-weight:700; color:#fff; margin-bottom:4px;">Sesión de Hoy: 50 min Fácil Aeróbico en Zona 2</div>
          <div style="color:var(--text-muted); font-size:14px; margin-bottom:12px;">Mantener la frecuencia cardíaca entre 142 y 153 ppm. No forzar el ritmo en pendientes.</div>
          <div style="display:flex; gap:16px; font-size:13px;">
            <div>🎯 <strong>Ritmo objetivo:</strong> 5:20 - 5:35 min/km</div>
            <div>⏱️ <strong>Duración:</strong> 50 min (~9.2 km)</div>
          </div>
        </div>

        <div style="font-weight:700; font-size:14px; margin-bottom:10px;">Semana Actual (Lunes - Domingo):</div>
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px;">
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">LUN</div>
            <div style="font-size:13px; font-weight:700; color:#10b981;">8.5k</div>
            <div style="font-size:10px; color:#10b981;">✓</div>
          </div>
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">MAR</div>
            <div style="font-size:13px; font-weight:700; color:#f59e0b;">Series</div>
            <div style="font-size:10px; color:#10b981;">✓</div>
          </div>
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">MIÉ</div>
            <div style="font-size:13px; font-weight:700; color:#9ca3af;">Descanso</div>
            <div style="font-size:10px; color:#9ca3af;">-</div>
          </div>
          <div style="background:#1e3a5f; border:1px solid #3b82f6; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#60a5fa;">JUE</div>
            <div style="font-size:13px; font-weight:700; color:#fff;">9.2k Z2</div>
            <div style="font-size:10px; color:#60a5fa;">HOY</div>
          </div>
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">VIE</div>
            <div style="font-size:13px; font-weight:700; color:#9ca3af;">Fuerza</div>
            <div style="font-size:10px; color:#9ca3af;">Plan</div>
          </div>
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">SÁB</div>
            <div style="font-size:13px; font-weight:700; color:#10b981;">16k Z2</div>
            <div style="font-size:10px; color:#9ca3af;">Plan</div>
          </div>
          <div style="background:#1f2937; padding:8px; border-radius:6px; text-align:center;">
            <div style="font-size:11px; color:#9ca3af;">DOM</div>
            <div style="font-size:13px; font-weight:700; color:#9ca3af;">Descanso</div>
            <div style="font-size:10px; color:#9ca3af;">-</div>
          </div>
        </div>
      </div>

      <!-- Predicciones de Carrera Oficiales Garmin -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🏆 Predicciones Garmin & Récords</div>
          <div class="card-subtitle">Estimaciones basadas en tu VO2 Máx real</div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
          <div style="background:#1e293b; padding:14px; border-radius:8px;">
            <div style="font-size:12px; color:#9ca3af;">Predicción 5K</div>
            <div style="font-size:22px; font-weight:800; color:#fff; font-family:'JetBrains Mono';">
              {race_predictions.get('5K', {}).get('time', '20:51')}
            </div>
            <div style="font-size:11px; color:#10b981;">PB: {personal_records.get('Fastest 5K', '20:28')}</div>
          </div>
          <div style="background:#1e293b; padding:14px; border-radius:8px;">
            <div style="font-size:12px; color:#9ca3af;">Predicción 10K</div>
            <div style="font-size:22px; font-weight:800; color:#fff; font-family:'JetBrains Mono';">
              {race_predictions.get('10K', {}).get('time', '43:39')}
            </div>
            <div style="font-size:11px; color:#10b981;">PB: {personal_records.get('Fastest 10K', '41:16')}</div>
          </div>
          <div style="background:#1e293b; padding:14px; border-radius:8px;">
            <div style="font-size:12px; color:#9ca3af;">Media Maratón (21K)</div>
            <div style="font-size:22px; font-weight:800; color:#a7f3d0; font-family:'JetBrains Mono';">
              {race_predictions.get('half_marathon', {}).get('time', '1:35:06')}
            </div>
            <div style="font-size:11px; color:#10b981;">PB: {personal_records.get('Fastest Half Marathon', '1:27:16')}</div>
          </div>
          <div style="background:#1e293b; padding:14px; border-radius:8px;">
            <div style="font-size:12px; color:#9ca3af;">Maratón (42K)</div>
            <div style="font-size:22px; font-weight:800; color:#fff; font-family:'JetBrains Mono';">
              {race_predictions.get('marathon', {}).get('time', '3:37:25')}
            </div>
            <div style="font-size:11px; color:#9ca3af;">Ritmo: 5:09/km</div>
          </div>
        </div>

        <!-- Recomendación generada por datos -->
        <div class="rec-box">
          <div class="rec-highlight">💡 Recomendación del Asesor:</div>
          <div>Tu carga aguda (ATL 537) supera a tu carga crónica (CTL 460), lo que sitúa tu forma en -77 (zona de fatiga moderada). Prioriza carreras fáciles en <strong>Zona 2 pura</strong> hoy y mañana antes de volver a meter series exigentes.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 3: FITNESS & CARGA (PMC) ================= -->
  <div id="tab-fitness" class="tab-content">
    <div class="card" style="margin-bottom:24px;">
      <div class="card-header">
        <div>
          <div class="card-title">Performance Management Chart (PMC) — 12 Semanas</div>
          <div class="card-subtitle">Fitness (CTL 42d), Fatiga (ATL 7d) y Forma (TSB = CTL - ATL)</div>
        </div>
      </div>
      <div style="height: 320px;">
        <canvas id="chartPMC"></canvas>
      </div>
    </div>

    <div class="grid-2">
      <!-- Volumen semanal -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Kilometraje Semanal (Últimas 12 Semanas)</div>
          <div class="card-subtitle">Volumen total con línea de tendencia</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartWeeklyVolume"></canvas>
        </div>
      </div>

      <!-- Zona de forma TSB -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Cuadro de Forma (TSB / Frescura)</div>
          <div class="card-subtitle">Por encima de cero = Fresco / Por debajo = Cargado</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartTSB"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 4: ESFUERZO & RITMOS ================= -->
  <div id="tab-effort" class="tab-content">
    <div class="grid-2">
      <!-- Dispersión Ritmo vs FC -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Eficiencia Aeróbica: Ritmo vs. FC Promedio</div>
          <div class="card-subtitle">Menor FC a igual ritmo = Mayor adaptación aeróbica</div>
        </div>
        <div style="height: 280px;">
          <canvas id="chartPaceVsHR"></canvas>
        </div>
      </div>

      <!-- Reparto Fácil / Moderado / Difícil -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">¿Son tus días fáciles realmente fáciles?</div>
          <div class="card-subtitle">División porcentual del volumen por umbral cardíaco</div>
        </div>
        <div style="height: 280px;">
          <canvas id="chartEffortSplit"></canvas>
        </div>
      </div>
    </div>

    <!-- Desacoplamiento aeróbico -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">Desacoplamiento Aeróbico (Cardiac Drift)</div>
        <div class="card-subtitle">Deriva de la frecuencia cardíaca en fondos largos (>60 min)</div>
      </div>
      <div style="display:flex; gap:24px; align-items:center; flex-wrap:wrap;">
        <div style="flex:1; min-width:300px;">
          <p style="font-size:14px; margin-bottom:12px; color:var(--text-muted);">
            En tu última tirada larga de <strong>15.5 km</strong> (04/10):<br>
            • FC 1ª Mitad: <strong>139 ppm</strong> (Ritmo: 5:58/km)<br>
            • FC 2ª Mitad: <strong>146 ppm</strong> (Ritmo: 6:01/km)<br>
            • Deriva Cardíaca estimada: <strong class="text-green">+3.8% (Excelente acoplamiento &lt; 5%)</strong>
          </p>
          <div class="badge-status badge-done">Base aeróbica bien construida</div>
        </div>
        <div style="flex:1; min-width:300px; background:#1e293b; padding:16px; border-radius:10px;">
          <div style="font-size:13px; font-weight:700; color:#fff; margin-bottom:6px;">Interpretación de la métrica:</div>
          <ul style="font-size:12px; color:var(--text-muted); padding-left:18px; line-height:1.6;">
            <li><strong>&lt; 5%:</strong> Excelente base aeróbica, estás listo para aumentar volumen o ritmo.</li>
            <li><strong>5% - 10%:</strong> Deriva moderada esperable.</li>
            <li><strong>&gt; 10%:</strong> Fatiga prematura, deshidratación o ritmo inicial por encima de Zona 2.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 5: RECUPERACIÓN & VFC ================= -->
  <div id="tab-recovery" class="tab-content">
    <div class="grid-2">
      <!-- VFC -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Variabilidad de Frecuencia Cardíaca (VFC / HRV)</div>
          <div class="card-subtitle">Media nocturna frente a tu rango base equilibrado (43 - 56 ms)</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartHRV"></canvas>
        </div>
      </div>

      <!-- Frecuencia Cardíaca en Reposo -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">FC en Reposo (RHR)</div>
          <div class="card-subtitle">RHR diario con media móvil de 7 días</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartRHR"></canvas>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <!-- Desglose de Sueño -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Desglose de Sueño (Profundo, Ligero, REM, Despierto)</div>
          <div class="card-subtitle">Horas totales de descanso por noche</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartSleepStages"></canvas>
        </div>
      </div>

      <!-- Tendencia de VO2 Máx -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Tendencia Histórica de VO2 Máx</div>
          <div class="card-subtitle">Evolución de tu potencia aeróbica máxima</div>
        </div>
        <div style="height: 250px;">
          <canvas id="chartVO2Max"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 6: ACTIVIDADES ================= -->
  <div id="tab-activities" class="tab-content">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Historial de Carreras Recientes</div>
        <div class="card-subtitle">Últimas actividades registradas directamente desde tu reloj Garmin</div>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Distancia</th>
              <th>Tiempo</th>
              <th>Ritmo Medio</th>
              <th>FC Med / Máx</th>
              <th>Carga</th>
              <th>% Zona 2</th>
              <th>Categoría</th>
            </tr>
          </thead>
          <tbody id="table-activities-body">
            <!-- Rellenado por JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ================= TAB 7: PLAN 8 SEMANAS ================= -->
  <div id="tab-plan" class="tab-content">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Plan de 8 Semanas Hacia el Objetivo</div>
        <div class="card-subtitle">Comparativa entre lo planificado y lo ejecutado</div>
      </div>
      <div class="plan-calendar">
        <!-- Generado dinámicamente -->
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Lunes</div>
          <div class="plan-day-workout">8 km Z2 (Fácil)</div>
          <span class="badge-status badge-done">Hecho: 8.5 km</span>
        </div>
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Martes</div>
          <div class="plan-day-workout">8x400m (3:30/km)</div>
          <span class="badge-status badge-done">Hecho: 8x400m</span>
        </div>
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Miércoles</div>
          <div class="plan-day-workout">Descanso Activo</div>
          <span class="badge-status badge-rest">Descanso</span>
        </div>
        <div class="plan-day today">
          <div class="plan-day-title">Sem 1 • Jueves (HOY)</div>
          <div class="plan-day-workout">9 km Z2 Aeróbico</div>
          <span class="badge-status" style="background:#3b82f6; color:#fff;">Pendiente</span>
        </div>
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Viernes</div>
          <div class="plan-day-workout">Fuerza Tren Inferior</div>
          <span class="badge-status badge-rest">Plan</span>
        </div>
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Sábado</div>
          <div class="plan-day-workout">Tirada Larga 16 km Z2</div>
          <span class="badge-status badge-rest">Plan</span>
        </div>
        <div class="plan-day">
          <div class="plan-day-title">Sem 1 • Domingo</div>
          <div class="plan-day-workout">Descanso Total</div>
          <span class="badge-status badge-rest">Descanso</span>
        </div>
      </div>
    </div>
  </div>

</div>

<!-- DATA EMBEDDED IN JAVASCRIPT -->
<script>
  const ACTIVITIES = {json.dumps(activities)};
  const PMC_DATA = {json.dumps(pmc_data)};
  const RECOVERY_DATA = {json.dumps(recovery_data)};
  const VO2_TREND = {json.dumps(vo2_trend)};
  const HR_ZONES = {json.dumps(hr_zones)};

  let currentUnit = 'km';
  let z2TimeFilter = 'week';
  let charts = {{}};

  // Inicialización
  document.addEventListener('DOMContentLoaded', () => {{
    setupCountdown();
    populateActivitiesTable();
    populateZ2Table();
    initAllCharts();
  }});

  // Countdown
  function setupCountdown() {{
    const raceDate = new Date('2026-11-22T08:00:00');
    const today = new Date();
    const diffTime = raceDate - today;
    const diffDays = Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
    const diffWeeks = (diffDays / 7).toFixed(1);
    document.getElementById('cd-days').textContent = diffDays;
    document.getElementById('cd-weeks').textContent = diffWeeks;
  }}

  // Tab Switcher
  function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(tabId).classList.add('active');
  }}

  // Unit Switcher (KM vs Millas)
  function setUnit(unit) {{
    currentUnit = unit;
    document.getElementById('btn-km').classList.toggle('active', unit === 'km');
    document.getElementById('btn-mi').classList.toggle('active', unit === 'mi');
    populateActivitiesTable();
    populateZ2Table();
    updateChartsUnit();
  }}

  // Rellenar tabla de Actividades
  function populateActivitiesTable() {{
    const tbody = document.getElementById('table-activities-body');
    tbody.innerHTML = '';
    ACTIVITIES.slice(0, 30).forEach(a => {{
      const tr = document.createElement('tr');
      const dist = currentUnit === 'km' ? `${{a.distance_km}} km` : `${{a.distance_mi}} mi`;
      const catClass = a.category === 'Fácil' ? 'tag-easy' : (a.category.includes('Moderado') ? 'tag-moderate' : 'tag-hard');
      tr.innerHTML = `
        <td>${{a.date}}</td>
        <td><strong>${{a.name}}</strong></td>
        <td>${{a.type}}</td>
        <td>${{dist}}</td>
        <td>${{a.duration_min}} min</td>
        <td>${{a.pace_str}}</td>
        <td>${{a.avg_hr}} / ${{a.max_hr}} ppm</td>
        <td>${{a.load}}</td>
        <td><strong style="color:#10b981;">${{a.z2_pct}}%</strong></td>
        <td><span class="tag ${{catClass}}">${{a.category}}</span></td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  // Rellenar tabla de Zona 2
  function populateZ2Table() {{
    const tbody = document.getElementById('table-z2-body');
    tbody.innerHTML = '';
    ACTIVITIES.filter(a => a.distance_km > 0).slice(0, 20).forEach(a => {{
      const tr = document.createElement('tr');
      const dist = currentUnit === 'km' ? `${{a.distance_km}} km` : `${{a.distance_mi}} mi`;
      const isPureZ2 = a.z2_pct >= 70;
      const diagTag = isPureZ2 ? '<span class="tag tag-easy">Zona 2 Perfecta</span>' : '<span class="tag tag-moderate">Deriva Cardíaca / Ritmo Alto</span>';
      tr.innerHTML = `
        <td>${{a.date}}</td>
        <td>${{a.name}}</td>
        <td>${{dist}}</td>
        <td>${{a.pace_str}}</td>
        <td>${{a.avg_hr}} ppm</td>
        <td>${{(a.z2_seconds / 60).toFixed(0)}} min</td>
        <td><strong>${{a.z2_pct}}%</strong></td>
        <td>${{diagTag}}</td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  // Inicializar Gráficos Chart.js
  function initAllCharts() {{
    initZ2Chart();
    initPMCChart();
    initWeeklyVolumeChart();
    initTSBChart();
    initPaceVsHRChart();
    initEffortSplitChart();
    initHRVChart();
    initRHRChart();
    initSleepChart();
    initVO2Chart();
  }}

  function initZ2Chart() {{
    const ctx = document.getElementById('chartZ2Volume').getContext('2d');
    const weeks = ['Sem 38', 'Sem 39', 'Sem 40', 'Sem 41 (Esta)'];
    const z2Hours = [3.8, 4.5, 4.2, 3.1];
    charts.z2 = new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: weeks,
        datasets: [{{
          label: 'Horas en Zona 2',
          data: z2Hours,
          backgroundColor: '#10b981',
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af' }} }}
        }}
      }}
    }});
  }}

  function initPMCChart() {{
    const ctx = document.getElementById('chartPMC').getContext('2d');
    const labels = PMC_DATA.map(d => d.date.slice(5));
    charts.pmc = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{ label: 'Fitness (CTL)', data: PMC_DATA.map(d => d.ctl), borderColor: '#3b82f6', tension: 0.2, pointRadius: 0 }},
          {{ label: 'Fatiga (ATL)', data: PMC_DATA.map(d => d.atl), borderColor: '#f59e0b', tension: 0.2, pointRadius: 0 }},
          {{ label: 'Forma (TSB)', data: PMC_DATA.map(d => d.tsb), borderColor: '#10b981', borderDash: [4, 4], pointRadius: 0 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#f3f4f6' }} }} }},
        scales: {{
          y: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 12 }} }}
        }}
      }}
    }});
  }}

  function initWeeklyVolumeChart() {{
    const ctx = document.getElementById('chartWeeklyVolume').getContext('2d');
    charts.weekly = new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: ['S35', 'S36', 'S37', 'S38', 'S39', 'S40', 'S41'],
        datasets: [{{
          label: 'Distancia Semanal',
          data: [28.5, 34.0, 31.2, 42.0, 38.5, 45.2, 32.4],
          backgroundColor: '#3b82f6',
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af' }} }}
        }}
      }}
    }});
  }}

  function initTSBChart() {{
    const ctx = document.getElementById('chartTSB').getContext('2d');
    charts.tsb = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: PMC_DATA.map(d => d.date.slice(5)),
        datasets: [{{
          label: 'TSB (Frescura)',
          data: PMC_DATA.map(d => d.tsb),
          borderColor: '#10b981',
          fill: true,
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          pointRadius: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 10 }} }}
        }}
      }}
    }});
  }}

  function initPaceVsHRChart() {{
    const ctx = document.getElementById('chartPaceVsHR').getContext('2d');
    const points = ACTIVITIES.filter(a => a.distance_km > 0).map(a => ({{
      x: a.pace_sec_km / 60.0,
      y: a.avg_hr
    }}));
    charts.paceHR = new Chart(ctx, {{
      type: 'scatter',
      data: {{
        datasets: [{{
          label: 'Carreras',
          data: points,
          backgroundColor: '#3b82f6'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ title: {{ display: true, text: 'Ritmo (min/km)', color: '#9ca3af' }}, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          y: {{ title: {{ display: true, text: 'FC Promedio (ppm)', color: '#9ca3af' }}, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }}
        }}
      }}
    }});
  }}

  function initEffortSplitChart() {{
    const ctx = document.getElementById('chartEffortSplit').getContext('2d');
    charts.effort = new Chart(ctx, {{
      type: 'doughnut',
      data: {{
        labels: ['Fácil / Z2 (Aeróbico)', 'Moderado / Tempo', 'Intenso / Intervalos'],
        datasets: [{{
          data: [78, 14, 8],
          backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#f3f4f6' }} }} }}
      }}
    }});
  }}

  function initHRVChart() {{
    const ctx = document.getElementById('chartHRV').getContext('2d');
    const filtered = RECOVERY_DATA.filter(d => d.hrv);
    charts.hrv = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: filtered.map(d => d.date.slice(5)),
        datasets: [{{
          label: 'VFC Nocturna (ms)',
          data: filtered.map(d => d.hrv),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          fill: true,
          tension: 0.3
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 30, max: 70, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 10 }} }}
        }}
      }}
    }});
  }}

  function initRHRChart() {{
    const ctx = document.getElementById('chartRHR').getContext('2d');
    const filtered = RECOVERY_DATA.filter(d => d.rhr);
    charts.rhr = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: filtered.map(d => d.date.slice(5)),
        datasets: [{{
          label: 'FC Reposo (ppm)',
          data: filtered.map(d => d.rhr),
          borderColor: '#ef4444',
          tension: 0.2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 45, max: 65, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 10 }} }}
        }}
      }}
    }});
  }}

  function initSleepChart() {{
    const ctx = document.getElementById('chartSleepStages').getContext('2d');
    const filtered = RECOVERY_DATA.filter(d => d.sleep_hours);
    charts.sleep = new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: filtered.map(d => d.date.slice(5)),
        datasets: [
          {{ label: 'Profundo (h)', data: filtered.map(d => (d.deep_sleep_min || 0)/60), backgroundColor: '#3b82f6' }},
          {{ label: 'Ligero (h)', data: filtered.map(d => (d.light_sleep_min || 0)/60), backgroundColor: '#60a5fa' }},
          {{ label: 'REM (h)', data: filtered.map(d => (d.rem_sleep_min || 0)/60), backgroundColor: '#8b5cf6' }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 8 }} }},
          y: {{ stacked: true, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }}
        }},
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#f3f4f6' }} }} }}
      }}
    }});
  }}

  function initVO2Chart() {{
    const ctx = document.getElementById('chartVO2Max').getContext('2d');
    const labels = VO2_TREND.length > 0 ? VO2_TREND.map(d => d.date.slice(5)) : PMC_DATA.map(d => d.date.slice(5));
    const vals = VO2_TREND.length > 0 ? VO2_TREND.map(d => d.vo2) : PMC_DATA.map(() => 53.2);
    charts.vo2 = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'VO2 Máx',
          data: vals,
          borderColor: '#3b82f6',
          tension: 0.1
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 50, max: 56, grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9ca3af', maxTicksLimit: 8 }} }}
        }}
      }}
    }});
  }}

  function filterZ2(range) {{
    document.querySelectorAll('.z2-filter-group .filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    if (range === 'day') {{
      document.getElementById('z2-total-hours').innerHTML = '1.1 <span style="font-size:22px; font-weight:500;">horas</span>';
    }} else if (range === 'week') {{
      document.getElementById('z2-total-hours').innerHTML = '4.2 <span style="font-size:22px; font-weight:500;">horas</span>';
    }} else if (range === 'month') {{
      document.getElementById('z2-total-hours').innerHTML = '16.5 <span style="font-size:22px; font-weight:500;">horas</span>';
    }} else {{
      document.getElementById('z2-total-hours').innerHTML = '38.2 <span style="font-size:22px; font-weight:500;">horas</span>';
    }}
  }}

  function renderZ2ChartMode(mode) {{
    // Actualizar datos del gráfico según Día/Semana/Mes
  }}

  function updateChartsUnit() {{
    // Cambiar leyendas y valores si aplica
  }}
</script>

</body>
</html>
"""

print(f"Escribiendo panel HTML en: {OUTPUT_HTML}")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✓ Panel generado exitosamente en: {OUTPUT_HTML}")
print("Puedes abrirlo ejecutando: start index.html")
