from typing import Dict, Any, Optional

def calculate_power_specs(cpu: Optional[str], gpu: Optional[str], brand: Optional[str]) -> Dict[str, Any]:
    """
    Calculates estimated Peak TDP/TGP (Watts), Average Workload Power (Watts),
    Power Efficiency Tier, and Monthly Electricity Cost in Portugal (€/month).

    Economic Baseline:
    - Residential electricity tariff in Portugal (EDP/Galp average): ~€0.22 per kWh.
    - Daily developer usage: 8 hours/day * 30 days = 240 active hours/month.
    """
    cpu_l = (cpu or "").lower()
    gpu_l = (gpu or "").lower()
    brand_l = (brand or "").lower()

    # 1. CPU TDP (Thermal Design Power)
    if "apple" in brand_l or any(x in cpu_l for x in ["m1", "m2", "m3"]):
        cpu_tdp = 20  # Apple Silicon is extraordinarily power-efficient
    elif any(x in cpu_l for x in ["snapdragon", "arm"]):
        cpu_tdp = 15
    elif any(x in cpu_l for x in ["hx", "13900", "14900", "13800", "7945", "7845"]):
        cpu_tdp = 55  # Desktop replacement class
    elif any(x in cpu_l for x in ["h", "hs", "13700", "12700", "11800", "5800h", "6800h", "7735hs", "7840hs", "10300h", "9300h", "9750h"]):
        cpu_tdp = 45  # Standard performance mobile H/HS-series
    elif any(x in cpu_l for x in ["p", "1260p", "1360p", "1240p"]):
        cpu_tdp = 28  # Balanced P-series
    elif any(x in cpu_l for x in ["u", "1235u", "1245u", "5500u", "5700u", "5825u", "7520u", "8350u", "8250u", "8550u"]):
        cpu_tdp = 15  # Ultra-low voltage U-series (cool & quiet)
    else:
        cpu_tdp = 25  # Mainstream mobile CPU default

    # 2. GPU TGP (Total Graphics Power)
    is_dgpu = False
    if "rtx 4090" in gpu_l or "rtx 4080" in gpu_l:
        gpu_tgp = 140
        is_dgpu = True
    elif "rtx 4070" in gpu_l or "rtx 3080" in gpu_l:
        gpu_tgp = 115
        is_dgpu = True
    elif "rtx 4060" in gpu_l:
        gpu_tgp = 100  # Typical laptop 80W-115W TGP
        is_dgpu = True
    elif "rtx 4050" in gpu_l:
        gpu_tgp = 75   # Typical laptop 45W-95W
        is_dgpu = True
    elif "rtx 3060" in gpu_l:
        gpu_tgp = 95
        is_dgpu = True
    elif "rtx 3050" in gpu_l or "rtx 2060" in gpu_l:
        gpu_tgp = 60
        is_dgpu = True
    elif "gtx 1660" in gpu_l:
        gpu_tgp = 60
        is_dgpu = True
    elif "gtx 1650" in gpu_l or "gtx 1060" in gpu_l or "gtx 1050" in gpu_l:
        gpu_tgp = 50
        is_dgpu = True
    elif "pro 560" in gpu_l or "pro 555" in gpu_l or "rx " in gpu_l:
        gpu_tgp = 35
        is_dgpu = True
    elif "quadro" in gpu_l:
        gpu_tgp = 50
        is_dgpu = True
    else:
        # Integrated graphics (Intel Iris Xe, UHD 620, AMD Radeon 680M/780M, Vega)
        gpu_tgp = 0
        is_dgpu = False

    # 3. Base platform power (display panel backlight, NVMe SSD, DDR4/DDR5 RAM, fans, chipset)
    base_system_watts = 15

    # 4. Total Peak System Power (Watts under combined stress)
    peak_watts = cpu_tdp + gpu_tgp + base_system_watts

    # 5. Realistic Average Load Watts (Dev / VM / Docker / Web Browsing workload)
    if "apple" in brand_l:
        avg_watts = 18
    elif not is_dgpu:
        # Ultrabook / integrated graphics: CPU runs at ~10-20W average
        avg_watts = max(15, int(cpu_tdp * 0.6) + 10)
    else:
        # Gaming/workstation laptop: dGPU idles at ~5-10W during coding, bursts during acceleration
        avg_watts = max(35, int(cpu_tdp * 0.7) + int(gpu_tgp * 0.3) + 12)

    # 6. Power Efficiency Rating
    if peak_watts <= 45:
        efficiency_tier = "A+ Ultra-Efficient"
        efficiency_badge = "ultra_efficient"
    elif peak_watts <= 85:
        efficiency_tier = "A Balanced Efficiency"
        efficiency_badge = "balanced"
    elif peak_watts <= 130:
        efficiency_tier = "B Performance Power"
        efficiency_badge = "performance"
    else:
        efficiency_tier = "C High-Draw Rig"
        efficiency_badge = "high_draw"

    # 7. Estimated Monthly Cost in Portugal (at €0.22/kWh, 8h/day, 30 days = 240 hours)
    monthly_kwh = (avg_watts / 1000.0) * 240
    monthly_cost_eur = round(monthly_kwh * 0.22, 2)

    return {
        "cpu_tdp_watts": cpu_tdp,
        "gpu_tgp_watts": gpu_tgp,
        "power_peak_watts": peak_watts,
        "power_avg_watts": avg_watts,
        "power_efficiency": efficiency_tier,
        "power_efficiency_badge": efficiency_badge,
        "monthly_cost_eur": monthly_cost_eur,
        "is_dgpu": is_dgpu
    }
