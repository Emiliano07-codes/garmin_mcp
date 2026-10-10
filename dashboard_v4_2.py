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
    print("Error: Se requiere garminconnect. Ejecuta con: uv run python dashboard_v3_1.py")
    sys.exit(1)

TOKEN_STORE = os.environ.get("GARMINTOKENS") or os.path.expanduser("~/.garminconnect")
OUTPUT_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_v4_2.html")

print("=============================================================")
print("Generando Panel Garmin V4.2: Coherencia Cromática, Predicciones,")
print("Racha de Entrenamiento y Gráfico Oficial de Carga Firstbeat")
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
    profile_data["vo2_max"] = user_data.get("vo2MaxRunning", 53.0)
    profile_data["threshold_hr"] = user_data.get("lactateThresholdHeartRate", 179)
except Exception as e:
    print(f"Aviso perfil: {e}")

# 2. Récords Personales (PRs) con Historial Anterior y Proyección Firstbeat
personal_records = {
    "1k": {
        "time_str": "3:25", "pace": "3:25/km", "date": "19/04/2026", "activity": "Ciudad de Buenos Aires - 4 x 1000", "status": "Confirmado",
        "prev_time_str": "3:34", "prev_date": "12/11/2025", "delta_str": "-9s (Mejora: 4.2%)", "prediction_target": "3:20 proyectado"
    },
    "1mi": {
        "time_str": "6:10", "pace": "3:50/km", "date": "10/05/2025", "activity": "Ciudad de Buenos Aires - 2x2200", "status": "Confirmado",
        "prev_time_str": "6:28", "prev_date": "15/09/2024", "delta_str": "-18s (Mejora: 4.6%)", "prediction_target": "6:05 proyectado"
    },
    "5k": {
        "time_str": "20:28", "pace": "4:05/km", "date": "14/09/2024", "activity": "General Pueyrredón Carrera", "status": "Confirmado",
        "prev_time_str": "21:10", "prev_date": "08/06/2024", "delta_str": "-42s (Mejora: 3.3%)", "prediction_target": "20:49 (Proyección Firstbeat)"
    },
    "10k": {
        "time_str": "41:16", "pace": "4:07/km", "date": "14/09/2024", "activity": "General Pueyrredón Carrera", "status": "Confirmado",
        "prev_time_str": "43:40", "prev_date": "11/05/2024", "delta_str": "-2m 24s (Mejora: 5.5%)", "prediction_target": "43:35 (Proyección Firstbeat)"
    },
    "21k": {
        "time_str": "1:27:16", "pace": "4:08/km", "date": "14/09/2024", "activity": "General Pueyrredón Carrera", "status": "Confirmado",
        "prev_time_str": "1:31:00", "prev_date": "21/04/2024", "delta_str": "-3m 44s (Mejora: 4.1%)", "prediction_target": "1:35:06 (Proyección Firstbeat)"
    },
    "42k": {
        "time_str": "--:--:--", "pace": "--", "date": "--", "activity": "Objetivo Maratón", "status": "En preparación",
        "prev_time_str": "Debut Próximo", "prev_date": "--", "delta_str": "En construcción de base CTL", "prediction_target": "3:36:48 (Proyección Firstbeat)"
    }
}
try:
    for pr in (client.get_personal_record() or []):
        if pr.get("activityType") == "running":
            tid = pr.get("typeId")
            val = float(pr.get("value") or 0.0)
            if tid == 1 and val > 0:
                m = int(val // 60); s = int(val % 60)
                personal_records["1k"]["time_str"] = f"{m}:{s:02d}"
                personal_records["1k"]["pace"] = f"{m}:{s:02d}/km"
            elif tid == 2 and val > 0:
                m = int(val // 60); s = int(val % 60)
                personal_records["1mi"]["time_str"] = f"{m}:{s:02d}"
            elif tid == 3 and val > 0:
                m = int(val // 60); s = int(val % 60)
                personal_records["5k"]["time_str"] = f"{m}:{s:02d}"
                personal_records["5k"]["pace"] = f"{int(val/5//60)}:{int(val/5%60):02d}/km"
            elif tid == 4 and val > 0:
                m = int(val // 60); s = int(val % 60)
                personal_records["10k"]["time_str"] = f"{m}:{s:02d}"
                personal_records["10k"]["pace"] = f"{int(val/10//60)}:{int(val/10%60):02d}/km"
            elif tid == 5 and val > 0:
                h = int(val // 3600); rem = val % 3600; m = int(rem // 60); s = int(rem % 60)
                personal_records["21k"]["time_str"] = f"{h}:{m:02d}:{s:02d}"
                personal_records["21k"]["pace"] = f"{int(val/21.0975//60)}:{int(val/21.0975%60):02d}/km"
except Exception as e:
    print(f"Aviso parseo PRs: {e}")

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
            {"zone": 1, "floor": z.get("zone1Floor", 116), "name": "Z1 Recuperación (< " + str(z.get("zone2Floor", 142)) + " ppm)"},
            {"zone": 2, "floor": z.get("zone2Floor", 142), "name": "Z2 Base Aeróbica (" + str(z.get("zone2Floor", 142)) + " - " + str(z.get("zone3Floor", 158)) + " ppm)"},
            {"zone": 3, "floor": z.get("zone3Floor", 158), "name": "Z3 Tempo (" + str(z.get("zone3Floor", 158)) + " - " + str(z.get("zone4Floor", 169)) + " ppm)"},
            {"zone": 4, "floor": z.get("zone4Floor", 169), "name": "Z4 Umbral Lactato (" + str(z.get("zone4Floor", 169)) + " - " + str(z.get("zone5Floor", 178)) + " ppm)"},
            {"zone": 5, "floor": z.get("zone5Floor", 178), "name": "Z5 Anaeróbico (> " + str(z.get("zone5Floor", 178)) + " ppm)"}
        ]
except Exception: pass

# 3.1 Predicciones Oficiales de Carrera (Garmin Race Predictions)
race_predictions_payload = {
    "5k": {"seconds": 1249, "time_str": "20:49", "pace": "4:09/km"},
    "10k": {"seconds": 2615, "time_str": "43:35", "pace": "4:21/km"},
    "21k": {"seconds": 5706, "time_str": "1:35:06", "pace": "4:30/km"},
    "42k": {"seconds": 13008, "time_str": "3:36:48", "pace": "5:08/km"}
}
try:
    rp = client.get_race_predictions() or {}
    t5 = rp.get("time5K", 1249)
    t10 = rp.get("time10K", 2615)
    t21 = rp.get("timeHalfMarathon", 5706)
    t42 = rp.get("timeMarathon", 13008)
    if t5:
        m = int(t5 // 60); s = int(t5 % 60)
        race_predictions_payload["5k"] = {"seconds": t5, "time_str": f"{m}:{s:02d}", "pace": f"{int(t5/5//60)}:{int(t5/5%60):02d}/km"}
    if t10:
        m = int(t10 // 60); s = int(t10 % 60)
        race_predictions_payload["10k"] = {"seconds": t10, "time_str": f"{m}:{s:02d}", "pace": f"{int(t10/10//60)}:{int(t10/10%60):02d}/km"}
    if t21:
        h = int(t21 // 3600); rem = t21 % 3600; m = int(rem // 60); s = int(rem % 60)
        race_predictions_payload["21k"] = {"seconds": t21, "time_str": f"{h}:{m:02d}:{s:02d}", "pace": f"{int(t21/21.0975//60)}:{int(t21/21.0975%60):02d}/km"}
    if t42:
        h = int(t42 // 3600); rem = t42 % 3600; m = int(rem // 60); s = int(rem % 60)
        race_predictions_payload["42k"] = {"seconds": t42, "time_str": f"{h}:{m:02d}:{s:02d}", "pace": f"{int(t42/42.195//60)}:{int(t42/42.195%60):02d}/km"}
except Exception as e:
    print(f"Aviso race predictions: {e}")

# 3.1.1 Historial Evolutivo de Predicciones de Carrera (Últimos 6 meses)
race_predictions_history = []
try:
    rp_start = (today_date - datetime.timedelta(days=180)).isoformat()
    rp_end = today_str
    rp_daily_raw = client.get_race_predictions(rp_start, rp_end, "daily") or []
    for item in rp_daily_raw:
        c_date = item.get("calendarDate")
        if not c_date:
            continue
        d_obj = datetime.date.fromisoformat(c_date)
        d_arg = f"{d_obj.day:02d}/{d_obj.month:02d}"
        s5 = item.get("time5K") or race_predictions_payload["5k"]["seconds"]
        s10 = item.get("time10K") or race_predictions_payload["10k"]["seconds"]
        s21 = item.get("timeHalfMarathon") or race_predictions_payload["21k"]["seconds"]
        s42 = item.get("timeMarathon") or race_predictions_payload["42k"]["seconds"]
        race_predictions_history.append({
            "iso_date": c_date,
            "date_arg": d_arg,
            "time5K": s5,
            "time10K": s10,
            "timeHalfMarathon": s21,
            "timeMarathon": s42,
            "time5K_str": f"{int(s5//60)}:{int(s5%60):02d}",
            "time10K_str": f"{int(s10//60)}:{int(s10%60):02d}",
            "timeHalfMarathon_str": f"{int(s21//3600)}:{int((s21%3600)//60):02d}:{int(s21%60):02d}",
            "timeMarathon_str": f"{int(s42//3600)}:{int((s42%3600)//60):02d}:{int(s42%60):02d}"
        })
except Exception as e:
    print(f"Aviso descarga historial de predicciones: {e}")

# Cálculo de Deltas Favorable / Desfavorable (vs 30 días atrás o primer registro)
pred_deltas = {"5k": {"text": "▼ 42s", "favorable": True}, "10k": {"text": "▼ 1m 15s", "favorable": True}, "21k": {"text": "▼ 2m 30s", "favorable": True}, "42k": {"text": "▼ 5m 12s", "favorable": True}}
if len(race_predictions_history) > 30:
    past_item = race_predictions_history[-30]
    curr_item = race_predictions_history[-1]
    
    for dist_key, raw_field in [("5k", "time5K"), ("10k", "time10K"), ("21k", "timeHalfMarathon"), ("42k", "timeMarathon")]:
        diff_sec = curr_item[raw_field] - past_item[raw_field]
        is_fav = diff_sec <= 0
        abs_diff = abs(diff_sec)
        if abs_diff >= 60:
            diff_str = f"{abs_diff//60}m {abs_diff%60}s"
        else:
            diff_str = f"{abs_diff}s"
        arrow = "▼" if is_fav else "▲"
        pred_deltas[dist_key] = {
            "text": f"{arrow} {diff_str}",
            "favorable": is_fav
        }

# 3.2 Predisposición al Entrenamiento (Training Readiness)
readiness_payload = {
    "score": 50,
    "level": "MODERATE",
    "recovery_time_hours": 24,
    "sleep_factor_percent": 68,
    "sleep_factor_feedback": "MODERATE",
    "hrv_factor_percent": 96,
    "hrv_factor_feedback": "GOOD",
    "stress_factor_percent": 96,
    "stress_factor_feedback": "GOOD",
    "acute_load_factor_percent": 83,
    "acute_load_factor_feedback": "GOOD",
    "feedback_short": "Descanso y carga equilibrados"
}
try:
    tr_list = client.get_training_readiness(today_str)
    if tr_list and isinstance(tr_list, list) and len(tr_list) > 0:
        tr0 = tr_list[0]
        readiness_payload["score"] = tr0.get("score", 50)
        readiness_payload["level"] = tr0.get("level", "MODERATE")
        rt_min = tr0.get("recoveryTime", 1440)
        readiness_payload["recovery_time_hours"] = round(rt_min / 60.0, 1)
        readiness_payload["sleep_factor_percent"] = tr0.get("sleepScoreFactorPercent", 68)
        readiness_payload["sleep_factor_feedback"] = tr0.get("sleepScoreFactorFeedback", "MODERATE")
        readiness_payload["hrv_factor_percent"] = tr0.get("hrvFactorPercent", 96)
        readiness_payload["hrv_factor_feedback"] = tr0.get("hrvFactorFeedback", "GOOD")
        readiness_payload["stress_factor_percent"] = tr0.get("stressHistoryFactorPercent", 96)
        readiness_payload["acute_load_factor_percent"] = tr0.get("acwrFactorPercent", 83)
        readiness_payload["feedback_short"] = str(tr0.get("feedbackShort", "Recuperación en curso")).replace("_", " ").title()
except Exception as e:
    print(f"Aviso readiness: {e}")

# 4. Estado de Entreno Oficial & Foco de Carga Firstbeat (Training Load Balance)
print("Consultando Estado de Entreno y Foco de Carga Firstbeat...")
training_status_payload = {
    "status_code": 7,
    "status_title": "Productivo",
    "fitness_trend_code": 3,
    "fitness_trend_title": "Mejorando",
    "acute_load": 603,
    "chronic_load": 505,
    "min_tunnel": 404,
    "max_tunnel": 758,
    "vo2_precise": 53.4,
    "feedback_phrase": "Tu carga de entrenamiento actual está en un nivel óptimo y mejora tu condición física.",
    "load_balance": {
        "aerobic_low": 653,
        "aerobic_low_min": 317,
        "aerobic_low_max": 718,
        "aerobic_high": 661,
        "aerobic_high_min": 416,
        "aerobic_high_max": 817,
        "anaerobic": 501,
        "anaerobic_min": 133,
        "anaerobic_max": 400,
        "feedback": "Foco Anaeróbico Elevado"
    },
    "history": []
}

try:
    ts_today = client.get_training_status(today_str) or {}
    ltd = ts_today.get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData", {})
    for dev in ltd.values():
        if isinstance(dev, dict):
            training_status_payload["status_code"] = dev.get("trainingStatus", 7)
            training_status_payload["fitness_trend_code"] = dev.get("fitnessTrend", 3)
            atl_dto = dev.get("acuteTrainingLoadDTO", {})
            training_status_payload["acute_load"] = atl_dto.get("dailyTrainingLoadAcute", 603)
            training_status_payload["chronic_load"] = atl_dto.get("dailyTrainingLoadChronic", 505)
            training_status_payload["min_tunnel"] = round(atl_dto.get("minTrainingLoadChronic", 404.0))
            training_status_payload["max_tunnel"] = round(atl_dto.get("maxTrainingLoadChronic", 758.0))
            break
    
    # VO2 Preciso
    v_prec = ts_today.get("mostRecentVO2Max", {}).get("generic", {}).get("vo2MaxPreciseValue")
    if v_prec:
        training_status_payload["vo2_precise"] = float(v_prec)

    # Foco de Carga Firstbeat
    tlb_map = ts_today.get("mostRecentTrainingLoadBalance", {}).get("metricsTrainingLoadBalanceDTOMap", {})
    for tlb_dev in tlb_map.values():
        if isinstance(tlb_dev, dict):
            training_status_payload["load_balance"]["aerobic_low"] = round(tlb_dev.get("monthlyLoadAerobicLow", 653))
            training_status_payload["load_balance"]["aerobic_low_min"] = round(tlb_dev.get("monthlyLoadAerobicLowTargetMin", 317))
            training_status_payload["load_balance"]["aerobic_low_max"] = round(tlb_dev.get("monthlyLoadAerobicLowTargetMax", 718))
            training_status_payload["load_balance"]["aerobic_high"] = round(tlb_dev.get("monthlyLoadAerobicHigh", 661))
            training_status_payload["load_balance"]["aerobic_high_min"] = round(tlb_dev.get("monthlyLoadAerobicHighTargetMin", 416))
            training_status_payload["load_balance"]["aerobic_high_max"] = round(tlb_dev.get("monthlyLoadAerobicHighTargetMax", 817))
            training_status_payload["load_balance"]["anaerobic"] = round(tlb_dev.get("monthlyLoadAnaerobic", 501))
            training_status_payload["load_balance"]["anaerobic_min"] = round(tlb_dev.get("monthlyLoadAnaerobicTargetMin", 133))
            training_status_payload["load_balance"]["anaerobic_max"] = round(tlb_dev.get("monthlyLoadAnaerobicTargetMax", 400))
            raw_feed = tlb_dev.get("trainingBalanceFeedbackPhrase", "ANAEROBIC_FOCUS")
            feed_dict = {
                "ANAEROBIC_FOCUS": "Foco Anaeróbico (Estimulación de alta intensidad)",
                "AEROBIC_HIGH_FOCUS": "Foco Aeróbico Alto (Tempo y Umbral)",
                "AEROBIC_LOW_FOCUS": "Foco Aeróbico Bajo (Base y Zona 2)",
                "BALANCED": "Equilibrio Óptimo de Carga"
            }
            training_status_payload["load_balance"]["feedback"] = feed_dict.get(raw_feed, "Carga de Entrenamiento Diversificada")
            break
except Exception as e:
    print(f"Aviso training status y load balance: {e}")

# Muestreo histórico de Training Status (últimos 6 meses, paso semanal)
status_names = {
    1: "Desentrenamiento",
    2: "Recuperación",
    3: "Mantenimiento",
    4: "Productivo",
    5: "Pico de Forma",
    6: "Sobreesfuerzo",
    7: "Productivo",
    8: "Cansado"
}
status_colors = {
    "Productivo": "#10b981",
    "Pico de Forma": "#38bdf8",
    "Mantenimiento": "#f59e0b",
    "Recuperación": "#60a5fa",
    "Sobreesfuerzo": "#ef4444",
    "Desentrenamiento": "#94a3b8",
    "Cansado": "#f97316"
}

print("Descargando serie histórica de Estado de Entreno...")
for d_back in range(0, 168, 7):
    d_check = (today_date - datetime.timedelta(days=d_back)).isoformat()
    try:
        ts = client.get_training_status(d_check) or {}
        ltd = ts.get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData", {})
        for dev in ltd.values():
            if isinstance(dev, dict):
                sc = dev.get("trainingStatus", 3)
                sname = status_names.get(sc, "Productivo")
                ft = dev.get("fitnessTrend", 2)
                d_obj = datetime.date.fromisoformat(d_check)
                training_status_payload["history"].append({
                    "date": d_check,
                    "date_arg": f"{d_obj.day:02d}/{d_obj.month:02d}",
                    "status_code": sc,
                    "status_title": sname,
                    "color": status_colors.get(sname, "#10b981"),
                    "trend_code": ft
                })
                break
    except Exception: pass

# Invertir para orden cronológico
training_status_payload["history"].reverse()

# 5. Extracción de Actividades Completas (Hasta 500 para cubrir todo el historial)
print("Descargando historial completo de actividades (2022 a la fecha)...")
raw_activities = []
try:
    total_count = client.count_activities() or 457
    raw_activities = client.get_activities(0, min(total_count, 500)) or []
    if isinstance(raw_activities, dict):
        raw_activities = raw_activities.get("activities", [])
except Exception as e:
    print(f"Error descargando actividades: {e}")

activities = []
weekly_all_strava = {}

for idx, a in enumerate(raw_activities):
    aid = a.get("activityId") or a.get("id")
    name = a.get("activityName") or a.get("name") or "Actividad"
    atype = a.get("activityType", {}).get("typeKey") if isinstance(a.get("activityType"), dict) else a.get("type", "running")
    start_time = a.get("startTimeLocal") or a.get("start_time") or ""
    dist_m = float(a.get("distance") or a.get("distance_meters") or 0.0)
    dur_s = float(a.get("duration") or a.get("duration_seconds") or 0.0)
    elev_m = float(a.get("elevationGain") or a.get("totalElevationGain") or 0.0)
    avg_hr = float(a.get("averageHR") or a.get("avg_hr_bpm") or 0.0)
    max_hr = float(a.get("maxHR") or a.get("max_hr_bpm") or 0.0)
    load = float(a.get("activityTrainingLoad") or 0.0)
    calories = float(a.get("calories") or 0.0)
    aerobic_te = float(a.get("aerobicTrainingEffect") or 0.0)
    anaerobic_te = float(a.get("anaerobicTrainingEffect") or 0.0)

    # Clasificación deportiva
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

    intensity_tag = "Moderado"
    if sport_category == "Carrera":
        if avg_hr > 160 or "interval" in name.lower() or "8x" in name.lower() or "series" in name.lower() or "tempo" in name.lower():
            intensity_tag = "Intenso / Series"
        elif avg_hr <= 148 or "fácil" in name.lower() or "easy" in name.lower() or "fondo" in name.lower():
            intensity_tag = "Fácil / Base Z2"
        else:
            intensity_tag = "Moderado / Mixto"
    elif sport_category == "Gimnasio / Fuerza":
        intensity_tag = "Fuerza Estructural"
    elif sport_category == "Caminata":
        intensity_tag = "Recuperación Activa"

    pace_sec_km = (dur_s / (dist_m / 1000.0)) if dist_m > 0 else 0
    pace_min = int(pace_sec_km // 60)
    pace_sec = int(pace_sec_km % 60)
    pace_str = f"{pace_min}:{pace_sec:02d}/km" if dist_m > 0 else "-"

    z1_s, z2_s, z3_s, z4_s, z5_s = 0, 0, 0, 0, 0
    tz_fetched = False
    if idx < 12:
        try:
            tz = client.get_activity_hr_in_timezones(aid)
            if tz and isinstance(tz, list) and len(tz) > 0:
                for tzone in tz:
                    znum = tzone.get("zoneNumber")
                    s = float(tzone.get("secsInZone", 0))
                    if znum == 1: z1_s = s
                    elif znum == 2: z2_s = s
                    elif znum == 3: z3_s = s
                    elif znum == 4: z4_s = s
                    elif znum == 5: z5_s = s
                tz_fetched = True
        except Exception:
            pass

    if not tz_fetched:
        if avg_hr > 0 and dur_s > 0:
            if avg_hr < 142:
                z1_s = dur_s * 0.70; z2_s = dur_s * 0.30
            elif avg_hr <= 152:
                z1_s = dur_s * 0.15; z2_s = dur_s * 0.75; z3_s = dur_s * 0.10
            elif avg_hr <= 165:
                z1_s = dur_s * 0.05; z2_s = dur_s * 0.25; z3_s = dur_s * 0.55; z4_s = dur_s * 0.15
            elif avg_hr <= 175:
                z2_s = dur_s * 0.10; z3_s = dur_s * 0.30; z4_s = dur_s * 0.45; z5_s = dur_s * 0.15
            else:
                z3_s = dur_s * 0.15; z4_s = dur_s * 0.45; z5_s = dur_s * 0.40

    z2_pct = round((z2_s / dur_s) * 100, 1) if dur_s > 0 else 0

    iso_date = start_time[:10] if start_time else ""
    arg_date = ""
    time_part = ""
    if iso_date:
        parts = iso_date.split("-")
        if len(parts) == 3:
            arg_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
    if len(start_time) >= 16:
        time_part = start_time[11:16]

    # Agrupación por semana calendario completa para navegación infinita
    if iso_date:
        try:
            dt = datetime.date.fromisoformat(iso_date)
            monday = dt - datetime.timedelta(days=dt.weekday())
            w_str = monday.isoformat()
            if w_str not in weekly_all_strava:
                weekly_all_strava[w_str] = {
                    "start_date": w_str,
                    "year": monday.year,
                    "label": f"{monday.day:02d}/{monday.month:02d}",
                    "month_name": ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"][monday.month - 1],
                    "dist_km": 0.0,
                    "dur_s": 0.0,
                    "elev_m": 0.0,
                    "z2_s": 0.0,
                    "load": 0.0,
                    "activities": 0
                }
            weekly_all_strava[w_str]["dist_km"] += (dist_m / 1000.0)
            weekly_all_strava[w_str]["dur_s"] += dur_s
            weekly_all_strava[w_str]["elev_m"] += elev_m
            weekly_all_strava[w_str]["z2_s"] += z2_s
            weekly_all_strava[w_str]["load"] += load
            weekly_all_strava[w_str]["activities"] += 1
        except Exception: pass

    activities.append({
        "id": aid,
        "name": name,
        "type": atype,
        "sport": sport_category,
        "intensity": intensity_tag,
        "iso_date": iso_date,
        "date_arg": arg_date,
        "time_part": time_part,
        "datetime": start_time,
        "distance_km": round(dist_m / 1000.0, 2),
        "duration_min": round(dur_s / 60.0, 1),
        "duration_hours": round(dur_s / 3600.0, 2),
        "duration_sec": dur_s,
        "elevation_m": round(elev_m),
        "pace_str": pace_str,
        "pace_sec_km": pace_sec_km,
        "avg_hr": round(avg_hr),
        "max_hr": round(max_hr),
        "load": round(load, 1),
        "calories": round(calories),
        "aerobic_te": aerobic_te,
        "anaerobic_te": anaerobic_te,
        "z1_sec": round(z1_s),
        "z2_sec": round(z2_s),
        "z3_sec": round(z3_s),
        "z4_sec": round(z4_s),
        "z5_sec": round(z5_s),
        "z1_min": round(z1_s / 60.0, 1),
        "z2_min": round(z2_s / 60.0, 1),
        "z3_min": round(z3_s / 60.0, 1),
        "z4_min": round(z4_s / 60.0, 1),
        "z5_min": round(z5_s / 60.0, 1),
        "z2_hours": round(z2_s / 3600.0, 2),
        "z2_pct": z2_pct
    })

print(f"✓ Total actividades sincronizadas: {len(activities)}")

# 6. Estructuración Continua del Histórico Completo de Semanas
current_monday = today_date - datetime.timedelta(days=today_date.weekday())
all_weeks_keys = sorted(weekly_all_strava.keys())
first_monday_str = all_weeks_keys[0] if all_weeks_keys else "2022-06-06"
first_monday = datetime.date.fromisoformat(first_monday_str)

full_timeline_weeks = []
cur_w = first_monday
while cur_w <= current_monday:
    w_key = cur_w.isoformat()
    if w_key in weekly_all_strava:
        item = weekly_all_strava[w_key]
        full_timeline_weeks.append({
            "week_key": w_key,
            "year": cur_w.year,
            "label": f"{cur_w.day:02d}/{cur_w.month:02d}",
            "month": ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"][cur_w.month - 1],
            "dist_km": round(item["dist_km"], 2),
            "dur_hours": round(item["dur_s"] / 3600.0, 2),
            "dur_str": f"{int(item['dur_s']//3600)}h {int((item['dur_s']%3600)//60)}m",
            "elev_m": round(item["elev_m"]),
            "z2_hours": round(item["z2_s"] / 3600.0, 2),
            "load": round(item["load"], 1),
            "activities": item["activities"],
            "is_current": (cur_w == current_monday)
        })
    else:
        full_timeline_weeks.append({
            "week_key": w_key,
            "year": cur_w.year,
            "label": f"{cur_w.day:02d}/{cur_w.month:02d}",
            "month": ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"][cur_w.month - 1],
            "dist_km": 0.0,
            "dur_hours": 0.0,
            "dur_str": "0h 0m",
            "elev_m": 0,
            "z2_hours": 0.0,
            "load": 0.0,
            "activities": 0,
            "is_current": (cur_w == current_monday)
        })
    cur_w += datetime.timedelta(days=7)

print(f"✓ Total semanas procesadas en el histórico: {len(full_timeline_weeks)} semanas")

# 6.1 Matriz de Consistencia y Racha de Entrenamiento (Estilo Strava / GitHub Heatmap)
consistency_days_map = {}
for act in activities:
    d = act.get("iso_date")
    if d:
        if d not in consistency_days_map:
            consistency_days_map[d] = {"min": 0, "load": 0.0, "sports": []}
        consistency_days_map[d]["min"] += act.get("duration_min", 0)
        consistency_days_map[d]["load"] += act.get("load", 0.0)
        consistency_days_map[d]["sports"].append(act.get("sport", "Carrera"))

# Calcular racha de semanas activas consecutivas
weeks_with_training = set()
for d_str in consistency_days_map.keys():
    try:
        d_obj = datetime.date.fromisoformat(d_str)
        y, w, _ = d_obj.isocalendar()
        weeks_with_training.add((y, w))
    except Exception:
        pass

curr_y, curr_w, _ = today_date.isocalendar()
consecutive_active_weeks = 0
chk_y, chk_w = curr_y, curr_w
while (chk_y, chk_w) in weeks_with_training:
    consecutive_active_weeks += 1
    ref_d = datetime.date.fromisocalendar(chk_y, chk_w, 1) - datetime.timedelta(days=7)
    chk_y, chk_w, _ = ref_d.isocalendar()

# Generar cuadrícula de los últimos 364 días (52 semanas x 7 días)
heatmap_start = today_date - datetime.timedelta(days=363)
# Ajustar para que empiece en lunes
days_to_monday = heatmap_start.weekday()
heatmap_start = heatmap_start - datetime.timedelta(days=days_to_monday)

consistency_weeks_list = []
cur_day = heatmap_start
while cur_day <= today_date:
    week_days = []
    for dow in range(7):
        d_iso = cur_day.isoformat()
        day_stat = consistency_days_map.get(d_iso, {"min": 0, "load": 0.0, "sports": []})
        mins = day_stat["min"]
        level = 0
        if mins > 90: level = 4
        elif mins >= 60: level = 3
        elif mins >= 30: level = 2
        elif mins > 0: level = 1
        
        is_future = cur_day > today_date
        week_days.append({
            "iso_date": d_iso,
            "date_arg": f"{cur_day.day:02d}/{cur_day.month:02d}",
            "day_name": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][dow],
            "minutes": mins,
            "load": round(day_stat["load"], 1),
            "sports": ", ".join(list(set(day_stat["sports"]))) if day_stat["sports"] else "Descanso",
            "level": level if not is_future else -1,
            "is_today": (cur_day == today_date)
        })
        cur_day += datetime.timedelta(days=1)
    consistency_weeks_list.append(week_days)

current_week_stats = full_timeline_weeks[-1]

# 7. Curva PMC EWMA a 84 días
pmc_series = []
start_12w = today_date - datetime.timedelta(days=84)
current = start_12w

daily_loads = {}
daily_z2_hours = {}
for act in activities:
    d = act.get("iso_date")
    if d:
        daily_loads[d] = daily_loads.get(d, 0.0) + act.get("load", 0.0)
        daily_z2_hours[d] = daily_z2_hours.get(d, 0.0) + act.get("z2_hours", 0.0)

atl_ewma = 40.0
ctl_ewma = 35.0
z2_cum_running = 0.0
recent_z2_window = []

while current <= today_date:
    d_str = current.isoformat()
    day_load = daily_loads.get(d_str, 0.0)
    day_z2 = daily_z2_hours.get(d_str, 0.0)
    z2_cum_running += day_z2

    recent_z2_window.append(day_z2)
    if len(recent_z2_window) > 7:
        recent_z2_window.pop(0)
    sma7_z2 = round(sum(recent_z2_window) / len(recent_z2_window), 2)

    day_min_tunnel = round(ctl_ewma * 0.8)
    day_max_tunnel = round(ctl_ewma * 1.5)

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
                    g_min = atl_dto.get("minTrainingLoadChronic")
                    g_max = atl_dto.get("maxTrainingLoadChronic")
                    if g_atl: atl_ewma = float(g_atl)
                    if g_ctl: ctl_ewma = float(g_ctl)
                    if g_min: day_min_tunnel = round(float(g_min))
                    if g_max: day_max_tunnel = round(float(g_max))
                    break
    except Exception:
        atl_ewma = atl_ewma * (1 - 0.25) + day_load * 0.25
        ctl_ewma = ctl_ewma * (1 - 0.069) + day_load * 0.069
        day_min_tunnel = round(ctl_ewma * 0.8)
        day_max_tunnel = round(ctl_ewma * 1.5)

    tsb = ctl_ewma - atl_ewma
    acwr = round(atl_ewma / ctl_ewma, 2) if ctl_ewma > 0 else 1.0
    d_arg = f"{current.day:02d}/{current.month:02d}/{current.year}"

    curr_vo2 = profile_data.get("vo2_max", 53.0)
    daily_es = int(round((curr_vo2 * 45.0) + (min(ctl_ewma, 600.0) * 3.5) + (day_z2 * 25.0 * 4)))

    pmc_series.append({
        "iso_date": d_str,
        "date_arg": d_arg,
        "ctl": round(ctl_ewma, 1),
        "atl": round(atl_ewma, 1),
        "min_tunnel": day_min_tunnel,
        "max_tunnel": day_max_tunnel,
        "tsb": round(tsb, 1),
        "acwr": acwr,
        "day_load": round(day_load, 1),
        "day_z2": round(day_z2, 2),
        "z2_sma7": sma7_z2,
        "z2_cum": round(z2_cum_running, 2),
        "endurance_score": daily_es
    })
    current += datetime.timedelta(days=1)

# 8. Endurance Score y Métricas de Recuperación
current_vo2 = profile_data.get("vo2_max", 53.0)
last_ctl = pmc_series[-1]["ctl"] if pmc_series else 460.0
last_atl = pmc_series[-1]["atl"] if pmc_series else 537.0

recent_z2_hours = sum(a["z2_hours"] for a in activities if a["iso_date"] >= (today_date - datetime.timedelta(days=28)).isoformat())
base_score = (current_vo2 * 45.0) + (min(last_ctl, 600.0) * 3.5) + (recent_z2_hours * 25.0)
endurance_score = int(round(base_score))

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

recovery_metrics = []
start_4w = today_date - datetime.timedelta(days=28)
current = start_4w

daily_steps_map = {}
try:
    st_hist = client.get_daily_steps(start_4w.isoformat(), today_str) or []
    for s in st_hist:
        c_date = s.get("calendarDate")
        if c_date:
            daily_steps_map[c_date] = {
                "steps": s.get("totalSteps", 0),
                "km": round((s.get("totalDistance", 0) or 0) / 1000.0, 1)
            }
except Exception: pass

while current <= today_date:
    d_str = current.isoformat()
    d_arg = f"{current.day:02d}/{current.month:02d}/{current.year}"
    step_info = daily_steps_map.get(d_str, {"steps": 8500, "km": 8.5})
    entry = {
        "iso_date": d_str,
        "date_arg": d_arg,
        "hrv": None,
        "rhr": None,
        "sleep_hours": 7.0,
        "sleep_score": 75,
        "steps": step_info["steps"],
        "steps_km": step_info["km"]
    }
    try:
        hrv_res = client.get_hrv_data(d_str)
        if hrv_res and isinstance(hrv_res, dict):
            hs = hrv_res.get("hrvSummary") or {}
            entry["hrv"] = hs.get("lastNightAvg") or hs.get("weeklyAvg") or hrv_res.get("lastNightAvg")
            entry["hrv_baseline_low"] = hs.get("baseline", {}).get("balancedLow", 43)
            entry["hrv_baseline_high"] = hs.get("baseline", {}).get("balancedUpper", 56)
    except Exception: pass

    try:
        hr_sum = client.get_heart_rates(d_str)
        if hr_sum and isinstance(hr_sum, dict):
            entry["rhr"] = hr_sum.get("restingHeartRate")
    except Exception: pass

    if current >= (today_date - datetime.timedelta(days=7)):
        try:
            sl = client.get_sleep_data(d_str)
            if sl and isinstance(sl, dict):
                dto = sl.get("dailySleepDTO", {})
                secs = dto.get("sleepTimeSeconds", 0)
                sc = dto.get("sleepScores", {}).get("overall", {}).get("value", 0)
                if secs > 0: entry["sleep_hours"] = round(secs / 3600.0, 1)
                if sc > 0: entry["sleep_score"] = sc
                entry["deep_hours"] = round((dto.get("deepSleepSeconds") or 0) / 3600.0, 1)
                entry["light_hours"] = round((dto.get("lightSleepSeconds") or 0) / 3600.0, 1)
                entry["rem_hours"] = round((dto.get("remSleepSeconds") or 0) / 3600.0, 1)
                entry["awake_min"] = round((dto.get("awakeSleepSeconds") or 0) / 60.0)
                entry["nap_min"] = round((dto.get("napTimeSeconds") or 0) / 60.0)
                entry["sleep_stress"] = round(float(dto.get("avgSleepStress") or 20))
        except Exception: pass

    recovery_metrics.append(entry)
    current += datetime.timedelta(days=1)

today_recovery = recovery_metrics[-1]
today_sleep_hours = today_recovery.get("sleep_hours", 7.5) or 7.5
today_sleep_score = today_recovery.get("sleep_score", 79) or 79
today_deep_hours = today_recovery.get("deep_hours", 1.8) or 1.8
today_light_hours = today_recovery.get("light_hours", 4.8) or 4.8
today_rem_hours = today_recovery.get("rem_hours", 1.0) or 1.0
today_awake_min = today_recovery.get("awake_min", 4) or 4
today_nap_min = today_recovery.get("nap_min", 38) or 38
today_sleep_stress = today_recovery.get("sleep_stress", 23) or 23

# 9. Última Actividad Destacada
latest_act = activities[0] if activities else {
    "name": "Sin actividad reciente", "sport": "Carrera", "date_arg": "--", "time_part": "",
    "distance_km": 0, "duration_min": 0, "elevation_m": 0, "avg_hr": 0, "max_hr": 0, "load": 0, "pace_str": "-",
    "z2_pct": 0, "aerobic_te": 0, "anaerobic_te": 0,
    "z1_min": 0, "z2_min": 0, "z3_min": 0, "z4_min": 0, "z5_min": 0
}

# 10. Cálculo Dinámico de Colores de KPIs según Rango Fisiológico Real
current_vo2_val = float(training_status_payload.get('vo2_precise') or profile_data.get('vo2_max', 53.4))
if current_vo2_val >= 52:
    kpi_vo2_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Superior"}
elif current_vo2_val >= 49:
    kpi_vo2_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Excelente"}
elif current_vo2_val >= 42:
    kpi_vo2_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Bueno"}
else:
    kpi_vo2_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Ajustar"}

current_endurance_val = float(endurance_data_payload.get('score', 4450))
if current_endurance_val >= 4700:
    kpi_endurance_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Élite"}
elif current_endurance_val >= 4100:
    kpi_endurance_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Avanzado"}
elif current_endurance_val >= 3500:
    kpi_endurance_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Intermedio"}
else:
    kpi_endurance_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Inicial"}

current_acwr_val = float(pmc_series[-1].get('acwr', 1.05))
if 0.80 <= current_acwr_val <= 1.30:
    kpi_acwr_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Sweet Spot"}
elif 1.30 < current_acwr_val <= 1.50:
    kpi_acwr_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Alerta Carga"}
elif current_acwr_val > 1.50:
    kpi_acwr_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Zona Peligro"}
else:
    kpi_acwr_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Descarga"}

current_z2_val = float(endurance_data_payload.get('z2_hours_4w', 14.5))
if current_z2_val >= 18:
    kpi_z2_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Alto Volumen"}
elif current_z2_val >= 12:
    kpi_z2_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Óptimo 4s"}
elif current_z2_val >= 8:
    kpi_z2_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Mantenimiento"}
else:
    kpi_z2_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Bajo"}

current_hrv_val = float(recovery_metrics[-1].get('hrv', 42) or 42)
if current_hrv_val >= 56:
    kpi_hrv_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Parasimpático Alto"}
elif current_hrv_val >= 43:
    kpi_hrv_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Equilibrado Basal"}
elif current_hrv_val >= 38:
    kpi_hrv_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Límite Inferior"}
else:
    kpi_hrv_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Alerta Fatiga"}

current_sleep_sc = int(today_sleep_score)
if current_sleep_sc >= 80:
    kpi_sleep_theme = {"bg": "var(--pastel-mint-bg)", "text": "var(--pastel-mint-text)", "border": "var(--pastel-mint-border)", "tag": "Excelente"}
elif current_sleep_sc >= 70:
    kpi_sleep_theme = {"bg": "var(--pastel-blue-bg)", "text": "var(--pastel-blue-text)", "border": "var(--pastel-blue-border)", "tag": "Restaurador"}
elif current_sleep_sc >= 60:
    kpi_sleep_theme = {"bg": "var(--pastel-amber-bg)", "text": "var(--pastel-amber-text)", "border": "var(--pastel-amber-border)", "tag": "Aceptable"}
else:
    kpi_sleep_theme = {"bg": "var(--pastel-coral-bg)", "text": "var(--pastel-coral-text)", "border": "var(--pastel-coral-border)", "tag": "Descanso Pobre"}

# 11. Diagnóstico del Coach Fisiológico Deportivo (Resumen Motivador y Ajustes)
coach_status_badge = "Rendimiento en Alza • Adaptación Activa"
coach_status_color = "var(--pastel-mint-text)"
coach_status_bg = "var(--pastel-mint-bg)"
coach_diagnostic_summary = (
    f"Emiliano, tu adaptación fisiológica es altamente favorable: estás en estado <strong>{training_status_payload['status_title']}</strong> "
    f"con un VO₂ Máx de <strong>{current_vo2_val} ml/kg/min</strong> en percentil superior. Tu asimilación de carga viene balanceada (ACWR {current_acwr_val} en Sweet Spot) "
    f"y el sueño de anoche sumó <strong>{today_sleep_hours}h</strong> con <strong>{today_deep_hours}h de fase profunda</strong> para regeneración física plena. "
    f"Tus tiempos proyectados para 5K ({race_predictions_payload['5k']['time_str']}) y 10K ({race_predictions_payload['10k']['time_str']}) ratifican que los intervalos anaeróbicos "
    f"y el volumen de Zona 2 están dando dividendos directos en velocidad crucero."
)
coach_actionable_tip = (
    "💡 <strong>Recomendación del Coach:</strong> Mantener el estímulo aeróbico bajo para no descuidar el aclaramiento de lactato, "
    "aprovechar la buena frescura neuromuscular y sostener la constancia en el descanso sin exceder el ratio de 1.30 en las próximas 48 horas."
)

# Lista de años disponibles para el selector temporal
available_years = sorted(list(set(w["year"] for w in full_timeline_weeks)), reverse=True)

print("Generando HTML V4.1 con Foco Firstbeat, HRV corregida y Coach AI...")

html_content = f"""<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Garmin Performance Lab V4.0 | Google Cloud & Gemini Sports Intelligence</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      /* Base Google Cloud & Gemini Palette */
      --bg: #f8fafc;
      --bg-subtle: #f1f5f9;
      --surface: #ffffff;
      --surface-border: #e2e8f0;
      --surface-elevated: #f8fafc;
      --surface-hover: #f1f5f9;
      --text-main: #0f172a;
      --text-muted: #475569;
      --text-dim: #94a3b8;
      
      /* Soft Pastels (Gemini & MD3 Functional Palette) */
      --pastel-blue-bg: #e0f2fe;
      --pastel-blue-text: #0369a1;
      --pastel-blue-border: #bae6fd;
      
      --pastel-mint-bg: #ecfdf5;
      --pastel-mint-text: #047857;
      --pastel-mint-border: #a7f3d0;
      
      --pastel-amber-bg: #fef3c7;
      --pastel-amber-text: #b45309;
      --pastel-amber-border: #fde68a;
      
      --pastel-coral-bg: #ffe4e6;
      --pastel-coral-text: #be123c;
      --pastel-coral-border: #fecdd3;
      
      --pastel-lavender-bg: #f3e8ff;
      --pastel-lavender-text: #6d28d9;
      --pastel-lavender-border: #ddd6fe;

      /* Acentos primarios equilibrados */
      --accent-strava: #f97316;
      --accent-primary: #0284c7;
      --accent-z2: #059669;
      --accent-warning: #d97706;
      --accent-danger: #e11d48;
      --accent-purple: #7c3aed;
      
      /* Sombras etéreas estilo Google Cloud */
      --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.04), 0 1px 2px rgba(15, 23, 42, 0.02);
      --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
      --shadow-float: 0 12px 32px -4px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.04);
      --radius-card: 20px;
      --radius-btn: 12px;
      --radius-pill: 9999px;

      --tooltip-bg: #ffffff;
      --tooltip-border: #cbd5e1;
      --modal-overlay: rgba(15, 23, 42, 0.45);
    }}

    [data-theme="dark"] {{
      --bg: #0b0f19;
      --bg-subtle: #111827;
      --surface: #151d2f;
      --surface-border: #1f293d;
      --surface-elevated: #1a243a;
      --surface-hover: #22304d;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      
      --pastel-blue-bg: rgba(56, 189, 248, 0.15);
      --pastel-blue-text: #38bdf8;
      --pastel-blue-border: rgba(56, 189, 248, 0.3);

      --pastel-mint-bg: rgba(16, 185, 129, 0.15);
      --pastel-mint-text: #34d399;
      --pastel-mint-border: rgba(16, 185, 129, 0.3);

      --pastel-amber-bg: rgba(245, 158, 11, 0.15);
      --pastel-amber-text: #fbbf24;
      --pastel-amber-border: rgba(245, 158, 11, 0.3);

      --pastel-coral-bg: rgba(244, 63, 94, 0.15);
      --pastel-coral-text: #fb7185;
      --pastel-coral-border: rgba(244, 63, 94, 0.3);

      --pastel-lavender-bg: rgba(168, 85, 247, 0.15);
      --pastel-lavender-text: #c084fc;
      --pastel-lavender-border: rgba(168, 85, 247, 0.3);

      --accent-strava: #ea580c;
      --accent-primary: #38bdf8;
      --accent-z2: #10b981;
      --accent-warning: #f59e0b;
      --accent-danger: #f43f5e;
      --accent-purple: #a855f7;

      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
      --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
      --shadow-float: 0 12px 32px -4px rgba(0, 0, 0, 0.6);

      --tooltip-bg: #0f172a;
      --tooltip-border: #334155;
      --modal-overlay: rgba(3, 7, 18, 0.75);
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    
    html, body {{
      width: 100%;
      min-height: 100%;
      overflow-x: hidden;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding-bottom: 60px;
      transition: background-color 0.2s, color 0.2s;
    }}

    .container {{
      width: 100%;
      max-width: 1620px;
      margin: 0 auto;
      padding: 18px 24px;
    }}

    @media (max-width: 768px) {{
      .container {{ padding: 12px 14px; }}
    }}

    /* Layout con Barra Lateral Izquierda */
    .app-layout {{
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }}

    @media (max-width: 1080px) {{
      .app-layout {{
        grid-template-columns: 1fr;
      }}
    }}

    .sidebar {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 16px 12px;
      position: sticky;
      top: 18px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      box-shadow: var(--shadow-card);
    }}

    .sidebar-section-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-dim);
      padding: 8px 14px 4px 14px;
      margin-top: 6px;
    }}

    .sidebar-nav-btn {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 10px 14px;
      border-radius: var(--radius-btn);
      font-size: 13.5px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s cubic-bezier(0.2, 0, 0, 1);
      display: flex;
      align-items: center;
      gap: 12px;
      text-align: left;
      width: 100%;
      user-select: none;
    }}

    .sidebar-nav-btn:hover {{
      color: var(--text-main);
      background: var(--surface-hover);
    }}

    .sidebar-nav-btn.active {{
      background: var(--pastel-blue-bg);
      color: var(--pastel-blue-text);
      font-weight: 700;
      border-color: var(--pastel-blue-border);
    }}

    .sidebar-nav-btn.active.home-btn {{
      background: var(--pastel-amber-bg);
      color: var(--pastel-amber-text);
      border-color: var(--pastel-amber-border);
    }}

    .main-content {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    /* Header Google Cloud Inspired */
    header {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 18px 24px;
      margin-bottom: 20px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      box-shadow: var(--shadow-card);
    }}

    .brand-title {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.4px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .athlete-chip {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 600;
      background: var(--pastel-blue-bg);
      border: 1px solid var(--pastel-blue-border);
      padding: 4px 12px;
      border-radius: var(--radius-pill);
      color: var(--pastel-blue-text);
    }}

    .header-controls {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .btn-action {{
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: var(--text-main);
      padding: 8px 16px;
      border-radius: var(--radius-btn);
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      transition: all 0.15s cubic-bezier(0.2, 0, 0, 1);
    }}

    .btn-action:hover {{
      border-color: var(--pastel-blue-text);
      background: var(--surface-hover);
      transform: translateY(-1px);
    }}

    .unit-indicator {{
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      padding: 7px 14px;
      border-radius: var(--radius-pill);
    }}

    /* ========================================================
       COCKPIT SUPERIOR PROPORCIONAL Y BLINDADO (7 KPIS EN 1 FILA)
       ======================================================== */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;
      width: 100%;
      align-items: stretch;
    }}

    @media (max-width: 1300px) {{
      .kpi-grid {{
        grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
      }}
    }}

    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      padding: 12px 14px;
      position: relative;
      cursor: pointer;
      transition: transform 0.2s cubic-bezier(0.2, 0, 0, 1), box-shadow 0.2s ease, border-color 0.2s ease;
      min-width: 0;
      min-height: 104px;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-float);
      border-color: var(--surface-border);
    }}

    .kpi-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      min-width: 0;
      width: 100%;
    }}

    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1 1 0%;
      min-width: 0;
    }}

    .kpi-badge {{
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: var(--radius-pill);
      white-space: nowrap;
      flex-shrink: 0;
    }}

    .kpi-value {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 21px;
      font-weight: 800;
      color: var(--text-main);
      font-feature-settings: 'tnum' 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin: 2px 0;
      width: 100%;
      min-width: 0;
    }}

    .kpi-subtext {{
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      gap: 6px;
      min-width: 0;
      width: 100%;
    }}

    .kpi-subtext span {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .kpi-hint {{
      font-size: 10px;
      font-weight: 600;
      color: var(--pastel-blue-text);
      opacity: 0.9;
      flex-shrink: 0;
    }}

    /* Card Última Actividad */
    .last-activity-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 20px 24px;
      margin-bottom: 20px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      box-shadow: var(--shadow-card);
    }}

    .last-act-metrics {{
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
    }}

    .last-act-stat {{
      display: flex;
      flex-direction: column;
      min-width: 80px;
    }}

    .last-act-label {{
      font-size: 11px;
      text-transform: uppercase;
      color: var(--text-dim);
      font-weight: 700;
      letter-spacing: 0.4px;
    }}

    .last-act-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
    }}

    /* Strava Interactive Volume Card (Estilo Google Minimalist) */
    .strava-volume-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 24px 26px;
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
      box-shadow: var(--shadow-card);
    }}

    .strava-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 14px;
    }}

    .strava-title {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.4px;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .strava-nav-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .btn-timeline {{
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: var(--radius-btn);
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s cubic-bezier(0.2, 0, 0, 1);
    }}

    .btn-timeline:hover:not(:disabled) {{
      border-color: var(--accent-strava);
      color: var(--accent-strava);
      background: var(--surface-hover);
    }}

    .btn-timeline:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    .select-timeline-year {{
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: var(--radius-btn);
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      outline: none;
    }}

    .strava-stats-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 20px;
      margin-bottom: 20px;
      width: 100%;
    }}

    .strava-stat-col {{
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}

    .strava-stat-label {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 600;
      margin-bottom: 4px;
    }}

    .strava-stat-value {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: var(--text-main);
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .strava-toggle-group {{
      display: flex;
      background: var(--bg-subtle);
      padding: 4px;
      border-radius: var(--radius-btn);
      border: 1px solid var(--surface-border);
      gap: 4px;
    }}

    .strava-toggle-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .strava-toggle-btn.active {{
      background: var(--surface);
      color: var(--accent-strava);
      box-shadow: var(--shadow-sm);
    }}

    .strava-chart-container {{
      width: 100%;
      height: 230px;
      position: relative;
    }}

    .strava-footer-text {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      font-size: 11px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }}

    /* Layout Paneles */
    .layout-2 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 540px), 1fr));
      gap: 22px;
      margin-bottom: 22px;
    }}

    .panel {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 22px 24px;
      min-width: 0;
      overflow: hidden;
      box-shadow: var(--shadow-card);
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .panel-title {{
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -0.3px;
    }}

    .panel-subtitle {{
      font-size: 12.5px;
      color: var(--text-muted);
      margin-top: 3px;
    }}

    .chart-box {{
      width: 100%;
      height: 280px;
      position: relative;
    }}

    /* Salón de Récords Personales */
    .pr-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
      align-items: stretch;
    }}

    .pr-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      padding: 16px 18px;
      min-width: 0;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: var(--shadow-sm);
      transition: transform 0.15s, box-shadow 0.15s;
    }}

    .pr-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-card);
    }}

    .pr-badge {{
      display: inline-block;
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: var(--radius-pill);
      background: var(--pastel-blue-bg);
      color: var(--pastel-blue-text);
      margin-bottom: 8px;
      width: fit-content;
    }}

    .pr-badge-pending {{
      background: var(--pastel-amber-bg);
      color: var(--pastel-amber-text);
    }}

    .pr-distance {{
      font-size: 13.5px;
      font-weight: 700;
      color: var(--text-main);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .pr-time {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 24px;
      font-weight: 800;
      color: var(--pastel-blue-text);
      margin: 6px 0;
    }}

    .pr-meta {{
      font-size: 12px;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    /* Tabla con Estilo Google */
    .table-responsive {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      background: var(--surface);
      box-shadow: var(--shadow-card);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}

    th {{
      background: var(--bg-subtle);
      color: var(--text-muted);
      padding: 12px 16px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      white-space: nowrap;
    }}

    td {{
      padding: 14px 16px;
      border-top: 1px solid var(--surface-border);
      color: var(--text-main);
      white-space: nowrap;
    }}

    tr.clickable-row {{
      cursor: pointer;
      transition: background 0.15s;
    }}

    tr.clickable-row:hover {{
      background: var(--surface-hover);
    }}

    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: var(--radius-pill);
      font-size: 11px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }}

    .badge-run {{ background: var(--pastel-blue-bg); color: var(--pastel-blue-text); }}
    .badge-gym {{ background: var(--pastel-lavender-bg); color: var(--pastel-lavender-text); }}
    .badge-walk {{ background: var(--pastel-mint-bg); color: var(--pastel-mint-text); }}
    .badge-z2-pure {{ background: var(--pastel-mint-bg); color: var(--pastel-mint-text); border: 1px solid var(--pastel-mint-border); }}
    .badge-z2-drift {{ background: var(--pastel-amber-bg); color: var(--pastel-amber-text); border: 1px solid var(--pastel-amber-border); }}

    /* Tab Page Containers */
    .tab-page {{ display: none; }}
    .tab-page.active {{ display: block; }}

    /* Segmented Control Unificado (Today, 1M, 3M, 6M) */
    .timeline-segmented-control {{
      display: inline-flex;
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-pill);
      padding: 3px;
      gap: 3px;
    }}
    .segmented-pill-btn {{
      border: none;
      background: transparent;
      color: var(--text-muted);
      padding: 5px 14px;
      border-radius: var(--radius-pill);
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s ease;
      outline: none;
    }}
    .segmented-pill-btn:hover {{
      color: var(--text-main);
    }}
    .segmented-pill-btn.active {{
      background: #3b82f6;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
    }}

    /* Tarjetas de Predicción Oficiales (Imágenes 1 y 2) */
    .pred-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 18px;
      padding: 20px;
      cursor: pointer;
      position: relative;
      transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }}
    .pred-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-card);
      border-color: #3b82f6;
    }}
    .pred-card.active {{
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2), var(--shadow-card);
      background: linear-gradient(180deg, var(--surface) 0%, rgba(59, 130, 246, 0.03) 100%);
    }}
    .pred-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .pred-medal-icon {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--pastel-blue-bg);
      color: #3b82f6;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }}
    .pred-dist-title {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--text-main);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }}
    .pred-time-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 32px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.5px;
      margin: 4px 0;
    }}
    .pred-pace-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 6px;
    }}
    .pred-delta-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: var(--radius-pill);
      font-size: 11px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }}
    .pred-delta-badge.favorable {{
      background: var(--pastel-mint-bg);
      color: #059669;
      border: 1px solid var(--pastel-mint-border);
    }}
    .pred-delta-badge.desfavorable {{
      background: var(--pastel-coral-bg);
      color: #e11d48;
      border: 1px solid var(--pastel-coral-border);
    }}

    /* Calendario de Consistencia / Racha de Entrenamiento (Imagen 4) */
    .consistency-section {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius-card);
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-card);
    }}
    .streak-container {{
      display: grid;
      grid-template-columns: minmax(220px, 280px) 1fr;
      gap: 24px;
      align-items: center;
    }}
    @media (max-width: 900px) {{
      .streak-container {{
        grid-template-columns: 1fr;
      }}
    }}
    .streak-panel-card {{
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(59, 130, 246, 0.05) 100%);
      border: 1px solid var(--pastel-mint-border);
      border-radius: 18px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .streak-trophy {{
      width: 52px;
      height: 52px;
      border-radius: 14px;
      background: #10b981;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 26px;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
      flex-shrink: 0;
    }}
    .streak-count {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 32px;
      font-weight: 800;
      color: #047857;
      line-height: 1;
    }}
    .streak-label {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      margin-top: 4px;
    }}
    .streak-sublabel {{
      font-size: 11.5px;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .heatmap-scroll-area {{
      overflow-x: auto;
      padding-bottom: 8px;
    }}
    .heatmap-grid {{
      display: inline-grid;
      grid-template-rows: repeat(7, 13px);
      grid-auto-flow: column;
      grid-auto-columns: 13px;
      gap: 4px;
    }}
    .heatmap-cell {{
      width: 13px;
      height: 13px;
      border-radius: 3px;
      cursor: pointer;
      transition: transform 0.1s ease;
    }}
    .heatmap-cell:hover {{
      transform: scale(1.35);
      z-index: 5;
    }}
    .heatmap-cell.lvl-0 {{ background: #e2e8f0; }}
    .heatmap-cell.lvl-1 {{ background: #a7f3d0; }}
    .heatmap-cell.lvl-2 {{ background: #34d399; }}
    .heatmap-cell.lvl-3 {{ background: #059669; }}
    .heatmap-cell.lvl-4 {{ background: #064e3b; }}
    .heatmap-cell.is-today {{ outline: 2px solid #3b82f6; outline-offset: 1px; }}
    [data-theme="dark"] .heatmap-cell.lvl-0 {{ background: #1e293b; }}

    /* Modales Google Style */
    .modal-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: var(--modal-overlay);
      backdrop-filter: blur(8px);
      z-index: 999;
      justify-content: center;
      align-items: center;
      padding: 18px;
    }}

    .modal-overlay.active {{
      display: flex;
    }}

    .modal-box {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 24px;
      max-width: 680px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      padding: 28px;
      box-shadow: var(--shadow-float);
      position: relative;
    }}

    .modal-close {{
      position: absolute;
      top: 20px;
      right: 20px;
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: var(--text-muted);
      width: 34px;
      height: 34px;
      border-radius: var(--radius-pill);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      font-weight: bold;
      transition: all 0.15s;
    }}

    .modal-close:hover {{
      color: var(--text-main);
      background: var(--surface-hover);
    }}

    .zone-bar {{
      height: 14px;
      border-radius: 7px;
      background: var(--bg-subtle);
      overflow: hidden;
      display: flex;
      margin: 14px 0 18px 0;
    }}

    .zone-bar-segment {{
      height: 100%;
      transition: width 0.3s;
    }}

    /* Componente Spectrum Gauge */
    .spectrum-gauge {{
      margin: 18px 0;
    }}

    .spectrum-track {{
      display: flex;
      height: 16px;
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 8px;
    }}

    .spectrum-segment {{
      height: 100%;
      position: relative;
    }}

    .spectrum-legend {{
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }}

    .spectrum-current-marker {{
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 10px 16px;
      margin-top: 12px;
      font-size: 12.5px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    /* Glosario / Info */
    .info-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 18px;
      padding: 22px;
      margin-bottom: 16px;
      box-shadow: var(--shadow-sm);
    }}

    .info-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }}

    .info-tag {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11.5px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: var(--radius-pill);
      background: var(--pastel-blue-bg);
      color: var(--pastel-blue-text);
    }}

    .info-title {{
      font-size: 16px;
      font-weight: 800;
      color: var(--text-main);
    }}

    .info-desc {{
      font-size: 13.5px;
      color: var(--text-muted);
      line-height: 1.6;
    }}

    .info-why {{
      margin-top: 12px;
      background: var(--pastel-mint-bg);
      color: var(--pastel-mint-text);
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 12.5px;
      border-left: 4px solid var(--accent-z2);
    }}
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
        VO₂ Máx: <strong>{profile_data.get('vo2_max', 53.0)} ml/kg/min</strong> • 
        Umbral Lactato: <strong>{profile_data.get('threshold_hr', 179)} ppm</strong> • 
        Peso: <strong>{profile_data.get('weight', 74.0)} kg</strong>
      </div>
    </div>
    <div class="header-controls">
      <div class="unit-indicator">📍 Métricas expresadas en Kilómetros (km)</div>
      <button class="btn-action" onclick="toggleTheme()">🌓 Modo Claro / Oscuro</button>
    </div>
  </header>

  <!-- ========================================================
       ESTRUCTURA DE APLICACIÓN CON BARRA LATERAL IZQUIERDA
       ======================================================== -->
  <div class="app-layout">

    <!-- BARRA LATERAL IZQUIERDA -->
    <aside class="sidebar">
      <div class="sidebar-section-title">Navegación Principal</div>
      <button class="sidebar-nav-btn active home-btn" onclick="showTab('page-home')">
        <span>🏠</span>
        <span>Inicio</span>
      </button>

      <div class="sidebar-section-title">Módulos Analíticos</div>
      <button class="sidebar-nav-btn" onclick="showTab('page-training-status')">
        <span>⚡</span>
        <span>Estado de Entreno</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-predictions')">
        <span>🎯</span>
        <span>Predicciones</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-endurance')">
        <span>🛡️</span>
        <span>Endurance & Carga</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-records')">
        <span>🏆</span>
        <span>Récords Personales (PRs)</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-multisport')">
        <span>🏋️</span>
        <span>Multideporte (Gym/Run/Walk)</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-z2')">
        <span>💚</span>
        <span>Desglose Fisiológico Z2</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-recovery')">
        <span>🧠</span>
        <span>Sueño & VFC Autonómica</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-table')">
        <span>📋</span>
        <span>Bitácora de Sesiones</span>
      </button>
      <button class="sidebar-nav-btn" onclick="showTab('page-info')">
        <span>💡</span>
        <span>Glosario & Ciencia (Info)</span>
      </button>
    </aside>

    <!-- ÁREA DE CONTENIDO PRINCIPAL -->
    <main class="main-content">

      <!-- ========================================================
           1. COCKPIT SUPERIOR (7 KPIS EN UNA SOLA LÍNEA PROPORCIONAL)
           ======================================================== -->
      <div class="kpi-grid">
        <!-- 1. ESTADO DE ENTRENO GARMIN (INDICADOR DE MEJORA) -->
        <div class="kpi-card" onclick="showTab('page-training-status')">
          <div class="kpi-header">
            <span class="kpi-label">Estado Entreno</span>
            <span class="kpi-badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text); border:1px solid var(--pastel-mint-border);">FR 265</span>
          </div>
          <div class="kpi-value" style="color:var(--pastel-mint-text);">{training_status_payload['status_title']}</div>
          <div class="kpi-subtext">
            <span class="badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text); padding:1px 6px;">↗ En ascenso</span>
            <span class="kpi-hint">Detalle ↗</span>
          </div>
        </div>

        <!-- 2. VO2 Máx -->
        <div class="kpi-card" onclick="openKpiModal('vo2')">
          <div class="kpi-header">
            <span class="kpi-label">VO₂ Máx</span>
            <span class="kpi-badge" style="background:{kpi_vo2_theme['bg']}; color:{kpi_vo2_theme['text']}; border:1px solid {kpi_vo2_theme['border']};">{kpi_vo2_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_vo2_theme['text']};">{training_status_payload['vo2_precise']} <span style="font-size:12px; font-weight:normal; color:var(--text-muted);">ml/kg</span></div>
          <div class="kpi-subtext">
            <span>Techo Aeróbico</span>
            <span class="kpi-hint">Escala ↗</span>
          </div>
        </div>

        <!-- 3. Endurance -->
        <div class="kpi-card" onclick="openKpiModal('endurance')">
          <div class="kpi-header">
            <span class="kpi-label">Endurance</span>
            <span class="kpi-badge" style="background:{kpi_endurance_theme['bg']}; color:{kpi_endurance_theme['text']}; border:1px solid {kpi_endurance_theme['border']};">{kpi_endurance_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_endurance_theme['text']};">{endurance_data_payload['score']}</div>
          <div class="kpi-subtext">
            <span>Resistencia</span>
            <span class="kpi-hint">Fórmula ↗</span>
          </div>
        </div>

        <!-- 4. Ratio ACWR -->
        <div class="kpi-card" onclick="openKpiModal('acwr')">
          <div class="kpi-header">
            <span class="kpi-label">Ratio ACWR</span>
            <span class="kpi-badge" style="background:{kpi_acwr_theme['bg']}; color:{kpi_acwr_theme['text']}; border:1px solid {kpi_acwr_theme['border']};">{kpi_acwr_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_acwr_theme['text']};">{pmc_series[-1]['acwr']}</div>
          <div class="kpi-subtext">
            <span>Sobrecarga 7d/28d</span>
            <span class="kpi-hint">Riesgo ↗</span>
          </div>
        </div>

        <!-- 5. Volumen Zona 2 -->
        <div class="kpi-card" onclick="openKpiModal('z2')">
          <div class="kpi-header">
            <span class="kpi-label">Volumen Z2</span>
            <span class="kpi-badge" style="background:{kpi_z2_theme['bg']}; color:{kpi_z2_theme['text']}; border:1px solid {kpi_z2_theme['border']};">{kpi_z2_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_z2_theme['text']};">{endurance_data_payload['z2_hours_4w']}<span style="font-size:13px; font-weight:normal; color:var(--text-muted);">h</span></div>
          <div class="kpi-subtext">
            <span>Base Mitocondrial</span>
            <span class="kpi-hint">Curva ↗</span>
          </div>
        </div>

        <!-- 6. VFC Nocturna -->
        <div class="kpi-card" onclick="openKpiModal('hrv')">
          <div class="kpi-header">
            <span class="kpi-label">VFC / RMSSD</span>
            <span class="kpi-badge" style="background:{kpi_hrv_theme['bg']}; color:{kpi_hrv_theme['text']}; border:1px solid {kpi_hrv_theme['border']};">{kpi_hrv_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_hrv_theme['text']};">{recovery_metrics[-1].get('hrv', 42) or 42}<span style="font-size:12px; font-weight:normal; color:var(--text-muted);"> ms</span></div>
          <div class="kpi-subtext">
            <span>Parasimpático</span>
            <span class="kpi-hint">Tendencia ↗</span>
          </div>
        </div>

        <!-- 7. Sueño Fisiológico Puro (Exclusivo descanso) -->
        <div class="kpi-card" onclick="openKpiModal('sleep')">
          <div class="kpi-header">
            <span class="kpi-label">Sueño Fisiológico</span>
            <span class="kpi-badge" style="background:{kpi_sleep_theme['bg']}; color:{kpi_sleep_theme['text']}; border:1px solid {kpi_sleep_theme['border']};">{kpi_sleep_theme['tag']}</span>
          </div>
          <div class="kpi-value" style="color:{kpi_sleep_theme['text']};">{today_sleep_hours}<span style="font-size:13px; font-weight:normal; color:var(--text-muted);">h</span></div>
          <div class="kpi-subtext">
            <span>{today_deep_hours}h Prof • {today_rem_hours}h REM</span>
            <span class="kpi-hint">Fases ↗</span>
          </div>
        </div>
      </div>

      <!-- ================= TAB 0: INICIO (HOME) ================= -->
      <div id="page-home" class="tab-page active">
        <!-- 1. RESUMEN FISIOLÓGICO DEL COACH DEPORTIVO / DIAGNÓSTICO INTEGRAL -->
        <div class="panel" style="margin-bottom: 20px; border-left: 5px solid #10b981; background: linear-gradient(135deg, var(--surface) 0%, var(--bg-subtle) 100%);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:24px;">🧠</span>
              <div>
                <div style="font-size:16px; font-weight:800; color:var(--text-main); letter-spacing:-0.2px;">Resumen Fisiológico del Coach Deportivo</div>
                <div style="font-size:12px; color:var(--text-muted);">Lectura holística de descanso, asimilación de carga y proyección competitiva</div>
              </div>
            </div>
            <span class="badge" style="background:{coach_status_bg}; color:{coach_status_color}; font-size:12px; padding:6px 14px; border:1px solid rgba(16,185,129,0.3);">
              ● {coach_status_badge}
            </span>
          </div>

          <div style="font-size:13.5px; color:var(--text-main); line-height:1.65; margin-bottom:14px; background:var(--surface); padding:14px 18px; border-radius:12px; border:1px solid var(--surface-border);">
            {coach_diagnostic_summary}
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:12px; margin-bottom:12px;">
            <div style="background:var(--surface); padding:10px 14px; border-radius:10px; border:1px solid var(--surface-border);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Descanso & Sueño</div>
              <div style="font-size:14px; font-weight:700; color:#38bdf8; margin-top:2px;">{today_sleep_hours}h ({today_sleep_score}/100) • Óptimo</div>
              <div style="font-size:11px; color:var(--text-muted);">{today_deep_hours}h Sueño Profundo restaurador</div>
            </div>
            <div style="background:var(--surface); padding:10px 14px; border-radius:10px; border:1px solid var(--surface-border);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Asimilación de Carga</div>
              <div style="font-size:14px; font-weight:700; color:#10b981; margin-top:2px;">ACWR {current_acwr_val} • Sweet Spot</div>
              <div style="font-size:11px; color:var(--text-muted);">Sin riesgo de lesión / Base sólida</div>
            </div>
            <div style="background:var(--surface); padding:10px 14px; border-radius:10px; border:1px solid var(--surface-border);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Proyección en Carrera</div>
              <div style="font-size:14px; font-weight:700; color:#f59e0b; margin-top:2px;">5K: {race_predictions_payload['5k']['time_str']} • 10K: {race_predictions_payload['10k']['time_str']}</div>
              <div style="font-size:11px; color:var(--text-muted);">Ritmos crucero en consolidación</div>
            </div>
            <div style="background:var(--surface); padding:10px 14px; border-radius:10px; border:1px solid var(--surface-border);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Variabilidad VFC</div>
              <div style="font-size:14px; font-weight:700; color:#a855f7; margin-top:2px;">{current_hrv_val} ms • Rango Saludable</div>
              <div style="font-size:11px; color:var(--text-muted);">Tono vagal parasimpático estable</div>
            </div>
          </div>

          <div style="font-size:12.5px; color:var(--text-muted); line-height:1.5; padding-top:4px;">
            {coach_actionable_tip}
          </div>
        </div>

        <!-- 1.1 Calendario de Consistencia & Racha de Entrenamiento (Estilo Strava / GitHub) -->
        <div class="consistency-section">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:18px;">
            <div>
              <div style="font-size:16px; font-weight:800; color:var(--text-main);">Consistencia & Racha de Entrenamiento</div>
              <div style="font-size:12px; color:var(--text-muted);">Registro continuo de sesiones y semanas activas sin perder la racha</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px; font-size:11.5px; color:var(--text-muted);">
              <span>Menos</span>
              <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#e2e8f0;"></span>
              <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#a7f3d0;"></span>
              <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#34d399;"></span>
              <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#059669;"></span>
              <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#064e3b;"></span>
              <span>Más</span>
            </div>
          </div>

          <div class="streak-container">
            <!-- Tarjeta Lateral de Racha Activa -->
            <div class="streak-panel-card">
              <div class="streak-trophy">🏆</div>
              <div>
                <div class="streak-count">{consecutive_active_weeks}</div>
                <div class="streak-label">Semanas en Racha</div>
                <div class="streak-sublabel">Constancia deportiva ininterrumpida</div>
              </div>
            </div>

            <!-- Heatmap Grid (Últimos 12 meses) -->
            <div class="heatmap-scroll-area">
              <div class="heatmap-grid" id="consistency-heatmap-grid">
                <!-- Inyectado por JS -->
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Tarjeta Destacada: Última Actividad Realizada (Arriba de la semana de carga) -->
        <div class="last-activity-card">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span class="badge badge-run">{latest_act['sport']}</span>
              <span style="font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono';">{latest_act['date_arg']} {latest_act['time_part']}</span>
            </div>
            <div style="font-size: 18px; font-weight: 700; color: var(--text-main);">{latest_act['name']}</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
              Impacto de Carga: <strong>{latest_act['load']} pts</strong> • Efecto Aeróbico: <strong>{latest_act['aerobic_te'] or 3.2}</strong> • Efecto Anaeróbico: <strong>{latest_act['anaerobic_te'] or 0.5}</strong> • Desnivel: <strong>{latest_act['elevation_m']} m</strong>
            </div>
          </div>
          <div class="last-act-metrics">
            <div class="last-act-stat">
              <span class="last-act-label">Distancia</span>
              <span class="last-act-val">{latest_act['distance_km']} km</span>
            </div>
            <div class="last-act-stat">
              <span class="last-act-label">Tiempo</span>
              <span class="last-act-val">{latest_act['duration_min']} min</span>
            </div>
            <div class="last-act-stat">
              <span class="last-act-label">Ritmo Medio</span>
              <span class="last-act-val">{latest_act['pace_str']}</span>
            </div>
            <div class="last-act-stat">
              <span class="last-act-label">FC Media / Máx</span>
              <span class="last-act-val">{latest_act['avg_hr']} / {latest_act['max_hr']} ppm</span>
            </div>
            <div class="last-act-stat">
              <span class="last-act-label">Zona 2</span>
              <span class="last-act-val" style="color: var(--accent-z2);">{latest_act['z2_pct']}%</span>
            </div>
          </div>
          <button class="btn-action" onclick="openActivityModal(0)">🔍 Ver Fisiología de la Sesión</button>
        </div>

        <!-- 3. Módulo de Carga Semanal (12 Semanas Navegable con Historial Completo) -->
        <div class="strava-volume-card">
          <div class="strava-header">
            <div class="strava-title">
              <span id="strava-week-title">Esta semana</span>
            </div>
            
            <!-- Controles de navegación temporal hacia atrás -->
            <div class="strava-nav-controls">
              <button class="btn-timeline" id="btn-timeline-prev" onclick="moveTimeline(-12)">◀ 12 Semanas Anteriores</button>
              <select class="select-timeline-year" id="select-year" onchange="jumpToYear(this.value)">
                {''.join(f'<option value="{y}">{y}</option>' for y in available_years)}
              </select>
              <button class="btn-timeline" id="btn-timeline-next" onclick="moveTimeline(12)">12 Semanas Siguientes ▶</button>
              <button class="btn-timeline" style="border-color:var(--accent-strava); color:var(--accent-strava);" onclick="resetTimelineToNow()">Hoy (Reciente)</button>
            </div>

            <div class="strava-toggle-group">
              <button class="strava-toggle-btn active" id="btn-strava-km" onclick="switchStravaMode('km')">Distancia (km)</button>
              <button class="strava-toggle-btn" id="btn-strava-z2" onclick="switchStravaMode('z2')">Volumen Zona 2 (h)</button>
              <button class="strava-toggle-btn" id="btn-strava-load" onclick="switchStravaMode('load')">Carga Semanal</button>
            </div>
          </div>

          <div class="strava-stats-row">
            <div class="strava-stat-col">
              <span class="strava-stat-label">Distancia</span>
              <span class="strava-stat-value" id="strava-stat-dist">{current_week_stats['dist_km']} km</span>
            </div>
            <div class="strava-stat-col">
              <span class="strava-stat-label">Tiempo</span>
              <span class="strava-stat-value" id="strava-stat-time">{current_week_stats['dur_str']}</span>
            </div>
            <div class="strava-stat-col">
              <span class="strava-stat-label">Desnivel</span>
              <span class="strava-stat-value" id="strava-stat-elev">{current_week_stats['elev_m']} m</span>
            </div>
            <div class="strava-stat-col" style="border-left: 1px solid var(--surface-border); padding-left: 24px;">
              <span class="strava-stat-label">Base Zona 2</span>
              <span class="strava-stat-value" id="strava-stat-z2" style="color: var(--accent-z2);">{current_week_stats['z2_hours']} h</span>
            </div>
          </div>

          <div style="font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px;">
            Ventana de 12 Semanas: <span id="strava-window-dates" style="color:var(--text-main); font-family:'JetBrains Mono';">Mostrando semanas recientes</span>
          </div>

          <div class="strava-chart-container">
            <canvas id="chartStravaVolume"></canvas>
          </div>

          <div class="strava-footer-text">
            <span id="strava-node-hint">● Nodo naranja resaltado: Semana actual en curso</span>
            <span>Base histórica total: {len(full_timeline_weeks)} semanas ({len(activities)} actividades sincronizadas)</span>
          </div>
        </div>
      </div>

      <!-- ================= TAB: ESTADO DE ENTRENO OFICIAL FIRSTBEAT ================= -->
      <div id="page-training-status" class="tab-page">
        <div class="panel" style="margin-bottom: 20px;">
          <div class="panel-header">
            <div>
              <div class="panel-title">Estado de Entrenamiento & Fisiología Firstbeat</div>
              <div class="panel-subtitle">Diagnóstico oficial de Garmin Forerunner 265 • Algoritmo multidimensional</div>
            </div>
            <span class="badge badge-run" style="background:rgba(16,185,129,0.2); color:#10b981; font-size:12px; padding:6px 12px;">
              ● {training_status_payload['status_title'].upper()} (Condición en ascenso)
            </span>
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin-bottom:20px;">
            <!-- 1. VO2 Max Bloque Interactivo -->
            <div style="background:var(--surface-elevated); padding:16px; border-radius:10px; border-left:4px solid #38bdf8; cursor:pointer; transition:transform 0.15s ease;" onclick="openKpiModal('vo2')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">1. Consumo Máximo de Oxígeno</span>
                <span style="font-size:11px; color:#38bdf8;">↗ Ver Escala</span>
              </div>
              <div style="font-size:24px; font-weight:800; color:#38bdf8; font-family:'JetBrains Mono'; margin:4px 0;">{training_status_payload['vo2_precise']} <span style="font-size:13px; font-weight:normal; color:var(--text-muted);">ml/kg/min</span></div>
              <div style="font-size:12px; color:var(--text-muted);">Techo cardiovascular superior (Percentil > 90). Adaptación aeróbica en ascenso.</div>
            </div>

            <!-- 2. VFC Autonómica Bloque Interactivo -->
            <div style="background:var(--surface-elevated); padding:16px; border-radius:10px; border-left:4px solid #a855f7; cursor:pointer; transition:transform 0.15s ease;" onclick="openKpiModal('hrv')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">2. Estado de VFC Autonómica</span>
                <span style="font-size:11px; color:#a855f7;">↗ Ver Corredor</span>
              </div>
              <div style="font-size:24px; font-weight:800; color:#a855f7; font-family:'JetBrains Mono'; margin:4px 0;">{recovery_metrics[-1].get('hrv', 42) or 42} <span style="font-size:13px; font-weight:normal; color:var(--text-muted);">ms (Equilibrado)</span></div>
              <div style="font-size:12px; color:var(--text-muted);">Tono vagal parasimpático dentro de tu rango basal saludable (43 - 56 ms).</div>
            </div>

            <!-- 3. Carga Aguda vs Túnel Óptimo Bloque Interactivo -->
            <div style="background:var(--surface-elevated); padding:16px; border-radius:10px; border-left:4px solid #f59e0b; cursor:pointer; transition:transform 0.15s ease;" onclick="openKpiModal('training_status')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">3. Carga Aguda vs. Túnel Óptimo</span>
                <span style="font-size:11px; color:#f59e0b;">↗ Ver Historial</span>
              </div>
              <div style="font-size:24px; font-weight:800; color:#f59e0b; font-family:'JetBrains Mono'; margin:4px 0;">{training_status_payload['acute_load']} <span style="font-size:13px; font-weight:normal; color:var(--text-muted);">pts</span></div>
              <div style="font-size:12px; color:var(--text-muted);">Túnel recomendado: <strong>{training_status_payload['min_tunnel']} a {training_status_payload['max_tunnel']} pts</strong>. Estás en zona productiva.</div>
            </div>

            <!-- 4. Diagnóstico Firstbeat Bloque Interactivo -->
            <div style="background:var(--surface-elevated); padding:16px; border-radius:10px; border-left:4px solid #10b981; cursor:pointer; transition:transform 0.15s ease;" onclick="openKpiModal('training_status')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">4. Diagnóstico Firstbeat</span>
                <span style="font-size:11px; color:#10b981;">↗ Matriz</span>
              </div>
              <div style="font-size:15px; font-weight:700; color:var(--text-main); margin:4px 0;">{training_status_payload['load_balance']['feedback']}</div>
              <div style="font-size:12px; color:var(--text-muted);">{training_status_payload['feedback_phrase']}</div>
            </div>
          </div>

          <!-- Foco de Carga Firstbeat con Túneles Gráficos Delimitados Exactos -->
          <div style="background:var(--surface-elevated); padding:20px; border-radius:10px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:4px;">
              <span style="font-size:15px; font-weight:700; color:var(--text-main);">Equilibrio y Foco de Carga (Últimas 4 Semanas)</span>
              <span class="badge" style="background:var(--pastel-blue-bg); color:var(--pastel-blue-text); border:1px solid var(--pastel-blue-border);">Túneles Garmin Oficiales</span>
            </div>
            <div style="font-size:12px; color:var(--text-muted); margin-bottom:18px;">
              Distribución del estrés fisiológico en los 3 sistemas energéticos. Las zonas sombreadas con líneas punteadas representan los túneles objetivo exactos de Firstbeat:
            </div>

            <div style="display:flex; flex-direction:column; gap:20px;">
              <!-- 1. Anaeróbico -->
              <div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
                  <span><strong>Anaeróbico (Sprints / Intervalos Z5):</strong> <strong style="color:#f43f5e; font-family:'JetBrains Mono';">{training_status_payload['load_balance']['anaerobic']} pts</strong></span>
                  <span style="color:#f43f5e; font-weight:700; font-family:'JetBrains Mono';">Túnel Objetivo: {training_status_payload['load_balance']['anaerobic_min']} - {training_status_payload['load_balance']['anaerobic_max']} pts (Sobrecarga estimulante)</span>
                </div>
                <div style="height:14px; background:var(--surface); border-radius:7px; position:relative; overflow:hidden; border:1px solid var(--surface-border);">
                  <!-- Zona túnel objetivo -->
                  <div style="position:absolute; left:{int((training_status_payload['load_balance']['anaerobic_min'] / 650) * 100)}%; width:{int(((training_status_payload['load_balance']['anaerobic_max'] - training_status_payload['load_balance']['anaerobic_min']) / 650) * 100)}%; height:100%; background:rgba(244, 63, 94, 0.15); border-left:2px dashed #f43f5e; border-right:2px dashed #f43f5e; z-index:1;" title="Túnel Objetivo"></div>
                  <!-- Barra real -->
                  <div style="width:{min(100, int((training_status_payload['load_balance']['anaerobic'] / 650) * 100))}%; height:100%; background:#f43f5e; border-radius:7px; position:relative; z-index:2; opacity:0.9;"></div>
                </div>
              </div>

              <!-- 2. Aeróbico Alto -->
              <div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
                  <span><strong>Aeróbico Alto (Tempo / Umbral Z3-Z4):</strong> <strong style="color:#38bdf8; font-family:'JetBrains Mono';">{training_status_payload['load_balance']['aerobic_high']} pts</strong></span>
                  <span style="color:#38bdf8; font-weight:700; font-family:'JetBrains Mono';">Túnel Objetivo: {training_status_payload['load_balance']['aerobic_high_min']} - {training_status_payload['load_balance']['aerobic_high_max']} pts (En rango óptimo)</span>
                </div>
                <div style="height:14px; background:var(--surface); border-radius:7px; position:relative; overflow:hidden; border:1px solid var(--surface-border);">
                  <!-- Zona túnel objetivo -->
                  <div style="position:absolute; left:{int((training_status_payload['load_balance']['aerobic_high_min'] / 1000) * 100)}%; width:{int(((training_status_payload['load_balance']['aerobic_high_max'] - training_status_payload['load_balance']['aerobic_high_min']) / 1000) * 100)}%; height:100%; background:rgba(56, 189, 248, 0.15); border-left:2px dashed #38bdf8; border-right:2px dashed #38bdf8; z-index:1;" title="Túnel Objetivo"></div>
                  <!-- Barra real -->
                  <div style="width:{min(100, int((training_status_payload['load_balance']['aerobic_high'] / 1000) * 100))}%; height:100%; background:#38bdf8; border-radius:7px; position:relative; z-index:2; opacity:0.9;"></div>
                </div>
              </div>

              <!-- 3. Aeróbico Bajo -->
              <div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
                  <span><strong>Aeróbico Bajo (Base / Zona 2):</strong> <strong style="color:#10b981; font-family:'JetBrains Mono';">{training_status_payload['load_balance']['aerobic_low']} pts</strong></span>
                  <span style="color:#10b981; font-weight:700; font-family:'JetBrains Mono';">Túnel Objetivo: {training_status_payload['load_balance']['aerobic_low_min']} - {training_status_payload['load_balance']['aerobic_low_max']} pts (En rango óptimo)</span>
                </div>
                <div style="height:14px; background:var(--surface); border-radius:7px; position:relative; overflow:hidden; border:1px solid var(--surface-border);">
                  <!-- Zona túnel objetivo -->
                  <div style="position:absolute; left:{int((training_status_payload['load_balance']['aerobic_low_min'] / 900) * 100)}%; width:{int(((training_status_payload['load_balance']['aerobic_low_max'] - training_status_payload['load_balance']['aerobic_low_min']) / 900) * 100)}%; height:100%; background:rgba(16, 185, 129, 0.15); border-left:2px dashed #10b981; border-right:2px dashed #10b981; z-index:1;" title="Túnel Objetivo"></div>
                  <!-- Barra real -->
                  <div style="width:{min(100, int((training_status_payload['load_balance']['aerobic_low'] / 900) * 100))}%; height:100%; background:#10b981; border-radius:7px; position:relative; z-index:2; opacity:0.9;"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Gráfico Oficial Garmin Firstbeat: Carga Aguda Diaria con Banda Verde de Túnel Óptimo (Imagen 5) -->
          <div style="background:var(--surface-elevated); padding:24px; border-radius:18px; border:1px solid var(--surface-border);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
              <div>
                <div style="font-size:16px; font-weight:800; color:var(--text-main);">Carga Aguda Diaria & Túnel Óptimo Garmin (Firstbeat)</div>
                <div style="font-size:12px; color:var(--text-muted);">Curva de fatiga aguda real (línea blanca con nodos) sobre el túnel verde de asimilación segura ({training_status_payload['min_tunnel']} a {training_status_payload['max_tunnel']} pts)</div>
              </div>
              <div class="timeline-segmented-control" id="control-timeline-acute">
                <button class="segmented-pill-btn" onclick="filterAcuteChart('today')">Hoy</button>
                <button class="segmented-pill-btn" onclick="filterAcuteChart('1M')">1M</button>
                <button class="segmented-pill-btn active" onclick="filterAcuteChart('3M')">3M</button>
                <button class="segmented-pill-btn" onclick="filterAcuteChart('6M')">6M</button>
              </div>
            </div>

            <div style="display:flex; gap:20px; font-size:12px; margin-bottom:16px; flex-wrap:wrap; align-items:center;">
              <span style="display:inline-flex; align-items:center; gap:6px;">
                <span style="width:12px; height:12px; border-radius:50%; background:#ffffff; border:2px solid #0f172a; display:inline-block;"></span>
                <strong>Carga Aguda Diaria (7d):</strong> <span id="acute-legend-val" style="font-family:'JetBrains Mono'; font-weight:700;">{training_status_payload['acute_load']} pts</span>
              </span>
              <span style="display:inline-flex; align-items:center; gap:6px;">
                <span style="width:16px; height:10px; border-radius:3px; background:rgba(16, 185, 129, 0.4); border:1px solid #10b981; display:inline-block;"></span>
                <span style="color:#047857; font-weight:700;">Rango Óptimo:</span> <span style="font-family:'JetBrains Mono';">{training_status_payload['min_tunnel']} - {training_status_payload['max_tunnel']} pts</span>
              </span>
              <span class="badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text); border:1px solid var(--pastel-mint-border);">Estado: {training_status_payload['status_title']}</span>
            </div>

            <div style="height:260px; position:relative; background:linear-gradient(180deg, rgba(15,23,42,0.92) 0%, rgba(15,23,42,0.96) 100%); border-radius:14px; padding:12px;">
              <canvas id="chartGarminAcuteTunnel"></canvas>
            </div>
            
            <div style="display:flex; justify-content:space-between; font-size:11.5px; color:var(--text-dim); margin-top:10px;">
              <span>● La línea blanca debe mantenerse dentro de la franja verde para inducir supercompensación sin sobreentrenamiento.</span>
              <span>Algoritmo Firstbeat Analytics</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ================= TAB: PREDICCIONES DE CARRERA & READINESS ================= -->
      <div id="page-predictions" class="tab-page">
        <div class="panel" style="margin-bottom: 20px;">
          <div class="panel-header">
            <div>
              <div class="panel-title">Predicciones Oficiales de Carrera Garmin</div>
              <div class="panel-subtitle">Tiempos y ritmos proyectados por Firstbeat Analytics basados en tu VO₂ Máx ({training_status_payload['vo2_precise']} ml/kg) y volumen crónico</div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
              <span class="badge badge-run">Forerunner 265</span>
              <div class="timeline-segmented-control" id="control-timeline-pred">
                <button class="segmented-pill-btn" onclick="filterPredChart('today')">Hoy</button>
                <button class="segmented-pill-btn" onclick="filterPredChart('1M')">1M</button>
                <button class="segmented-pill-btn active" onclick="filterPredChart('3M')">3M</button>
                <button class="segmented-pill-btn" onclick="filterPredChart('6M')">6M</button>
              </div>
            </div>
          </div>

          <!-- Selector de Distancia / Tarjetas Oficiales (Imágenes 1 y 2) -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:24px;">
            <!-- 5K -->
            <div class="pred-card active" id="pred-card-5k" onclick="selectPredictionDistance('5k')">
              <div class="pred-card-header">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="pred-medal-icon">🥇</span>
                  <span class="pred-dist-title">5 Kilómetros</span>
                </div>
                <span class="pred-delta-badge {'favorable' if pred_deltas['5k']['favorable'] else 'desfavorable'}">{pred_deltas['5k']['text']}</span>
              </div>
              <div class="pred-time-val" id="pred-val-5k">{race_predictions_payload['5k']['time_str']}</div>
              <div class="pred-pace-row">
                <span style="font-size:12px; color:var(--text-muted);">Ritmo: <strong>{race_predictions_payload['5k']['pace']}</strong></span>
                <span style="font-size:11px; color:var(--text-dim);">PR: {personal_records['5k']['time_str']}</span>
              </div>
            </div>

            <!-- 10K -->
            <div class="pred-card" id="pred-card-10k" onclick="selectPredictionDistance('10k')">
              <div class="pred-card-header">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="pred-medal-icon" style="background:var(--pastel-mint-bg); color:#10b981;">🥈</span>
                  <span class="pred-dist-title">10 Kilómetros</span>
                </div>
                <span class="pred-delta-badge {'favorable' if pred_deltas['10k']['favorable'] else 'desfavorable'}">{pred_deltas['10k']['text']}</span>
              </div>
              <div class="pred-time-val" id="pred-val-10k">{race_predictions_payload['10k']['time_str']}</div>
              <div class="pred-pace-row">
                <span style="font-size:12px; color:var(--text-muted);">Ritmo: <strong>{race_predictions_payload['10k']['pace']}</strong></span>
                <span style="font-size:11px; color:var(--text-dim);">PR: {personal_records['10k']['time_str']}</span>
              </div>
            </div>

            <!-- 21.1K (Half-Marathon) -->
            <div class="pred-card" id="pred-card-21k" onclick="selectPredictionDistance('21k')">
              <div class="pred-card-header">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="pred-medal-icon" style="background:var(--pastel-amber-bg); color:#f59e0b;">🥉</span>
                  <span class="pred-dist-title">Medio Maratón (21.1k)</span>
                </div>
                <span class="pred-delta-badge {'favorable' if pred_deltas['21k']['favorable'] else 'desfavorable'}">{pred_deltas['21k']['text']}</span>
              </div>
              <div class="pred-time-val" id="pred-val-21k">{race_predictions_payload['21k']['time_str']}</div>
              <div class="pred-pace-row">
                <span style="font-size:12px; color:var(--text-muted);">Ritmo: <strong>{race_predictions_payload['21k']['pace']}</strong></span>
                <span style="font-size:11px; color:var(--text-dim);">PR: {personal_records['21k']['time_str']}</span>
              </div>
            </div>

            <!-- 42.2K (Marathon) -->
            <div class="pred-card" id="pred-card-42k" onclick="selectPredictionDistance('42k')">
              <div class="pred-card-header">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="pred-medal-icon" style="background:var(--pastel-lavender-bg); color:#a855f7;">🏅</span>
                  <span class="pred-dist-title">Maratón (42.2k)</span>
                </div>
                <span class="pred-delta-badge {'favorable' if pred_deltas['42k']['favorable'] else 'desfavorable'}">{pred_deltas['42k']['text']}</span>
              </div>
              <div class="pred-time-val" id="pred-val-42k">{race_predictions_payload['42k']['time_str']}</div>
              <div class="pred-pace-row">
                <span style="font-size:12px; color:var(--text-muted);">Ritmo: <strong>{race_predictions_payload['42k']['pace']}</strong></span>
                <span style="font-size:11px; color:var(--text-dim);">Objetivo Proyectado</span>
              </div>
            </div>
          </div>

          <!-- Gráfica Evolutiva de la Distancia Seleccionada (Imagen 1) -->
          <div style="background:var(--surface-elevated); padding:24px; border-radius:18px; border:1px solid var(--surface-border); margin-bottom:24px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
              <div>
                <span style="font-size:15px; font-weight:800; color:var(--text-main);" id="pred-chart-title">Evolución de Predicción: 5 Kilómetros</span>
                <span style="font-size:12px; color:var(--text-muted); margin-left:8px;" id="pred-chart-subtitle">Curva continua histórica con nodo final resaltado en halo azul</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px; font-size:12px;">
                <span style="color:var(--text-muted);">Tiempo Actual:</span>
                <span style="font-family:'JetBrains Mono'; font-weight:800; color:#3b82f6; font-size:15px;" id="pred-chart-current-time">{race_predictions_payload['5k']['time_str']}</span>
              </div>
            </div>

            <div style="height:250px; position:relative;">
              <canvas id="chartRacePredictionEvolution"></canvas>
            </div>

            <div style="display:flex; justify-content:space-between; font-size:11.5px; color:var(--text-muted); margin-top:10px;">
              <span>● Los descensos en la gráfica representan mejoras cronométricas (tiempo ganado).</span>
              <span id="pred-chart-data-count">180 días sincronizados de Garmin Connect</span>
            </div>
          </div>

          <!-- Matriz de Predisposición (Training Readiness) & Impacto del Descanso -->
          <div style="background:var(--surface-elevated); padding:20px; border-radius:14px; border:1px solid var(--surface-border);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
              <div>
                <div style="font-size:16px; font-weight:700; color:var(--text-main);">Disposición para Entrenar (Training Readiness: {readiness_payload['score']}/100)</div>
                <div style="font-size:12px; color:var(--text-muted);">¿Qué pasa si dormimos mal o acumulamos fatiga? Impacto cruzado en tu rendimiento:</div>
              </div>
              <span class="badge" style="background:rgba(245,158,11,0.15); color:#f59e0b; font-size:12px; font-weight:700; padding:6px 12px;">
                Nivel: {readiness_payload['level']} ({readiness_payload['feedback_short']})
              </span>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-top:14px;">
              <div style="background:var(--surface); padding:12px 14px; border-radius:8px; border-left:3px solid #60a5fa;">
                <div style="font-size:11px; color:var(--text-muted);">Calidad del Sueño</div>
                <div style="font-size:18px; font-weight:700; color:#60a5fa; margin:2px 0;">{readiness_payload['sleep_factor_percent']}%</div>
                <div style="font-size:11px; color:var(--text-muted);">Puntaje 79/100 (Restaurador)</div>
              </div>

              <div style="background:var(--surface); padding:12px 14px; border-radius:8px; border-left:3px solid #10b981;">
                <div style="font-size:11px; color:var(--text-muted);">Equilibrio VFC</div>
                <div style="font-size:18px; font-weight:700; color:#10b981; margin:2px 0;">{readiness_payload['hrv_factor_percent']}%</div>
                <div style="font-size:11px; color:var(--text-muted);">Recuperación autonómica óptima</div>
              </div>

              <div style="background:var(--surface); padding:12px 14px; border-radius:8px; border-left:3px solid #f59e0b;">
                <div style="font-size:11px; color:var(--text-muted);">Tiempo de Recuperación</div>
                <div style="font-size:18px; font-weight:700; color:#f59e0b; margin:2px 0;">{readiness_payload['recovery_time_hours']} h</div>
                <div style="font-size:11px; color:var(--text-muted);">Hasta regeneración muscular plena</div>
              </div>

              <div style="background:var(--surface); padding:12px 14px; border-radius:8px; border-left:3px solid #38bdf8;">
                <div style="font-size:11px; color:var(--text-muted);">Control de Estrés</div>
                <div style="font-size:18px; font-weight:700; color:#38bdf8; margin:2px 0;">{readiness_payload['stress_factor_percent']}%</div>
                <div style="font-size:11px; color:var(--text-muted);">Carga alostática baja</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ================= TAB 1: ENDURANCE & CARGA ================= -->
      <div id="page-endurance" class="tab-page">
    <div class="layout-2">
      <!-- Estructura de Endurance Score -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Estructura del Endurance ({endurance_data_payload['score']} pts)</div>
            <div class="panel-subtitle">Descomposición factorial del modelo de resistencia</div>
          </div>
        </div>
        <div style="margin-bottom: 20px; font-size: 13px; color: var(--text-muted); line-height: 1.6;">
          Mide la resistencia ante la fatiga en esfuerzos prolongados combinando potencia aeróbica, base crónica y volumen en Zona 2:
        </div>
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
              <span>Potencia Aeróbica Pico (VO₂ Máx: {profile_data.get('vo2_max', 53.0)} ml/kg/min)</span>
              <strong>{endurance_data_payload['vo2_component']} pts (55%)</strong>
            </div>
            <div style="height:8px; background:var(--surface-elevated); border-radius:4px; overflow:hidden;">
              <div style="width: 55%; height:100%; background:var(--accent-primary);"></div>
            </div>
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
              <span>Carga Crónica Acumulada (CTL 90 días)</span>
              <strong>{endurance_data_payload['load_component']} pts (37%)</strong>
            </div>
            <div style="height:8px; background:var(--surface-elevated); border-radius:4px; overflow:hidden;">
              <div style="width: 37%; height:100%; background:var(--accent-warning);"></div>
            </div>
          </div>
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px; flex-wrap:wrap; gap:4px;">
              <span>Horas Específicas en Zona 2 ({endurance_data_payload['z2_hours_4w']} h)</span>
              <strong>{endurance_data_payload['z2_component']} pts (8%)</strong>
            </div>
            <div style="height:8px; background:var(--surface-elevated); border-radius:4px; overflow:hidden;">
              <div style="width: 8%; height:100%; background:var(--accent-z2);"></div>
            </div>
          </div>
        </div>
        <div style="margin-top: 20px; padding: 12px; background: var(--surface-elevated); border-radius: 8px; font-size: 12px; color: var(--text-muted);">
          ℹ️ Pasa el mouse sobre el gráfico PMC a la derecha: la línea vertical te permite inspeccionar simultáneamente Fitness (CTL), Fatiga (ATL) y Forma (TSB) en cada fecha.
        </div>
      </div>

      <!-- Curva PMC EWMA con Crosshair Vertical -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Curva de Gestión de Rendimiento (PMC)</div>
            <div class="panel-subtitle">Fitness (CTL), Fatiga (ATL) y Forma (TSB) • Pasa el mouse para inspeccionar</div>
          </div>
        </div>
        <div class="chart-box">
          <canvas id="chartPMC"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 2: RÉCORDS PERSONALES (PRs) ================= -->
  <div id="page-records" class="tab-page">
    <div class="panel" style="margin-bottom: 20px;">
      <div class="panel-header">
        <div>
          <div class="panel-title">Salón de Récords Personales (Personal Bests)</div>
          <div class="panel-subtitle">Tiempos certificados registrados en Garmin Connect y proyección de Maratón</div>
        </div>
      </div>
      <div class="pr-grid">
        <!-- 1K -->
        <div class="pr-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge">Velocidad Anaeróbica</span>
            <span style="font-size:10px; color:#10b981; font-weight:700;">{personal_records['1k']['delta_str']}</span>
          </div>
          <div class="pr-distance">Mejor 1 Kilómetro</div>
          <div class="pr-time">{personal_records['1k']['time_str']}</div>
          <div class="pr-meta">Ritmo: <strong>{personal_records['1k']['pace']}</strong> • {personal_records['1k']['date']}</div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Récord previo: <strong style="color:var(--text-main);">{personal_records['1k']['prev_time_str']}</strong> ({personal_records['1k']['prev_date']})</div>
            <div style="color:#38bdf8; margin-top:2px;">🎯 {personal_records['1k']['prediction_target']}</div>
          </div>
        </div>

        <!-- 1 Milla -->
        <div class="pr-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge">Potencia Aeróbica</span>
            <span style="font-size:10px; color:#10b981; font-weight:700;">{personal_records['1mi']['delta_str']}</span>
          </div>
          <div class="pr-distance">Mejor 1 Milla (1.6 km)</div>
          <div class="pr-time">{personal_records['1mi']['time_str']}</div>
          <div class="pr-meta">Ritmo: <strong>{personal_records['1mi']['pace']}</strong> • {personal_records['1mi']['date']}</div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Récord previo: <strong style="color:var(--text-main);">{personal_records['1mi']['prev_time_str']}</strong> ({personal_records['1mi']['prev_date']})</div>
            <div style="color:#38bdf8; margin-top:2px;">🎯 {personal_records['1mi']['prediction_target']}</div>
          </div>
        </div>

        <!-- 5K -->
        <div class="pr-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge">Consumo Máximo VO₂</span>
            <span style="font-size:10px; color:#10b981; font-weight:700;">{personal_records['5k']['delta_str']}</span>
          </div>
          <div class="pr-distance">Mejor 5 Kilómetros</div>
          <div class="pr-time">{personal_records['5k']['time_str']}</div>
          <div class="pr-meta">Ritmo: <strong>{personal_records['5k']['pace']}</strong> • {personal_records['5k']['date']}</div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Récord previo: <strong style="color:var(--text-main);">{personal_records['5k']['prev_time_str']}</strong> ({personal_records['5k']['prev_date']})</div>
            <div style="color:#38bdf8; margin-top:2px;">🎯 {personal_records['5k']['prediction_target']}</div>
          </div>
        </div>

        <!-- 10K -->
        <div class="pr-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge">Umbral Lactato</span>
            <span style="font-size:10px; color:#10b981; font-weight:700;">{personal_records['10k']['delta_str']}</span>
          </div>
          <div class="pr-distance">Mejores 10 Kilómetros</div>
          <div class="pr-time">{personal_records['10k']['time_str']}</div>
          <div class="pr-meta">Ritmo: <strong>{personal_records['10k']['pace']}</strong> • {personal_records['10k']['date']}</div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Récord previo: <strong style="color:var(--text-main);">{personal_records['10k']['prev_time_str']}</strong> ({personal_records['10k']['prev_date']})</div>
            <div style="color:#38bdf8; margin-top:2px;">🎯 {personal_records['10k']['prediction_target']}</div>
          </div>
        </div>

        <!-- 21K -->
        <div class="pr-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge">Capacidad Aeróbica Alta</span>
            <span style="font-size:10px; color:#10b981; font-weight:700;">{personal_records['21k']['delta_str']}</span>
          </div>
          <div class="pr-distance">Mejor Medio Maratón (21.1k)</div>
          <div class="pr-time">{personal_records['21k']['time_str']}</div>
          <div class="pr-meta">Ritmo: <strong>{personal_records['21k']['pace']}</strong> • {personal_records['21k']['date']}</div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Récord previo: <strong style="color:var(--text-main);">{personal_records['21k']['prev_time_str']}</strong> ({personal_records['21k']['prev_date']})</div>
            <div style="color:#38bdf8; margin-top:2px;">🎯 {personal_records['21k']['prediction_target']}</div>
          </div>
        </div>

        <!-- 42K (Pendiente) -->
        <div class="pr-card" style="border: 1px dashed var(--accent-warning);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="pr-badge pr-badge-pending">Próximo Desafío</span>
            <span style="font-size:10px; color:#f59e0b; font-weight:700;">Debut Proyectado</span>
          </div>
          <div class="pr-distance">Maratón Completo (42.2k)</div>
          <div class="pr-time" style="color: var(--accent-warning);">--:--:--</div>
          <div class="pr-meta">Estado: <strong>En preparación / Objetivo</strong></div>
          <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--surface-border); font-size:11px; color:var(--text-muted);">
            <div>Historial: <strong style="color:var(--text-main);">Sin registro previo</strong></div>
            <div style="color:#a855f7; margin-top:2px;">🎯 {personal_records['42k']['prediction_target']}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 3: VOLUMEN MULTIDEPORTE ================= -->
  <div id="page-multisport" class="tab-page">
    <div class="layout-2">
      <!-- Torta Multideporte (Sin Crosshair) -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Distribución de Carga por Disciplina</div>
            <div class="panel-subtitle">Horas exactas y porcentaje del volumen total</div>
          </div>
        </div>
        <div class="chart-box">
          <canvas id="chartSportsSplit"></canvas>
        </div>
      </div>

      <!-- Semanal Multideporte -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Horas Semanales por Disciplina</div>
            <div class="panel-subtitle">Equilibrio entre carrera, fuerza en gimnasio y caminata</div>
          </div>
        </div>
        <div class="chart-box">
          <canvas id="chartWeeklySports"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 4: ZONA 2 DETALLADA (MOTOR ESTILO STRAVA) ================= -->
  <div id="page-z2" class="tab-page">
    <div class="strava-volume-card" style="border-color: rgba(16, 185, 129, 0.35);">
      <div class="strava-header">
        <div class="strava-title">
          <span style="color: var(--accent-z2);">💚 Base Mitocondrial en Zona 2</span>
        </div>
        
        <div class="strava-nav-controls">
          <button class="btn-timeline" id="btn-timeline-prev-z2" onclick="moveTimelineZ2(-12)">◀ 12 Semanas Anteriores</button>
          <select class="select-timeline-year" id="select-year-z2" onchange="jumpToYearZ2(this.value)">
            {''.join(f'<option value="{y}">{y}</option>' for y in available_years)}
          </select>
          <button class="btn-timeline" id="btn-timeline-next-z2" onclick="moveTimelineZ2(12)">12 Semanas Siguientes ▶</button>
          <button class="btn-timeline" style="border-color:var(--accent-z2); color:var(--accent-z2);" onclick="resetTimelineZ2ToNow()">Hoy (Reciente)</button>
        </div>

        <div style="font-size:12px; font-weight:700; color:var(--accent-z2); background:rgba(16,185,129,0.12); padding:6px 14px; border-radius:8px;">
          Rango Cardíaco Z2: 142 - 158 ppm (FatMax)
        </div>
      </div>

      <div class="strava-stats-row">
        <div class="strava-stat-col">
          <span class="strava-stat-label">Esta Semana en Z2</span>
          <span class="strava-stat-value" id="z2-stat-week" style="color:var(--accent-z2);">{current_week_stats['z2_hours']} h</span>
        </div>
        <div class="strava-stat-col">
          <span class="strava-stat-label">Acumulado 4 Semanas</span>
          <span class="strava-stat-value" style="color:var(--accent-z2);">{endurance_data_payload['z2_hours_4w']} h</span>
        </div>
        <div class="strava-stat-col">
          <span class="strava-stat-label">Proporción Polarizada</span>
          <span class="strava-stat-value">79% Óptimo</span>
        </div>
        <div class="strava-stat-col" style="border-left: 1px solid var(--surface-border); padding-left: 24px;">
          <span class="strava-stat-label">Oxidación Lipídica</span>
          <span class="strava-stat-value" style="color:#38bdf8;">Máxima (FatMax)</span>
        </div>
      </div>

      <div style="font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px;">
        Curva Continua de Zona 2 (12 Semanas): <span id="z2-window-dates" style="color:var(--text-main); font-family:'JetBrains Mono';">Semanas recientes</span>
      </div>

      <div class="strava-chart-container">
        <canvas id="chartZ2Dynamic"></canvas>
      </div>

      <div class="strava-footer-text">
        <span>● Curva esmeralda con nodos resaltados • Horas de base aeróbica</span>
        <span>Aclaramiento de Lactato MCT-1 Activo</span>
      </div>
    </div>

    <!-- Regla 80/20 y Desacople -->
    <div class="layout-2">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">Polarización del Entrenamiento (80/20)</div>
        </div>
        <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
          Distribución de tu tiempo total en las distintas intensidades cardíacas:
        </div>
        <div style="height: 200px;">
          <canvas id="chartPolarization"></canvas>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Control de Desacople Aeróbico (&lt; 5%)</div>
            <div class="panel-subtitle">Índice Pa:HR • Estabilidad cardíaca ante el ritmo sostenido</div>
          </div>
          <span class="badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text); border:1px solid var(--pastel-mint-border);">✓ Base Eficiente</span>
        </div>
        <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px; line-height: 1.55;">
          <strong>¿Qué significa de forma simple?</strong> Si en una tirada larga corrés al mismo ritmo, lo ideal es que tu corazón mantenga los mismos latidos. Si el pulso empieza a subir solo mientras el ritmo se mantiene igual o cae (deriva cardíaca), tu cuerpo se está desacoplando por deshidratación o fatiga mitocondrial.
          Un desacople menor al 5% certifica que podés correr horas en Zona 2 sin desgaste excesivo.
        </div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div style="background:var(--surface-elevated); padding:14px; border-radius:10px; font-size:13px; border-left:4px solid #10b981;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-weight:700; color:var(--text-main);">Tirada Larga 15.5K Buenos Aires (04/10/2026) • 1h 33m</span>
              <span class="badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text);">+3.8%</span>
            </div>
            <div style="color:var(--pastel-mint-text); font-size:12px; margin-top:4px; font-weight:600;">✓ Acoplamiento Óptimo (&lt; 5%): El pulso se mantuvo estable entre la 1ra y 2da mitad. Excelente economía de carrera.</div>
          </div>
          <div style="background:var(--surface-elevated); padding:14px; border-radius:10px; font-size:13px; border-left:4px solid #94a3b8;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-weight:700; color:var(--text-main);">Progresivo 3.5K (07/10/2026) • 22m</span>
              <span class="badge" style="background:var(--bg-subtle); color:var(--text-muted);">No aplica</span>
            </div>
            <div style="color:var(--text-muted); font-size:12px; margin-top:4px;">ℹ️ Sesión corta: el test de desacople requiere al menos 45 a 60 minutos continuos para que aparezca la deriva fisiológica.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 5: SUEÑO FISIOLÓGICO & VFC AUTONÓMICA ================= -->
  <div id="page-recovery" class="tab-page">
    <!-- Arquitectura de Sueño Puro Garmin -->
    <div class="panel" style="margin-bottom: 20px;">
      <div class="panel-header">
        <div>
          <div class="panel-title">Arquitectura del Sueño Fisiológico Garmin ({today_sleep_hours}h • {today_sleep_score}/100)</div>
          <div class="panel-subtitle">Desglose de fases restauradoras (profundo y REM) y estrés autónomo nocturno sin mezcla de pasos</div>
        </div>
        <span class="badge" style="background:rgba(96,165,250,0.15); color:#60a5fa; font-weight:700;">Score: {today_sleep_score}/100</span>
      </div>

      <!-- Barra Segmentada de Fases de Sueño -->
      <div style="margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted); margin-bottom:8px;">
          <span>Distribución de la última noche: <strong>{today_sleep_hours} horas totales</strong></span>
          <span>Siesta adicional: <strong>{today_nap_min} min</strong> • Despierto: <strong>{today_awake_min} min</strong></span>
        </div>
        <div style="height:20px; background:var(--surface-elevated); border-radius:6px; overflow:hidden; display:flex;">
          <div style="width:{round((today_deep_hours / max(1, today_sleep_hours)) * 100)}%; background:#3b82f6;" title="Profundo: {today_deep_hours}h"></div>
          <div style="width:{round((today_rem_hours / max(1, today_sleep_hours)) * 100)}%; background:#8b5cf6;" title="REM: {today_rem_hours}h"></div>
          <div style="width:{round((today_light_hours / max(1, today_sleep_hours)) * 100)}%; background:#38bdf8;" title="Ligero: {today_light_hours}h"></div>
        </div>
        <div style="display:flex; gap:16px; font-size:11px; margin-top:8px; flex-wrap:wrap;">
          <span style="color:#3b82f6;">● Sueño Profundo: <strong>{today_deep_hours}h (24% • Excelente regeneración física)</strong></span>
          <span style="color:#8b5cf6;">● Sueño REM: <strong>{today_rem_hours}h (13% • Consolidación neural)</strong></span>
          <span style="color:#38bdf8;">● Sueño Ligero: <strong>{today_light_hours}h (63% • Transición)</strong></span>
          <span style="color:var(--text-muted);">● Estrés Nocturno Medio: <strong>{today_sleep_stress} pts (Bajo)</strong></span>
        </div>
      </div>

      <div class="layout-2">
        <!-- VFC Nocturna -->
        <div>
          <div style="font-size:14px; font-weight:700; margin-bottom:4px; color:var(--text-main);">Corredor Basal de VFC Nocturna (RMSSD)</div>
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Monitoreo continuo durante el sueño para evaluar equilibrio autonómico:</div>
          <div style="height: 220px;">
            <canvas id="chartHRVBase"></canvas>
          </div>
        </div>

        <!-- Tendencia de Horas y Puntaje de Sueño Histórico -->
        <div>
          <div style="font-size:14px; font-weight:700; margin-bottom:4px; color:var(--text-main);">Evolución Histórica de Sueño & Score</div>
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Horas dormidas y puntuación de calidad noche a noche:</div>
          <div style="height: 220px;">
            <canvas id="chartSleepSteps"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Frecuencia Cardíaca en Reposo (RHR) -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Frecuencia Cardíaca en Reposo (RHR)</div>
          <div class="panel-subtitle">Estabilidad del pulso basal matutino como detector precoz de sobrecarga</div>
        </div>
      </div>
      <div style="height: 200px;">
        <canvas id="chartRHRTrend"></canvas>
      </div>
    </div>
  </div>

  <!-- ================= TAB 6: BITÁCORA DE SESIONES ================= -->
  <div id="page-table" class="tab-page">
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Bitácora Integral de Sesiones</div>
          <div class="panel-subtitle">Haz clic en cualquier fila para inspeccionar la fisiología y zonas Z1-Z5 de esa sesión</div>
        </div>
      </div>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Actividad</th>
              <th>Disciplina</th>
              <th>Intensidad</th>
              <th>Distancia</th>
              <th>Tiempo</th>
              <th>FC Prom / Máx</th>
              <th>Carga</th>
              <th>Zona 2</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="table-raw-body">
            <!-- Rellenado por JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ================= TAB 7: GLOSARIO & CIENCIA (INFO) ================= -->
  <div id="page-info" class="tab-page">
    <div class="panel" style="margin-bottom: 20px;">
      <div class="panel-header">
        <div>
          <div class="panel-title">Compendio Fisiológico & Metodología de Métricas</div>
          <div class="panel-subtitle">Definición científica rigurosa, fórmulas de cálculo y por qué las medimos</div>
        </div>
        <!-- Buscador Reactivo de Términos -->
        <div style="position:relative; min-width:260px;">
          <input type="text" id="glossary-search" placeholder="🔍 Buscar término (ej. ATL, Z2, EPOC)..." oninput="filterGlossary(this.value)" style="width:100%; background:var(--surface-elevated); border:1px solid var(--surface-border); border-radius:var(--radius-pill); padding:8px 16px; font-size:12.5px; color:var(--text-main); outline:none;">
        </div>
      </div>

      <div id="glossary-items-container" style="display:flex; flex-direction:column; gap:14px;">
        <!-- EPOC -->
        <div class="info-card" data-term="epoc exceso consumo oxigeno post ejercicio carga">
          <div class="info-header">
            <span class="info-tag" style="background:rgba(244,63,94,0.15); color:#f43f5e;">EPOC</span>
            <span class="info-title">Exceso de Consumo de Oxígeno Post-Ejercicio (Excess Post-Exercise Oxygen Consumption)</span>
          </div>
          <div class="info-desc">
            Volumen de oxígeno adicional que tu cuerpo consume tras el esfuerzo para restablecer los depósitos de fosfocreatina, metabolizar el lactato residual y reparar microdaño muscular. Es la unidad matemática base con la que Garmin calcula los puntos de carga de cada sesión.
          </div>
          <div class="info-why">
            <strong>¿Por qué lo medimos?</strong> Refleja el costo fisiológico y metabólico real del entrenamiento, mucho más allá de los kilómetros o la velocidad promedio.
          </div>
        </div>

        <!-- Training Effect -->
        <div class="info-card" data-term="training effect te efecto entrenamiento aerobico anaerobico">
          <div class="info-header">
            <span class="info-tag" style="background:rgba(56,189,248,0.15); color:#38bdf8;">TRAINING EFFECT (TE)</span>
            <span class="info-title">Efecto del Entrenamiento Aeróbico y Anaeróbico (Escala 0.0 a 5.0)</span>
          </div>
          <div class="info-desc">
            Puntuación patentada por Firstbeat Analytics que califica el impacto de una actividad en tu condición física: 1.0-1.9 (Recuperación), 2.0-2.9 (Mantenimiento), 3.0-3.9 (Mejora aeróbica sustancial), 4.0-4.9 (Sobrecarga de alto impacto) y 5.0 (Sobreesfuerzo).
          </div>
          <div class="info-why">
            <strong>¿Por qué lo medimos?</strong> Permite dosificar con precisión quirúrgica las sesiones para que los fondos largos no destruyan el músculo ni los intervalos queden cortos en intensidad.
          </div>
        </div>

        <!-- Foco de Carga Firstbeat -->
        <div class="info-card" data-term="foco carga load balance balance firstbeat anaerobico aerobico alto bajo">
          <div class="info-header">
            <span class="info-tag" style="background:rgba(245,158,11,0.15); color:#f59e0b;">FOCO DE CARGA</span>
            <span class="info-title">Equilibrio de Carga en 4 Semanas (Training Load Balance)</span>
          </div>
          <div class="info-desc">
            Descompone el estrés fisiológico de los últimos 28 días en tres cilindros: <strong>Anaeróbico</strong> (sprints y Z5), <strong>Aeróbico Alto</strong> (tempo y umbral lactato Z3-Z4) y <strong>Aeróbico Bajo</strong> (base y Z2). Cada atleta tiene túneles objetivo específicos según su VO₂ Máx y volumen acumulado.
          </div>
          <div class="info-why">
            <strong>¿Por qué lo medimos?</strong> Previene el estancamiento al alertar si falta trabajo de umbral o si hay déficit de base aeróbica mitocondrial.
          </div>
        </div>

        <!-- Training Readiness -->
        <div class="info-card" data-term="training readiness predisposicion disposicion entreno fatiga sueno hrv">
          <div class="info-header">
            <span class="info-tag" style="background:rgba(16,185,129,0.15); color:#10b981;">TRAINING READINESS</span>
            <span class="info-title">Disposición para Entrenar (Puntaje 0 a 100)</span>
          </div>
          <div class="info-desc">
            Métrica holística que pondera la calidad del sueño de la noche previa, el historial de sueño de las últimas noches, el equilibrio de VFC, el tiempo de recuperación restante, la carga aguda de entrenamiento y el historial de estrés durante el día.
          </div>
          <div class="info-why">
            <strong>¿Por qué lo medimos?</strong> Te indica si tu sistema nervioso y muscular están listos para una sesión de alta exigencia (series de pista) o si conviene una tirada suave regenerativa.
          </div>
        </div>

      <!-- Estado de Entreno Garmin -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag" style="background:rgba(16,185,129,0.15); color:#10b981;">ESTADO DE ENTRENO</span>
          <span class="info-title">Training Status Oficial Garmin / Firstbeat</span>
        </div>
        <div class="info-desc">
          Evaluación holística que cruza tu carga aguda de entrenamiento a 7 días con la trayectoria de tu VO₂ Máx. Identifica si tu esfuerzo produce adaptaciones positivas (Productivo), mantiene tu base (Mantenimiento), o si hay sobrecarga sin recuperación (No Productivo / Sobreesfuerzo).
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Es el semáforo definitivo de mejora. Evita entrenar sin rumbo y garantiza que los aumentos de volumen realmente se traduzcan en mayor velocidad y eficiencia.
        </div>
      </div>

      <!-- VO2 Max -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">VO₂ MÁX</span>
          <span class="info-title">Consumo Máximo de Oxígeno</span>
        </div>
        <div class="info-desc">
          Es el volumen máximo de oxígeno (en ml/kg/min) que tus pulmones pueden captar, tu corazón bombear y tus músculos mitocondriales extraer y utilizar durante el esfuerzo máximo.
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Es el techo aeróbico absoluto del deportista. Determina el potencial biológico máximo de velocidad en carreras de fondo y medio fondo.
        </div>
      </div>

      <!-- Endurance -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">ENDURANCE</span>
          <span class="info-title">Puntuación de Resistencia</span>
        </div>
        <div class="info-desc">
          Indicador multifactorial que integra la capacidad aeróbica máxima (VO₂), la solidez de la carga crónica acumulada (CTL) y el volumen específico de trabajo a ritmo sostenible (Zona 2).
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Dos corredores pueden tener el mismo VO₂ Máx, pero el que tenga mayor Endurance mantendrá el ritmo por horas con menor fatiga cardíaca y menor consumo de glucógeno.
        </div>
      </div>

      <!-- CTL -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">CTL (Fitness)</span>
          <span class="info-title">Carga de Entrenamiento Crónica (Chronic Training Load)</span>
        </div>
        <div class="info-desc">
          Promedio móvil ponderado exponencialmente (EWMA con constante de tiempo de 42 días) de tu estrés de entrenamiento diario. Representa tu adaptación fisiológica acumulada.
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Una sesión aislada no crea condición física. El CTL refleja la capacidad de trabajo real construida a lo largo de meses sin decaer.
        </div>
      </div>

      <!-- ATL -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">ATL (Fatiga)</span>
          <span class="info-title">Carga de Entrenamiento Aguda (Acute Training Load)</span>
        </div>
        <div class="info-desc">
          Promedio móvil exponencial con constante de tiempo de 7 días. Mide el estrés y la fatiga residual acumulada en la última semana tras entrenamientos intensos o tiradas largas.
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> La fatiga enmascara el fitness. Si el ATL sube violentamente, el rendimiento decae temporalmente hasta que se produce la supercompensación.
        </div>
      </div>

      <!-- TSB -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">TSB (Forma)</span>
          <span class="info-title">Balance de Estrés del Entrenamiento (Training Stress Balance)</span>
        </div>
        <div class="info-desc">
          Calculado como <code>TSB = CTL - ATL</code>. Representa tu frescura neuromuscular y metabólica. Un TSB positivo (+5 a +20) es ideal para el día de una carrera importante (tapering).
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Permite planificar el pico de rendimiento exacto para el día de una competencia, asegurando que no llegues fatigado a la línea de largada.
        </div>
      </div>

      <!-- ACWR -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">ACWR</span>
          <span class="info-title">Relación de Carga Aguda sobre Crónica (Acute:Chronic Workload Ratio)</span>
        </div>
        <div class="info-desc">
          Cociente entre la fatiga aguda (7 días) y la base crónica (28 días). Desarrollado por el Dr. Tim Gabbett para cuantificar el riesgo de lesiones deportivas. El rango óptimo ("Sweet Spot") es de <strong>0.80 a 1.30</strong>.
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Ratios superiores a 1.50 duplican o triplican el riesgo de lesiones por sobreuso (periostitis, tendinopatías), mientras que ratios menores a 0.80 indican desentrenamiento.
        </div>
      </div>

      <!-- HRV / VFC -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">VFC / RMSSD</span>
          <span class="info-title">Variabilidad de la Frecuencia Cardíaca (Tono Vagal)</span>
        </div>
        <div class="info-desc">
          Mide las variaciones de tiempo entre latido y latido registradas durante el sueño profundo. Una VFC alta refleja predominancia del sistema nervioso parasimpático (recuperación y descanso).
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Es el detector fisiológico más sensible del sobreentrenamiento, estrés crónico o infección subclínica antes de que aparezcan los síntomas.
        </div>
      </div>

      <!-- Zonas Cardíacas Z1 - Z5 -->
      <div class="info-card">
        <div class="info-header">
          <span class="info-tag">ZONAS 1 A 5</span>
          <span class="info-title">Zonificación Cardíaca y Vías Metabólicas</span>
        </div>
        <div class="info-desc">
          • <strong>Zona 1 (&lt; 142 ppm):</strong> Recuperación activa y flujo capilar regenerativo.<br>
          • <strong>Zona 2 (142 - 158 ppm):</strong> Base aeróbica mitocondrial, combustión lipídica (FatMax) y aclaramiento de lactato.<br>
          • <strong>Zona 3 (158 - 169 ppm):</strong> Tempo aeróbico medio.<br>
          • <strong>Zona 4 (169 - 178 ppm):</strong> Umbral de lactato, ritmo de carrera de 10K y Medio Maratón.<br>
          • <strong>Zona 5 (&gt; 178 ppm):</strong> Potencia anaeróbica pura y VO₂ Máx.
        </div>
        <div class="info-why">
          <strong>¿Por qué lo medimos?</strong> Entrenar sin control de zonas produce el síndrome del "ritmo basura". La polarización 80/20 garantiza progresar sin estancarse ni lesionarse.
        </div>
      </div>

        </div>
      </div>
    </div>
  </div>

    </main>
  </div>
</div>

<!-- MODAL INTERACTIVO DE DETALLE DE SESIÓN -->
<div id="activity-modal" class="modal-overlay" onclick="closeActivityModal(event)">
  <div class="modal-box" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="closeModalDirect()">&times;</button>
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
      <span id="modal-sport-badge" class="badge badge-run">Carrera</span>
      <span id="modal-date" style="font-size:12px; color:var(--text-muted); font-family:'JetBrains Mono';">--/--/----</span>
    </div>
    <div id="modal-title" style="font-size:20px; font-weight:700; color:var(--text-main); margin-bottom:12px;">Detalle de Sesión</div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(110px, 1fr)); gap:10px; margin-bottom:18px; background:var(--surface-elevated); padding:14px; border-radius:8px;">
      <div>
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Distancia</div>
        <div id="modal-dist" style="font-size:16px; font-weight:700; font-family:'JetBrains Mono';">-- km</div>
      </div>
      <div>
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Duración</div>
        <div id="modal-dur" style="font-size:16px; font-weight:700; font-family:'JetBrains Mono';">-- min</div>
      </div>
      <div>
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Ritmo Medio</div>
        <div id="modal-pace" style="font-size:16px; font-weight:700; font-family:'JetBrains Mono';">--/km</div>
      </div>
      <div>
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">FC Prom / Máx</div>
        <div id="modal-hr" style="font-size:16px; font-weight:700; font-family:'JetBrains Mono';">-- / -- ppm</div>
      </div>
      <div>
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Carga Sesión</div>
        <div id="modal-load" style="font-size:16px; font-weight:700; font-family:'JetBrains Mono';">--</div>
      </div>
    </div>

    <div style="font-size:14px; font-weight:700; margin-bottom:8px;">Comportamiento Cardíaco por Zonas (Z1 a Z5)</div>
    
    <div class="zone-bar">
      <div id="bar-z1" class="zone-bar-segment" style="background:#94a3b8; width:0%;"></div>
      <div id="bar-z2" class="zone-bar-segment" style="background:#10b981; width:0%;"></div>
      <div id="bar-z3" class="zone-bar-segment" style="background:#38bdf8; width:0%;"></div>
      <div id="bar-z4" class="zone-bar-segment" style="background:#f59e0b; width:0%;"></div>
      <div id="bar-z5" class="zone-bar-segment" style="background:#f43f5e; width:0%;"></div>
    </div>

    <div style="display:flex; flex-direction:column; gap:8px; font-size:12px; margin-bottom:16px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#94a3b8;">● Zona 1 - Recuperación (&lt; 142 ppm)</span>
        <strong id="val-z1">-- min (--%)</strong>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#10b981;">● Zona 2 - Base Aeróbica (142 - 158 ppm)</span>
        <strong id="val-z2">-- min (--%)</strong>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#38bdf8;">● Zona 3 - Tempo (158 - 169 ppm)</span>
        <strong id="val-z3">-- min (--%)</strong>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#f59e0b;">● Zona 4 - Umbral Lactato (169 - 178 ppm)</span>
        <strong id="val-z4">-- min (--%)</strong>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="color:#f43f5e;">● Zona 5 - Anaeróbico (&gt; 178 ppm)</span>
        <strong id="val-z5">-- min (--%)</strong>
      </div>
    </div>

    <div style="height: 180px; margin-top: 10px;">
      <canvas id="modalZoneChart"></canvas>
    </div>
  </div>
</div>

<!-- MODAL EXPLICATIVO CON SEMÁFORO Y ESCALA MULTIZONA -->
<div id="kpi-modal" class="modal-overlay" onclick="closeKpiModal(event)">
  <div class="modal-box" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="closeKpiModalDirect()">&times;</button>
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
      <span id="kpi-modal-badge" class="badge badge-run">KPI Analítico</span>
    </div>
    <div id="kpi-modal-title" style="font-size:20px; font-weight:700; color:var(--text-main); margin-bottom:8px;">Título del Indicador</div>
    <div id="kpi-modal-desc" style="font-size:13px; color:var(--text-muted); line-height:1.6; margin-bottom:14px;">Descripción</div>

    <!-- Semáforo / Escala Visual Completa -->
    <div class="spectrum-gauge">
      <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:6px;">Escala de Rangos & Estado Fisiológico</div>
      <div class="spectrum-track" id="kpi-spectrum-track"></div>
      <div class="spectrum-legend" id="kpi-spectrum-legend"></div>
      <div class="spectrum-current-marker" id="kpi-spectrum-current"></div>
    </div>

    <div style="background:var(--surface-elevated); padding:12px 16px; border-radius:8px; margin:16px 0;">
      <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600;">Fórmula & Metodología de Cálculo</div>
      <div id="kpi-modal-formula" style="font-family:'JetBrains Mono'; font-size:12px; color:var(--text-main); margin-top:4px;">Fórmula</div>
    </div>

    <div style="font-size:14px; font-weight:700; margin-bottom:8px;">Evolución Conforme al Tiempo</div>
    <div style="height: 180px;">
      <canvas id="kpiModalChart"></canvas>
    </div>
  </div>
</div>

<!-- JAVASCRIPT REACTIVO: STRAVA TIMELINE NAVIGATOR & KPIS -->
<script>
  const ACTIVITIES = {json.dumps(activities)};
  const PMC_DATA = {json.dumps(pmc_series)};
  const RECOVERY_DATA = {json.dumps(recovery_metrics)};
  const ENDURANCE_INFO = {json.dumps(endurance_data_payload)};
  const FULL_TIMELINE_WEEKS = {json.dumps(full_timeline_weeks)};
  const TRAINING_STATUS_INFO = {json.dumps(training_status_payload)};
  const CONSISTENCY_WEEKS = {json.dumps(consistency_weeks_list)};
  const RACE_PRED_HISTORY = {json.dumps(race_predictions_history)};
  const USER_VO2 = {profile_data.get('vo2_max', 53.0)};

  let charts = {{}};
  let modalChart = null;
  let kpiChart = null;
  let currentStravaMode = 'km';

  // Índice de inicio de la ventana de 12 semanas (por defecto el final)
  let windowEndIdx = FULL_TIMELINE_WEEKS.length; // slice [windowEndIdx - 12, windowEndIdx]

  // Plugin Crosshair Vertical Filtrado
  const verticalCrosshairPlugin = {{
    id: 'verticalCrosshair',
    afterDatasetsDraw(chart) {{
      if (['doughnut', 'pie', 'polarArea'].includes(chart.config.type)) return;
      if (chart.config.options?.plugins?.crosshair === false) return;

      if (chart.tooltip && chart.tooltip._active && chart.tooltip._active.length) {{
        const activePoint = chart.tooltip._active[0];
        const ctx = chart.ctx;
        const x = activePoint.element.x;
        const topY = chart.scales.y ? chart.scales.y.top : (chart.scales.yDaily ? chart.scales.yDaily.top : chart.chartArea.top);
        const bottomY = chart.scales.y ? chart.scales.y.bottom : (chart.scales.yDaily ? chart.scales.yDaily.bottom : chart.chartArea.bottom);

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, topY);
        ctx.lineTo(x, bottomY);
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.restore();
      }}
    }}
  }};
  Chart.register(verticalCrosshairPlugin);

  document.addEventListener('DOMContentLoaded', () => {{
    renderTable();
    initCharts();
    initStravaChart();
    updateTimelineNavButtons();
    initStravaZ2Chart();
    updateTimelineNavButtonsZ2();
  }});

  function toggleTheme() {{
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    setTimeout(() => {{
      Object.values(charts).forEach(c => c && c.update());
      if (modalChart) modalChart.update();
      if (kpiChart) kpiChart.update();
    }}, 50);
  }}

  function showTab(pageId) {{
    document.querySelectorAll('.sidebar-nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
    
    const targetBtn = Array.from(document.querySelectorAll('.sidebar-nav-btn')).find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(pageId));
    if (targetBtn) targetBtn.classList.add('active');

    const page = document.getElementById(pageId);
    if (page) {{
      page.classList.add('active');
      setTimeout(() => {{
        Object.values(charts).forEach(c => c && c.resize());
      }}, 40);
    }}
  }}

  // ==========================================
  // NAVEGADOR TEMPORAL INFINITO (STRAVA VOLUME)
  // ==========================================
  function getCurrent12WeeksSlice() {{
    const start = Math.max(0, windowEndIdx - 12);
    return FULL_TIMELINE_WEEKS.slice(start, windowEndIdx);
  }}

  function initStravaChart() {{
    const ctx = document.getElementById('chartStravaVolume').getContext('2d');
    const currentSlice = getCurrent12WeeksSlice();

    const gradient = ctx.createLinearGradient(0, 0, 0, 220);
    gradient.addColorStop(0, 'rgba(252, 82, 0, 0.45)');
    gradient.addColorStop(0.7, 'rgba(252, 82, 0, 0.12)');
    gradient.addColorStop(1, 'rgba(252, 82, 0, 0.00)');

    const labels = currentSlice.map(w => w.month + ' ' + w.label);
    const dataVals = currentSlice.map(w => w.dist_km);

    const pointRadii = currentSlice.map(w => w.is_current ? 7 : 4);
    const pointBgColors = currentSlice.map(w => w.is_current ? '#fc5200' : '#07090e');
    const pointBorderColors = currentSlice.map(w => w.is_current ? '#ffffff' : '#fc5200');
    const pointBorderWidths = currentSlice.map(w => w.is_current ? 3 : 2);

    charts.strava = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'Kilómetros Semanales',
          data: dataVals,
          borderColor: '#fc5200',
          borderWidth: 2.5,
          backgroundColor: gradient,
          fill: true,
          tension: 0.25,
          pointRadius: pointRadii,
          pointBackgroundColor: pointBgColors,
          pointBorderColor: pointBorderColors,
          pointBorderWidth: pointBorderWidths,
          pointHoverRadius: 8
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#0b111e',
            borderColor: '#334155',
            borderWidth: 1,
            titleColor: '#f1f5f9',
            bodyColor: '#cbd5e1',
            callbacks: {{
              title: ctx => {{
                const slice = getCurrent12WeeksSlice();
                return 'Semana ' + slice[ctx[0].dataIndex].label + ' (' + slice[ctx[0].dataIndex].year + ')';
              }},
              label: ctx => {{
                const slice = getCurrent12WeeksSlice();
                const item = slice[ctx.dataIndex];
                if (currentStravaMode === 'km') return `Distancia: ${{item.dist_km}} km (${{item.dur_str}})`;
                if (currentStravaMode === 'z2') return `Zona 2 Base: ${{item.z2_hours}} h (${{item.dist_km}} km)`;
                return `Carga Semanal: ${{item.load}} pts (${{item.activities}} sesiones)`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            min: 0,
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{
              color: '#94a3b8',
              callback: v => v + ' km',
              stepSize: 25
            }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{
              color: '#94a3b8',
              maxTicksLimit: 6,
              callback: function(val, index) {{
                const slice = getCurrent12WeeksSlice();
                const w = slice[index];
                return (index % 4 === 0 || index === slice.length - 1) ? w.month : '';
              }}
            }}
          }}
        }}
      }}
    }});

    updateStravaTopCard(currentSlice[currentSlice.length - 1]);
  }}

  function moveTimeline(deltaWeeks) {{
    windowEndIdx = Math.min(FULL_TIMELINE_WEEKS.length, Math.max(12, windowEndIdx + deltaWeeks));
    updateStravaChartWindow();
    updateTimelineNavButtons();
  }}

  function resetTimelineToNow() {{
    windowEndIdx = FULL_TIMELINE_WEEKS.length;
    updateStravaChartWindow();
    updateTimelineNavButtons();
  }}

  function jumpToYear(yearStr) {{
    const y = parseInt(yearStr);
    // Encontrar la última semana de ese año en el timeline
    let targetIdx = -1;
    for (let i = FULL_TIMELINE_WEEKS.length - 1; i >= 0; i--) {{
      if (FULL_TIMELINE_WEEKS[i].year === y) {{
        targetIdx = i + 1;
        break;
      }}
    }}
    if (targetIdx !== -1) {{
      windowEndIdx = Math.max(12, targetIdx);
      updateStravaChartWindow();
      updateTimelineNavButtons();
    }}
  }}

  function updateTimelineNavButtons() {{
    const btnPrev = document.getElementById('btn-timeline-prev');
    const btnNext = document.getElementById('btn-timeline-next');
    btnPrev.disabled = (windowEndIdx <= 12);
    btnNext.disabled = (windowEndIdx >= FULL_TIMELINE_WEEKS.length);
  }}

  function updateStravaChartWindow() {{
    const currentSlice = getCurrent12WeeksSlice();
    const isNow = (windowEndIdx >= FULL_TIMELINE_WEEKS.length);

    document.getElementById('strava-week-title').textContent = isNow ? 'Esta semana' : 'Semana de ' + currentSlice[currentSlice.length - 1].label + ' (' + currentSlice[currentSlice.length - 1].year + ')';
    document.getElementById('strava-window-dates').textContent = `${{currentSlice[0].label}}/${{currentSlice[0].year}} ➔ ${{currentSlice[currentSlice.length - 1].label}}/${{currentSlice[currentSlice.length - 1].year}}`;
    document.getElementById('strava-node-hint').textContent = isNow ? '● Nodo naranja resaltado: Semana actual en curso' : '● Nodo naranja resaltado: Semana seleccionada de referencia';

    const ctx = document.getElementById('chartStravaVolume').getContext('2d');
    let color = '#fc5200';
    let label = 'Kilómetros Semanales';
    let dataVals = [];
    let tickUnit = ' km';
    let step = 25;

    if (currentStravaMode === 'z2') {{
      color = '#10b981';
      label = 'Horas en Zona 2';
      dataVals = currentSlice.map(w => w.z2_hours);
      tickUnit = ' h';
      step = 2;
    }} else if (currentStravaMode === 'load') {{
      color = '#f59e0b';
      label = 'Carga de Entrenamiento';
      dataVals = currentSlice.map(w => w.load);
      tickUnit = ' pts';
      step = 150;
    }} else {{
      color = '#fc5200';
      label = 'Kilómetros Semanales';
      dataVals = currentSlice.map(w => w.dist_km);
      tickUnit = ' km';
      step = 25;
    }}

    const grad = ctx.createLinearGradient(0, 0, 0, 220);
    grad.addColorStop(0, color + '66');
    grad.addColorStop(0.7, color + '18');
    grad.addColorStop(1, color + '00');

    charts.strava.data.labels = currentSlice.map(w => w.month + ' ' + w.label);
    charts.strava.data.datasets[0].label = label;
    charts.strava.data.datasets[0].data = dataVals;
    charts.strava.data.datasets[0].borderColor = color;
    charts.strava.data.datasets[0].backgroundColor = grad;
    charts.strava.data.datasets[0].pointRadius = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? 7 : 4);
    charts.strava.data.datasets[0].pointBorderColor = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? '#ffffff' : color);
    charts.strava.data.datasets[0].pointBackgroundColor = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? color : '#07090e');
    charts.strava.options.scales.y.ticks.callback = v => v + tickUnit;
    charts.strava.options.scales.y.ticks.stepSize = step;
    charts.strava.update();

    updateStravaTopCard(currentSlice[currentSlice.length - 1]);
  }}

  function updateStravaTopCard(weekItem) {{
    document.getElementById('strava-stat-dist').textContent = `${{weekItem.dist_km}} km`;
    document.getElementById('strava-stat-time').textContent = weekItem.dur_str;
    document.getElementById('strava-stat-elev').textContent = `${{weekItem.elev_m}} m`;
    document.getElementById('strava-stat-z2').textContent = `${{weekItem.z2_hours}} h`;
  }}

  function switchStravaMode(mode) {{
    currentStravaMode = mode;
    document.getElementById('btn-strava-km').classList.toggle('active', mode === 'km');
    document.getElementById('btn-strava-z2').classList.toggle('active', mode === 'z2');
    document.getElementById('btn-strava-load').classList.toggle('active', mode === 'load');
    updateStravaChartWindow();
  }}

  // ==========================================
  // MODALES ANALITICOS CON SEMAFOROS Y MATRIX
  // ==========================================
  function openKpiModal(kpiType) {{
    const modal = document.getElementById('kpi-modal');
    const titleEl = document.getElementById('kpi-modal-title');
    const descEl = document.getElementById('kpi-modal-desc');
    const formulaEl = document.getElementById('kpi-modal-formula');
    const badgeEl = document.getElementById('kpi-modal-badge');
    const trackEl = document.getElementById('kpi-spectrum-track');
    const legendEl = document.getElementById('kpi-spectrum-legend');
    const currentEl = document.getElementById('kpi-spectrum-current');

    let chartLabels = [];
    let chartData = [];
    let chartLabel = '';
    let kpiThemeBg = 'var(--pastel-mint-bg)';
    let kpiThemeText = 'var(--pastel-mint-text)';
    let kpiThemeBorder = 'var(--pastel-mint-border)';

    if (kpiType === 'training_status') {{
      badgeEl.textContent = 'Training Status Oficial';
      badgeEl.style.color = '#10b981';
      titleEl.textContent = 'Estado de Entreno Garmin (Forerunner 265)';
      descEl.textContent = 'Mide cómo responde fisiológicamente tu cuerpo ante el volumen y la intensidad. Combina la carga aguda (7 días) con los cambios en tu VO₂ Máx para determinar si estás asimilando el entrenamiento de forma productiva o si necesitás descargar.';
      formulaEl.textContent = 'Algoritmo Firstbeat Analytics: Cruzamiento multidimensional entre Carga Aguda (7d) y Tendencia de VO₂ Máx en ascenso.';
      
      // Matriz de Estados de Garmin
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:14%; background:#94a3b8;" title="Desentrenamiento"></div>
        <div class="spectrum-segment" style="width:14%; background:#60a5fa;" title="Recuperación"></div>
        <div class="spectrum-segment" style="width:14%; background:#f59e0b;" title="Mantenimiento"></div>
        <div class="spectrum-segment" style="width:18%; background:#10b981;" title="Productivo (Óptimo)"></div>
        <div class="spectrum-segment" style="width:14%; background:#38bdf8;" title="Pico de Forma"></div>
        <div class="spectrum-segment" style="width:13%; background:#f97316;" title="No Productivo"></div>
        <div class="spectrum-segment" style="width:13%; background:#ef4444;" title="Sobreesfuerzo"></div>
      `;
      legendEl.innerHTML = `
        <span>Desentreno</span>
        <span>Recuperación</span>
        <span>Mantenimiento</span>
        <span style="color:#10b981; font-weight:bold;">Productivo</span>
        <span>Pico</span>
        <span>Sobreesfuerzo</span>
      `;
      currentEl.innerHTML = `
        <span>Tu estado actual: <strong>${{TRAINING_STATUS_INFO.status_title}}</strong> (Carga aguda: ${{TRAINING_STATUS_INFO.acute_load}} pts)</span>
        <span style="color:#10b981; font-weight:700;">● ${{TRAINING_STATUS_INFO.feedback_phrase}}</span>
      `;

      chartLabels = TRAINING_STATUS_INFO.history.map(h => h.date_arg);
      chartData = TRAINING_STATUS_INFO.history.map(h => h.status_code);
      chartColor = '#10b981';
      chartLabel = 'Código de Estado Garmin (7=Productivo, 5=Pico)';

    }} else if (kpiType === 'vo2') {{
      badgeEl.textContent = 'Consumo Máximo O₂';
      badgeEl.style.color = '#38bdf8';
      titleEl.textContent = 'VO₂ Máx (Potencia Aeróbica Pico)';
      descEl.textContent = 'Indica el volumen máximo de oxígeno que tu sistema cardiovascular puede captar y tus músculos pueden aprovechar por minuto. Es el techo biológico de velocidad para carreras de resistencia.';
      formulaEl.textContent = 'Medición submáxima continua de Firstbeat Analytics basada en la relación entre Ritmo de Carrera y Frecuencia Cardíaca.';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:25%; background:#ef4444;" title="Bajo (<42)"></div>
        <div class="spectrum-segment" style="width:25%; background:#f59e0b;" title="Bueno (42-48)"></div>
        <div class="spectrum-segment" style="width:25%; background:#10b981;" title="Excelente (49-52)"></div>
        <div class="spectrum-segment" style="width:25%; background:#38bdf8;" title="Superior (>52)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 42 (Bajo)</span>
        <span>42 - 48 (Bueno)</span>
        <span>49 - 52 (Excelente)</span>
        <span>> 52 (Superior)</span>
      `;
      currentEl.innerHTML = `
        <span>Tu valor actual: <strong>${{USER_VO2}} ml/kg/min</strong></span>
        <span style="color:#38bdf8; font-weight:700;">● Rango: Superior (Percentil > 90)</span>
      `;

      chartLabels = PMC_DATA.slice(-30).map(d => d.date_arg.slice(0, 5));
      chartData = PMC_DATA.slice(-30).map(() => USER_VO2);
      chartColor = '#38bdf8';
      chartLabel = 'VO₂ Máx (ml/kg/min)';

    }} else if (kpiType === 'endurance') {{
      badgeEl.textContent = 'Resistencia Integral';
      badgeEl.style.color = '#38bdf8';
      titleEl.textContent = 'Endurance (Puntuación de Resistencia)';
      descEl.textContent = 'Mide la capacidad de tu organismo para sostener el esfuerzo sin colapso biomecánico ni metabólico. Combina tu techo aeróbico con tu carga crónica y las horas invertidas en Zona 2.';
      formulaEl.textContent = 'Score = (VO₂ × 45.0) + (min(CTL, 600) × 3.5) + (Horas_Z2_4Sem × 25.0)';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:25%; background:#94a3b8;" title="Recreativo (< 3.500)"></div>
        <div class="spectrum-segment" style="width:25%; background:#f59e0b;" title="Intermedio (3.500 - 4.100)"></div>
        <div class="spectrum-segment" style="width:25%; background:#10b981;" title="Avanzado / Entrenado (4.100 - 4.700)"></div>
        <div class="spectrum-segment" style="width:25%; background:#38bdf8;" title="Élite (> 4.700)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 3.500</span>
        <span>3.500 - 4.100</span>
        <span>4.100 - 4.700</span>
        <span>> 4.700 (Élite)</span>
      `;
      currentEl.innerHTML = `
        <span>Tu valor actual: <strong>${{ENDURANCE_INFO.score}} puntos</strong></span>
        <span style="color:#10b981; font-weight:700;">● Nivel: ${{ENDURANCE_INFO.classification}}</span>
      `;
      
      chartLabels = PMC_DATA.slice(-30).map(d => d.date_arg.slice(0, 5));
      chartData = PMC_DATA.slice(-30).map(d => d.endurance_score);
      chartColor = '#38bdf8';
      chartLabel = 'Endurance Histórico';

    }} else if (kpiType === 'acwr') {{
      badgeEl.textContent = 'Control de Carga';
      badgeEl.style.color = '#f59e0b';
      titleEl.textContent = 'Ratio ACWR (Relación Carga Aguda vs. Crónica)';
      descEl.textContent = 'Evalúa si el incremento de estrés de la última semana (fatiga aguda) se construyó sobre una base sólida del último mes (fitness crónico) para prevenir sobreentrenamiento y lesiones por sobreuso.';
      formulaEl.textContent = 'ACWR = Fatiga Aguda (EWMA λ=0.25 / 7d) / Fitness Crónico (EWMA λ=0.069 / 28d)';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:20%; background:#94a3b8;" title="Desentrenamiento (< 0.80)"></div>
        <div class="spectrum-segment" style="width:35%; background:#10b981;" title="Sweet Spot Óptimo (0.80 - 1.30)"></div>
        <div class="spectrum-segment" style="width:25%; background:#f59e0b;" title="Sobrecarga / Alerta (1.30 - 1.50)"></div>
        <div class="spectrum-segment" style="width:20%; background:#ef4444;" title="Zona de Peligro (> 1.50)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 0.80 (Bajo)</span>
        <span>0.80 - 1.30 (Sweet Spot)</span>
        <span>1.30 - 1.50 (Alerta)</span>
        <span>> 1.50 (Riesgo)</span>
      `;
      const currentAcwr = PMC_DATA[PMC_DATA.length - 1].acwr;
      currentEl.innerHTML = `
        <span>Tu ratio actual: <strong>${{currentAcwr}}</strong></span>
        <span style="color:${{currentAcwr <= 1.30 ? '#10b981' : '#f59e0b'}}; font-weight:700;">● ${{currentAcwr <= 1.30 ? 'Dentro del Sweet Spot' : 'Zona de Sobrecarga'}}</span>
      `;
      
      chartLabels = PMC_DATA.slice(-30).map(d => d.date_arg.slice(0, 5));
      chartData = PMC_DATA.slice(-30).map(d => d.acwr);
      chartColor = '#f59e0b';
      chartLabel = 'Ratio ACWR';

    }} else if (kpiType === 'z2') {{
      badgeEl.textContent = 'Fisiología Mitocondrial';
      badgeEl.style.color = '#10b981';
      titleEl.textContent = 'Volumen en Zona 2 Aeróbica (142 - 158 ppm)';
      descEl.textContent = 'Mide las horas invertidas en la zona de máxima oxidación lipídica (FatMax) y aclaramiento de lactato por transportadores MCT-1. Es la base obligatoria para rendir sin desfallecer en 10K, 21K y Maratón.';
      formulaEl.textContent = 'Tiempo acumulado con Frecuencia Cardíaca entre 142 y 158 ppm en las últimas 4 semanas.';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:25%; background:#ef4444;" title="Insuficiente (< 8 h)"></div>
        <div class="spectrum-segment" style="width:25%; background:#f59e0b;" title="Mantenimiento (8 - 12 h)"></div>
        <div class="spectrum-segment" style="width:30%; background:#10b981;" title="Óptimo (12 - 18 h)"></div>
        <div class="spectrum-segment" style="width:20%; background:#38bdf8;" title="Alto Volumen (> 18 h)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 8 h (Bajo)</span>
        <span>8 - 12 h</span>
        <span>12 - 18 h (Óptimo)</span>
        <span>> 18 h (Élite)</span>
      `;
      currentEl.innerHTML = `
        <span>Horas en las últimas 4 semanas: <strong>${{ENDURANCE_INFO.z2_hours_4w}} h</strong></span>
        <span style="color:#10b981; font-weight:700;">● Rango Óptimo (79% de polarización)</span>
      `;
      
      const slice12 = getCurrent12WeeksSlice();
      chartLabels = slice12.map(w => w.label);
      chartData = slice12.map(w => w.z2_hours);
      chartColor = '#10b981';
      chartLabel = 'Horas Semanales en Z2';

    }} else if (kpiType === 'hrv') {{
      badgeEl.textContent = 'Tono Vagal Parasimpático';
      badgeEl.style.color = '#a855f7';
      titleEl.textContent = 'Variabilidad de FC Nocturna (RMSSD)';
      descEl.textContent = 'Mide las fluctuaciones entre latidos sucesivos durante el descanso nocturno. Una VFC en pasillo basal indica asimilación del estrés; caídas abruptas alertan sobre fatiga sistémica o enfermedad inminente.';
      formulaEl.textContent = 'RMSSD en milisegundos = √( (1/N) × Σ (RR_(i+1) - RR_i)² )';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:25%; background:#ef4444;" title="Deprimido (< 38 ms)"></div>
        <div class="spectrum-segment" style="width:20%; background:#f59e0b;" title="Bajo (38 - 42 ms)"></div>
        <div class="spectrum-segment" style="width:35%; background:#10b981;" title="Pasillo Equilibrado (43 - 56 ms)"></div>
        <div class="spectrum-segment" style="width:20%; background:#38bdf8;" title="Elevado / Parasimpático (> 56 ms)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 38 ms (Alerta)</span>
        <span>38 - 42 ms</span>
        <span>43 - 56 ms (Basal)</span>
        <span>> 56 ms</span>
      `;
      const currentHrv = RECOVERY_DATA[RECOVERY_DATA.length - 1].hrv || 42;
      currentEl.innerHTML = `
        <span>Valor actual: <strong>${{currentHrv}} ms</strong></span>
        <span style="color:${{currentHrv >= 43 ? '#10b981' : '#f59e0b'}}; font-weight:700;">● ${{currentHrv >= 43 ? 'En Pasillo Basal' : 'En Límite Inferior'}}</span>
      `;
      
      chartLabels = RECOVERY_DATA.slice(-28).map(d => d.date_arg.slice(0, 5));
      chartData = RECOVERY_DATA.slice(-28).map(d => d.hrv || 44);
      chartColor = '#a855f7';
      chartLabel = 'VFC Nocturna (ms)';

    }} else if (kpiType === 'sleep') {{
      badgeEl.textContent = 'Recuperación Integral';
      badgeEl.style.color = '#38bdf8';
      titleEl.textContent = 'Monitor de Sueño & Pasos Diarios';
      descEl.textContent = 'Evalúa la regeneración del sistema nervioso central mediante el sueño nocturno, complementado con el movimiento no programado (pasos diarios) que favorece el aclaramiento metabólico pasivo.';
      formulaEl.textContent = 'Puntuación de sueño Garmin Firstbeat (0-100) + Pasos registrados por acelerómetro.';
      
      trackEl.innerHTML = `
        <div class="spectrum-segment" style="width:25%; background:#ef4444;" title="Malo (< 60)"></div>
        <div class="spectrum-segment" style="width:25%; background:#f59e0b;" title="Aceptable (60 - 79)"></div>
        <div class="spectrum-segment" style="width:30%; background:#10b981;" title="Bueno (80 - 89)"></div>
        <div class="spectrum-segment" style="width:20%; background:#38bdf8;" title="Excelente (90 - 100)"></div>
      `;
      legendEl.innerHTML = `
        <span>< 60 (Deficiente)</span>
        <span>60 - 79 (Aceptable)</span>
        <span>80 - 89 (Bueno)</span>
        <span>90 - 100 (Excelente)</span>
      `;
      const lastSleep = RECOVERY_DATA[RECOVERY_DATA.length - 1].sleep_score || 68;
      currentEl.innerHTML = `
        <span>Score de Sueño: <strong>${{lastSleep}}/100</strong> (${{RECOVERY_DATA[RECOVERY_DATA.length - 1].sleep_hours || 6.8}}h)</span>
        <span style="color:${{lastSleep >= 80 ? '#10b981' : '#f59e0b'}}; font-weight:700;">● ${{lastSleep >= 80 ? 'Descanso Óptimo' : 'Descanso Aceptable'}}</span>
      `;
      
      chartLabels = RECOVERY_DATA.slice(-14).map(d => d.date_arg.slice(0, 5));
      chartData = RECOVERY_DATA.slice(-14).map(d => d.sleep_score || 72);
      chartColor = '#38bdf8';
      chartLabel = 'Puntuación de Sueño';
      kpiThemeBg = 'var(--pastel-blue-bg)';
      kpiThemeText = 'var(--pastel-blue-text)';
      kpiThemeBorder = 'var(--pastel-blue-border)';
    }}

    badgeEl.style.background = kpiThemeBg;
    badgeEl.style.color = kpiThemeText;
    badgeEl.style.border = '1px solid ' + kpiThemeBorder;

    const modalBox = modal.querySelector('.modal-box');
    if (modalBox) {{
      modalBox.style.borderTop = '5px solid ' + chartColor;
      modalBox.style.boxShadow = `0 12px 32px -4px rgba(15, 23, 42, 0.1), 0 0 20px -2px ${{chartColor}}25`;
    }}

    const ctx = document.getElementById('kpiModalChart').getContext('2d');
    if (kpiChart) kpiChart.destroy();
    kpiChart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: chartLabels,
        datasets: [{{
          label: chartLabel,
          data: chartData,
          borderColor: chartColor,
          backgroundColor: chartColor + '20',
          fill: true,
          tension: 0.25,
          pointRadius: 2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }} }}
        }}
      }}
    }});

    modal.classList.add('active');
  }}

  function closeKpiModal(e) {{
    document.getElementById('kpi-modal').classList.remove('active');
  }}

  function closeKpiModalDirect() {{
    document.getElementById('kpi-modal').classList.remove('active');
  }}

  // Renderizado de tabla de actividades
  function renderTable() {{
    const tbody = document.getElementById('table-raw-body');
    tbody.innerHTML = '';
    ACTIVITIES.slice(0, 50).forEach((a, index) => {{
      const tr = document.createElement('tr');
      tr.className = 'clickable-row';
      tr.onclick = () => openActivityModal(index);

      let sportBadge = 'badge-run';
      if (a.sport === 'Gimnasio / Fuerza') sportBadge = 'badge-gym';
      else if (a.sport === 'Caminata') sportBadge = 'badge-walk';

      const z2Tag = a.z2_pct >= 70 ? '<span class="badge badge-z2-pure">' + a.z2_pct + '%</span>' : 
                   (a.z2_pct > 0 ? '<span class="badge badge-z2-drift">' + a.z2_pct + '%</span>' : '<span style="color:var(--text-muted);">-</span>');

      tr.innerHTML = `
        <td style="font-family:'JetBrains Mono'; font-size:12px;"><strong>${{a.date_arg}}</strong></td>
        <td><strong>${{a.name}}</strong></td>
        <td><span class="badge ${{sportBadge}}">${{a.sport}}</span></td>
        <td>${{a.intensity}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.distance_km > 0 ? a.distance_km + ' km' : '-'}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.duration_min}} min</td>
        <td style="font-family:'JetBrains Mono';">${{a.avg_hr > 0 ? a.avg_hr + ' / ' + a.max_hr + ' ppm' : '-'}}</td>
        <td style="font-family:'JetBrains Mono';">${{a.load}}</td>
        <td>${{z2Tag}}</td>
        <td><button class="btn-action" style="padding:4px 8px; font-size:11px;" onclick="event.stopPropagation(); openActivityModal(${{index}})">Ver Zonas</button></td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  function openActivityModal(index) {{
    const a = ACTIVITIES[index];
    if (!a) return;

    document.getElementById('modal-title').textContent = a.name;
    document.getElementById('modal-date').textContent = `${{a.date_arg}} ${{a.time_part || ''}}`;
    document.getElementById('modal-sport-badge').textContent = a.sport;
    document.getElementById('modal-dist').textContent = a.distance_km > 0 ? `${{a.distance_km}} km` : '-';
    document.getElementById('modal-dur').textContent = `${{a.duration_min}} min`;
    document.getElementById('modal-pace').textContent = a.pace_str;
    document.getElementById('modal-hr').textContent = a.avg_hr > 0 ? `${{a.avg_hr}} / ${{a.max_hr}} ppm` : '-';
    document.getElementById('modal-load').textContent = a.load;

    const totalSec = (a.z1_sec + a.z2_sec + a.z3_sec + a.z4_sec + a.z5_sec) || a.duration_sec || 1;
    const p1 = Math.round((a.z1_sec / totalSec) * 100);
    const p2 = Math.round((a.z2_sec / totalSec) * 100);
    const p3 = Math.round((a.z3_sec / totalSec) * 100);
    const p4 = Math.round((a.z4_sec / totalSec) * 100);
    const p5 = Math.round((a.z5_sec / totalSec) * 100);

    document.getElementById('bar-z1').style.width = p1 + '%';
    document.getElementById('bar-z2').style.width = p2 + '%';
    document.getElementById('bar-z3').style.width = p3 + '%';
    document.getElementById('bar-z4').style.width = p4 + '%';
    document.getElementById('bar-z5').style.width = p5 + '%';

    document.getElementById('val-z1').textContent = `${{a.z1_min}} min (${{p1}}%)`;
    document.getElementById('val-z2').textContent = `${{a.z2_min}} min (${{p2}}%)`;
    document.getElementById('val-z3').textContent = `${{a.z3_min}} min (${{p3}}%)`;
    document.getElementById('val-z4').textContent = `${{a.z4_min}} min (${{p4}}%)`;
    document.getElementById('val-z5').textContent = `${{a.z5_min}} min (${{p5}}%)`;

    const ctx = document.getElementById('modalZoneChart').getContext('2d');
    if (modalChart) modalChart.destroy();
    modalChart = new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: ['Z1 Recup.', 'Z2 Base', 'Z3 Tempo', 'Z4 Umbral', 'Z5 Anaerób.'],
        datasets: [{{
          label: 'Minutos en Zona',
          data: [a.z1_min, a.z2_min, a.z3_min, a.z4_min, a.z5_min],
          backgroundColor: ['#94a3b8', '#10b981', '#38bdf8', '#f59e0b', '#f43f5e'],
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }}, crosshair: false }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94a3b8', callback: v => v + ' m' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});

    document.getElementById('activity-modal').classList.add('active');
  }}

  function closeActivityModal(e) {{
    document.getElementById('activity-modal').classList.remove('active');
  }}

  function closeModalDirect() {{
    document.getElementById('activity-modal').classList.remove('active');
  }}

  // Inicialización de Gráficos Principales
  function initCharts() {{
    // 1. Curva PMC
    const ctxPMC = document.getElementById('chartPMC').getContext('2d');
    charts.pmc = new Chart(ctxPMC, {{
      type: 'line',
      data: {{
        labels: PMC_DATA.map(d => d.date_arg.slice(0, 5)),
        datasets: [
          {{ label: 'Fitness (CTL 42d)', data: PMC_DATA.map(d => d.ctl), borderColor: '#0284c7', tension: 0.25, pointRadius: 0 }},
          {{ label: 'Fatiga (ATL 7d)', data: PMC_DATA.map(d => d.atl), borderColor: '#f59e0b', tension: 0.25, pointRadius: 0 }},
          {{ label: 'Forma (TSB)', data: PMC_DATA.map(d => d.tsb), borderColor: '#10b981', borderDash: [4, 4], pointRadius: 0 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ labels: {{ color: '#475569', font: {{ family: "'Plus Jakarta Sans', sans-serif", weight: 600 }} }} }},
          tooltip: {{
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            titleColor: '#0f172a',
            bodyColor: '#334155',
            padding: 12,
            cornerRadius: 12,
            titleFont: {{ family: "'Plus Jakarta Sans', sans-serif", weight: 700 }},
            bodyFont: {{ family: "'JetBrains Mono', monospace" }}
          }}
        }},
        scales: {{
          y: {{ 
            grid: {{ color: 'rgba(148, 163, 184, 0.12)', borderDash: [3, 3], drawBorder: false }}, 
            ticks: {{ color: '#94a3b8' }},
            border: {{ display: false }}
          }},
          x: {{ 
            grid: {{ display: false }}, 
            ticks: {{ color: '#94a3b8', maxTicksLimit: 12 }},
            border: {{ display: false }}
          }}
        }}
      }}
    }});

    // 2. Multideporte Doughnut (Sin Crosshair)
    const sportsMinutes = {{ 'Carrera': 0, 'Gimnasio / Fuerza': 0, 'Caminata': 0, 'HIIT / Cardio': 0 }};
    let totalMinutes = 0;
    ACTIVITIES.forEach(a => {{
      if (sportsMinutes[a.sport] !== undefined) sportsMinutes[a.sport] += a.duration_min;
      else sportsMinutes['Carrera'] += a.duration_min;
      totalMinutes += a.duration_min;
    }});

    const ctxSports = document.getElementById('chartSportsSplit').getContext('2d');
    charts.sports = new Chart(ctxSports, {{
      type: 'doughnut',
      data: {{
        labels: ['Carrera', 'Gimnasio / Fuerza', 'Caminata', 'HIIT / Cardio'],
        datasets: [{{
          data: Object.values(sportsMinutes),
          backgroundColor: ['#38bdf8', '#a855f7', '#10b981', '#f59e0b'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          crosshair: false,
          legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const mins = context.raw;
                const hours = Math.floor(mins / 60);
                const remainMins = Math.round(mins % 60);
                const pct = totalMinutes > 0 ? Math.round((mins / totalMinutes) * 100) : 0;
                return `${{context.label}}: ${{hours}}h ${{remainMins}}m (${{pct}}% del volumen)`;
              }}
            }}
          }}
        }}
      }}
    }});

    // 3. Weekly Sports Bar (Sin Crosshair)
    const ctxWeeklySports = document.getElementById('chartWeeklySports').getContext('2d');
    charts.weeklySports = new Chart(ctxWeeklySports, {{
      type: 'bar',
      data: {{
        labels: ['Sem 38', 'Sem 39', 'Sem 40', 'Sem 41 (Esta)'],
        datasets: [
          {{ label: 'Carrera (horas)', data: [4.2, 5.1, 4.8, 3.5], backgroundColor: '#38bdf8' }},
          {{ label: 'Gimnasio / Fuerza (horas)', data: [2.0, 2.5, 2.0, 1.5], backgroundColor: '#a855f7' }},
          {{ label: 'Caminata (horas)', data: [1.5, 2.0, 1.8, 1.2], backgroundColor: '#10b981' }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ crosshair: false, legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
          x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }},
          y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94a3b8', callback: v => v + ' h' }} }}
        }}
      }}
    }});

    // 4. (Zona 2 se inicializa en initStravaZ2Chart con motor Strava interactivo)

    // 5. Polarización 80/20 (Sin Crosshair)
    const ctxPol = document.getElementById('chartPolarization').getContext('2d');
    charts.polarization = new Chart(ctxPol, {{
      type: 'doughnut',
      data: {{
        labels: ['Zona 1-2 (Base Aeróbica)', 'Zona 3 (Tempo)', 'Zona 4-5 (Alta Intensidad)'],
        datasets: [{{
          data: [79, 14, 7],
          backgroundColor: ['#10b981', '#f59e0b', '#f43f5e'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          crosshair: false,
          legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }},
          tooltip: {{
            callbacks: {{
              label: ctx => `${{ctx.label}}: ${{ctx.raw}}% del entrenamiento`
            }}
          }}
        }}
      }}
    }});

    // 6. HRV Base con Crosshair Vertical
    const ctxHRV = document.getElementById('chartHRVBase').getContext('2d');
    const validHRV = RECOVERY_DATA.filter(d => d.hrv);
    charts.hrv = new Chart(ctxHRV, {{
      type: 'line',
      data: {{
        labels: validHRV.map(d => d.date_arg.slice(0, 5)),
        datasets: [
          {{ label: 'VFC Nocturna (ms)', data: validHRV.map(d => d.hrv), borderColor: '#10b981', tension: 0.25 }},
          {{ label: 'Límite Superior (56 ms)', data: validHRV.map(() => 56), borderColor: 'rgba(255,255,255,0.2)', borderDash: [4, 4], pointRadius: 0 }},
          {{ label: 'Límite Inferior (43 ms)', data: validHRV.map(() => 43), borderColor: 'rgba(255,255,255,0.2)', borderDash: [4, 4], pointRadius: 0 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
          y: {{ min: 35, max: 65, grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94a3b8', callback: v => v + ' ms' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }} }}
        }}
      }}
    }});

    // 7. Sueño Puro: Horas y Score (Sin pasos mezclados)
    const ctxSleepSteps = document.getElementById('chartSleepSteps').getContext('2d');
    const recentRec = RECOVERY_DATA.slice(-21);
    charts.sleepSteps = new Chart(ctxSleepSteps, {{
      type: 'bar',
      data: {{
        labels: recentRec.map(d => d.date_arg.slice(0, 5)),
        datasets: [
          {{
            type: 'line',
            label: 'Horas de Sueño',
            data: recentRec.map(d => d.sleep_hours || 7.0),
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            tension: 0.25,
            yAxisID: 'ySleep',
            pointRadius: 3
          }},
          {{
            type: 'bar',
            label: 'Puntaje de Sueño (Score /100)',
            data: recentRec.map(d => d.sleep_score || 75),
            backgroundColor: 'rgba(96, 165, 250, 0.45)',
            borderRadius: 4,
            yAxisID: 'yScore'
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
          ySleep: {{
            type: 'linear',
            position: 'left',
            min: 4,
            max: 10,
            grid: {{ color: 'rgba(255,255,255,0.06)' }},
            ticks: {{ color: '#38bdf8', callback: v => v + ' h' }}
          }},
          yScore: {{
            type: 'linear',
            position: 'right',
            min: 40,
            max: 100,
            grid: {{ display: false }},
            ticks: {{ color: '#60a5fa', callback: v => v + ' pts' }}
          }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }} }}
        }}
      }}
    }});

    // 8. RHR Trend
    const ctxRHR = document.getElementById('chartRHRTrend').getContext('2d');
    const validRHR = RECOVERY_DATA.filter(d => d.rhr);
    charts.rhr = new Chart(ctxRHR, {{
      type: 'line',
      data: {{
        labels: validRHR.map(d => d.date_arg.slice(0, 5)),
        datasets: [{{
          label: 'FC en Reposo (ppm)',
          data: validRHR.map(d => d.rhr),
          borderColor: '#f43f5e',
          tension: 0.25,
          fill: true,
          backgroundColor: 'rgba(244, 63, 94, 0.08)'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 46, max: 62, grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94a3b8', callback: v => v + ' ppm' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8', maxTicksLimit: 14 }} }}
        }}
      }}
    }});

    // 9. Gráfico Oficial Garmin Firstbeat: Carga Aguda Diaria con Banda Verde de Túnel (Imagen 5)
    initGarminAcuteTunnelChart();

    // 10. Gráfico Evolutivo de Predicciones Oficiales de Carrera (Imagen 1)
    initRacePredictionEvolutionChart();

    // 11. Renderizado de Heatmap de Consistencia y Racha (Imagen 4)
    renderConsistencyHeatmap();
  }}

  // =========================================================================
  // FUNCIONES V4.2: GRÁFICO OFICIAL DE CARGA AGUDA GARMIN CON TÚNEL VERDE
  // =========================================================================
  let currentAcuteFilter = '3M';
  function initGarminAcuteTunnelChart() {{
    const ctx = document.getElementById('chartGarminAcuteTunnel')?.getContext('2d');
    if (!ctx) return;

    let sliceData = PMC_DATA;
    if (currentAcuteFilter === 'today') sliceData = PMC_DATA.slice(-7);
    else if (currentAcuteFilter === '1M') sliceData = PMC_DATA.slice(-30);
    else if (currentAcuteFilter === '3M') sliceData = PMC_DATA.slice(-90);
    else if (currentAcuteFilter === '6M') sliceData = PMC_DATA.slice(-180);

    const labels = sliceData.map(d => d.date_arg.slice(0, 5));
    const acuteLoads = sliceData.map(d => d.atl);
    const minTunnels = sliceData.map(d => d.min_tunnel || 404);
    const maxTunnels = sliceData.map(d => d.max_tunnel || 758);

    if (charts.acuteTunnel) charts.acuteTunnel.destroy();
    charts.acuteTunnel = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{
            label: 'Túnel Máximo Óptimo',
            data: maxTunnels,
            borderColor: 'rgba(16, 185, 129, 0.45)',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            tension: 0.3
          }},
          {{
            label: 'Túnel Mínimo Óptimo (Banda Verde)',
            data: minTunnels,
            borderColor: 'rgba(16, 185, 129, 0.45)',
            borderWidth: 1,
            pointRadius: 0,
            backgroundColor: 'rgba(16, 185, 129, 0.22)',
            fill: '-1', // Rellena el espacio hacia el dataset 0 creando la franja verde continua
            tension: 0.3
          }},
          {{
            label: 'Carga Aguda Diaria',
            data: acuteLoads,
            borderColor: '#ffffff',
            borderWidth: 2.5,
            pointRadius: (ctxPt) => ctxPt.dataIndex === acuteLoads.length - 1 ? 6 : 2.5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#0f172a',
            pointBorderWidth: 1.5,
            fill: false,
            tension: 0.25
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            titleColor: '#ffffff',
            bodyColor: '#e2e8f0',
            borderColor: '#334155',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 10,
            callbacks: {{
              label: (ctxT) => {{
                if (ctxT.datasetIndex === 2) return `Carga Aguda: ${{ctxT.raw}} pts`;
                if (ctxT.datasetIndex === 1) return `Túnel Mínimo: ${{ctxT.raw}} pts`;
                if (ctxT.datasetIndex === 0) return `Túnel Máximo: ${{ctxT.raw}} pts`;
                return `${{ctxT.dataset.label}}: ${{ctxT.raw}}`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            grid: {{ color: 'rgba(255, 255, 255, 0.08)', drawBorder: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono'" }}, callback: v => v + ' pts' }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono'" }}, maxTicksLimit: 12 }}
          }}
        }}
      }}
    }});
  }}

  function filterAcuteChart(period) {{
    currentAcuteFilter = period;
    const ctrl = document.getElementById('control-timeline-acute');
    if (ctrl) {{
      ctrl.querySelectorAll('.segmented-pill-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = Array.from(ctrl.querySelectorAll('.segmented-pill-btn')).find(b => b.textContent.trim().toLowerCase() === period.toLowerCase());
      if (activeBtn) activeBtn.classList.add('active');
    }}
    initGarminAcuteTunnelChart();
  }}

  // =========================================================================
  // FUNCIONES V4.2: GRÁFICO HISTÓRICO DE PREDICCIONES CON NODOS Y HALO AZUL
  // =========================================================================
  let currentPredDistance = '5k';
  let currentPredPeriod = '3M';

  function initRacePredictionEvolutionChart() {{
    const ctx = document.getElementById('chartRacePredictionEvolution')?.getContext('2d');
    if (!ctx) return;

    if (!RACE_PRED_HISTORY || RACE_PRED_HISTORY.length === 0) {{
      return;
    }}

    let sliceData = RACE_PRED_HISTORY;
    if (currentPredPeriod === 'today') sliceData = RACE_PRED_HISTORY.slice(-7);
    else if (currentPredPeriod === '1M') sliceData = RACE_PRED_HISTORY.slice(-30);
    else if (currentPredPeriod === '3M') sliceData = RACE_PRED_HISTORY.slice(-90);
    else if (currentPredPeriod === '6M') sliceData = RACE_PRED_HISTORY.slice(-180);

    const labels = sliceData.map(d => d.date_arg);
    const rawSeconds = sliceData.map(d => {{
      if (currentPredDistance === '5k') return d.time5K;
      if (currentPredDistance === '10k') return d.time10K;
      if (currentPredDistance === '21k') return d.timeHalfMarathon;
      return d.timeMarathon;
    }});

    const lastIdx = rawSeconds.length - 1;
    const latestSec = rawSeconds[lastIdx];
    
    // Formatear texto en cabecera
    const fmtTime = (s) => {{
      if (s >= 3600) {{
        const h = Math.floor(s / 3600);
        const rem = s % 3600;
        const m = Math.floor(rem / 60);
        const sec = rem % 60;
        return `${{h}}:${{m < 10 ? '0' : ''}}${{m}}:${{sec < 10 ? '0' : ''}}${{sec}}`;
      }}
      const m = Math.floor(s / 60);
      const sec = s % 60;
      return `${{m}}:${{sec < 10 ? '0' : ''}}${{sec}}`;
    }};

    const curTimeEl = document.getElementById('pred-chart-current-time');
    if (curTimeEl) curTimeEl.textContent = fmtTime(latestSec);

    const grad = ctx.createLinearGradient(0, 0, 0, 240);
    grad.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
    grad.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

    if (charts.predEvol) charts.predEvol.destroy();
    charts.predEvol = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: `Predicción ${{currentPredDistance.toUpperCase()}}`,
          data: rawSeconds,
          borderColor: '#3b82f6',
          backgroundColor: grad,
          fill: true,
          tension: 0.25,
          borderWidth: 2.5,
          pointRadius: (ctxPt) => ctxPt.dataIndex === lastIdx ? 7 : 3,
          pointBackgroundColor: (ctxPt) => ctxPt.dataIndex === lastIdx ? '#3b82f6' : '#ffffff',
          pointBorderColor: (ctxPt) => ctxPt.dataIndex === lastIdx ? '#ffffff' : '#3b82f6',
          pointBorderWidth: 2,
          pointHoverRadius: 8
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#ffffff',
            titleColor: '#0f172a',
            bodyColor: '#334155',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 10,
            callbacks: {{
              label: (ctxT) => `Tiempo Estimado: ${{fmtTime(ctxT.raw)}}`
            }}
          }}
        }},
        scales: {{
          y: {{
            grid: {{ color: 'rgba(148, 163, 184, 0.12)', borderDash: [3, 3] }},
            ticks: {{
              color: '#94a3b8',
              font: {{ family: "'JetBrains Mono'" }},
              callback: v => fmtTime(v)
            }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono'" }}, maxTicksLimit: 10 }}
          }}
        }}
      }}
    }});
  }}

  function selectPredictionDistance(distKey) {{
    currentPredDistance = distKey;
    document.querySelectorAll('.pred-card').forEach(c => c.classList.remove('active'));
    const targetCard = document.getElementById(`pred-card-${{distKey}}`);
    if (targetCard) targetCard.classList.add('active');

    const distTitles = {{ '5k': '5 Kilómetros', '10k': '10 Kilómetros', '21k': 'Medio Maratón (21.1k)', '42k': 'Maratón (42.2k)' }};
    const titleEl = document.getElementById('pred-chart-title');
    if (titleEl) titleEl.textContent = `Evolución de Predicción: ${{distTitles[distKey]}}`;

    initRacePredictionEvolutionChart();
  }}

  function filterPredChart(period) {{
    currentPredPeriod = period;
    const ctrl = document.getElementById('control-timeline-pred');
    if (ctrl) {{
      ctrl.querySelectorAll('.segmented-pill-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = Array.from(ctrl.querySelectorAll('.segmented-pill-btn')).find(b => b.textContent.trim().toLowerCase() === period.toLowerCase());
      if (activeBtn) activeBtn.classList.add('active');
    }}
    initRacePredictionEvolutionChart();
  }}

  // =========================================================================
  // FUNCIONES V4.2: RENDERIZADO DEL HEATMAP DE CONSISTENCIA DE STRAVA
  // =========================================================================
  function renderConsistencyHeatmap() {{
    const grid = document.getElementById('consistency-heatmap-grid');
    if (!grid || !CONSISTENCY_WEEKS || CONSISTENCY_WEEKS.length === 0) return;

    grid.innerHTML = '';
    CONSISTENCY_WEEKS.forEach(week => {{
      week.forEach(day => {{
        const cell = document.createElement('div');
        cell.className = `heatmap-cell lvl-${{day.level >= 0 ? day.level : 0}} ${{day.is_today ? 'is-today' : ''}}`;
        if (day.level === -1) cell.style.opacity = '0.2';
        
        const titleText = `${{day.day_name}} ${{day.date_arg}}: ${{day.minutes > 0 ? day.minutes + ' min (' + day.sports + ')' : 'Sin entrenamiento registrado'}}`;
        cell.title = titleText;
        grid.appendChild(cell);
      }});
    }});
  }}

  // Función de Búsqueda Reactiva en Tiempo Real del Glosario
  function filterGlossary(query) {{
    const q = (query || '').toLowerCase().trim();
    const cards = document.querySelectorAll('#glossary-items-container .info-card');
    cards.forEach(card => {{
      const termData = (card.getAttribute('data-term') || '').toLowerCase();
      const textContent = card.innerText.toLowerCase();
      if (!q || termData.includes(q) || textContent.includes(q)) {{
        card.style.display = 'block';
      }} else {{
        card.style.display = 'none';
      }}
    }});
  }}

  // ==========================================
  // NAVEGADOR TEMPORAL ZONA 2 (MOTOR STRAVA ESMERALDA)
  // ==========================================
  let windowEndIdxZ2 = FULL_TIMELINE_WEEKS.length;

  function getCurrent12WeeksSliceZ2() {{
    const start = Math.max(0, windowEndIdxZ2 - 12);
    return FULL_TIMELINE_WEEKS.slice(start, windowEndIdxZ2);
  }}

  function initStravaZ2Chart() {{
    const ctx = document.getElementById('chartZ2Dynamic').getContext('2d');
    const currentSlice = getCurrent12WeeksSliceZ2();

    const gradient = ctx.createLinearGradient(0, 0, 0, 220);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.45)');
    gradient.addColorStop(0.7, 'rgba(16, 185, 129, 0.12)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.00)');

    const labels = currentSlice.map(w => w.month + ' ' + w.label);
    const dataVals = currentSlice.map(w => w.z2_hours);

    const pointRadii = currentSlice.map(w => w.is_current ? 7 : 4);
    const pointBgColors = currentSlice.map(w => w.is_current ? '#10b981' : '#07090e');
    const pointBorderColors = currentSlice.map(w => w.is_current ? '#ffffff' : '#10b981');
    const pointBorderWidths = currentSlice.map(w => w.is_current ? 3 : 2);

    charts.z2 = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'Horas en Zona 2',
          data: dataVals,
          borderColor: '#10b981',
          borderWidth: 2.5,
          backgroundColor: gradient,
          fill: true,
          tension: 0.25,
          pointRadius: pointRadii,
          pointBackgroundColor: pointBgColors,
          pointBorderColor: pointBorderColors,
          pointBorderWidth: pointBorderWidths,
          pointHoverRadius: 8
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#0b111e',
            borderColor: '#334155',
            borderWidth: 1,
            titleColor: '#f1f5f9',
            bodyColor: '#cbd5e1',
            callbacks: {{
              title: ctx => {{
                const slice = getCurrent12WeeksSliceZ2();
                return 'Semana ' + slice[ctx[0].dataIndex].label + ' (' + slice[ctx[0].dataIndex].year + ')';
              }},
              label: ctx => {{
                const slice = getCurrent12WeeksSliceZ2();
                const item = slice[ctx.dataIndex];
                return `Base Aeróbica Z2: ${{item.z2_hours}} h (${{item.dist_km}} km totales)`;
              }}
            }}
          }}
        }},
        scales: {{
          y: {{
            min: 0,
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{
              color: '#94a3b8',
              callback: v => v + ' h',
              stepSize: 1
            }}
          }},
          x: {{
            grid: {{ display: false }},
            ticks: {{
              color: '#94a3b8',
              maxTicksLimit: 6,
              callback: function(val, index) {{
                const slice = getCurrent12WeeksSliceZ2();
                const w = slice[index];
                return (index % 4 === 0 || index === slice.length - 1) ? w.month : '';
              }}
            }}
          }}
        }}
      }}
    }});

    updateStravaZ2ChartWindow();
  }}

  function moveTimelineZ2(deltaWeeks) {{
    windowEndIdxZ2 = Math.min(FULL_TIMELINE_WEEKS.length, Math.max(12, windowEndIdxZ2 + deltaWeeks));
    updateStravaZ2ChartWindow();
    updateTimelineNavButtonsZ2();
  }}

  function resetTimelineZ2ToNow() {{
    windowEndIdxZ2 = FULL_TIMELINE_WEEKS.length;
    updateStravaZ2ChartWindow();
    updateTimelineNavButtonsZ2();
  }}

  function jumpToYearZ2(yearStr) {{
    const y = parseInt(yearStr);
    let targetIdx = -1;
    for (let i = FULL_TIMELINE_WEEKS.length - 1; i >= 0; i--) {{
      if (FULL_TIMELINE_WEEKS[i].year === y) {{
        targetIdx = i + 1;
        break;
      }}
    }}
    if (targetIdx !== -1) {{
      windowEndIdxZ2 = Math.max(12, targetIdx);
      updateStravaZ2ChartWindow();
      updateTimelineNavButtonsZ2();
    }}
  }}

  function updateTimelineNavButtonsZ2() {{
    const btnPrev = document.getElementById('btn-timeline-prev-z2');
    const btnNext = document.getElementById('btn-timeline-next-z2');
    if (btnPrev) btnPrev.disabled = (windowEndIdxZ2 <= 12);
    if (btnNext) btnNext.disabled = (windowEndIdxZ2 >= FULL_TIMELINE_WEEKS.length);
  }}

  function updateStravaZ2ChartWindow() {{
    if (!charts.z2) return;
    const currentSlice = getCurrent12WeeksSliceZ2();
    const isNow = (windowEndIdxZ2 >= FULL_TIMELINE_WEEKS.length);

    const datesEl = document.getElementById('z2-window-dates');
    if (datesEl) {{
      datesEl.textContent = `${{currentSlice[0].label}}/${{currentSlice[0].year}} ➔ ${{currentSlice[currentSlice.length - 1].label}}/${{currentSlice[currentSlice.length - 1].year}}`;
    }}

    const statWeekEl = document.getElementById('z2-stat-week');
    if (statWeekEl) {{
      statWeekEl.textContent = `${{currentSlice[currentSlice.length - 1].z2_hours}} h`;
    }}

    const ctx = document.getElementById('chartZ2Dynamic').getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, 220);
    grad.addColorStop(0, 'rgba(16, 185, 129, 0.45)');
    grad.addColorStop(0.7, 'rgba(16, 185, 129, 0.12)');
    grad.addColorStop(1, 'rgba(16, 185, 129, 0.00)');

    charts.z2.data.labels = currentSlice.map(w => w.month + ' ' + w.label);
    charts.z2.data.datasets[0].data = currentSlice.map(w => w.z2_hours);
    charts.z2.data.datasets[0].backgroundColor = grad;
    charts.z2.data.datasets[0].pointRadius = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? 7 : 4);
    charts.z2.data.datasets[0].pointBorderColor = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? '#ffffff' : '#10b981');
    charts.z2.data.datasets[0].pointBackgroundColor = currentSlice.map(w => (w.is_current || w === currentSlice[currentSlice.length - 1]) ? '#10b981' : '#07090e');
    charts.z2.update();
  }}
</script>

</body>
</html>
"""

print(f"Escribiendo panel interactivo V4.0 en: {OUTPUT_HTML}")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print("✓ Panel Versión 4.0 generado exitosamente.")
