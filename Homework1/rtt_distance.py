import argparse
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from geopy.distance import distance as geodistance
import requests


@dataclass
class PingResult:
    avg_ms: Optional[float]
    raw: str
    ok: bool


def run_ping(host: str, count: int, timeout_s: int) -> PingResult:
    """
    Runs system ping and parses average RTT (ms).
    Works on macOS and Linux.
    """
    system = platform.system().lower()

    # macOS: ping -c <count> -W <timeout_ms>
    # Linux: ping -c <count> -W <timeout_s>
    if "darwin" in system:
        cmd = ["ping", "-c", str(count), "-W", str(timeout_s * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout_s), host]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (p.stdout or "") + "\n" + (p.stderr or "")
    except Exception as e:
        return PingResult(avg_ms=None, raw=str(e), ok=False)

    # macOS/Linux summary line:
    # rtt min/avg/max/mdev = 12.345/23.456/34.567/1.234 ms
    m = re.search(r"rtt [^=]*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms", out)
    if not m:
        # Sometimes mac prints: round-trip min/avg/max/stddev = ...
        m2 = re.search(
            r"round-trip [^=]*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms",
            out
        )
        if not m2:
            return PingResult(avg_ms=None, raw=out, ok=False)
        avg = float(m2.group(2))
        return PingResult(avg_ms=avg, raw=out, ok=True)

    avg = float(m.group(2))
    return PingResult(avg_ms=avg, raw=out, ok=True)


def get_public_ip_location() -> Optional[tuple[float, float]]:
    """
    Detect approximate source coordinates using IP geolocation.
    NOTE: This returns the location of the public IP/ISP PoP, not GPS-accurate position.
    """
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        r.raise_for_status()
        data = r.json()
        loc = data.get("loc")  # "lat,lon"
        if not loc:
            return None
        lat_str, lon_str = loc.split(",")
        lat, lon = float(lat_str), float(lon_str)
        city = data.get("city", "")
        region = data.get("region", "")
        country = data.get("country", "")
        org = data.get("org", "")
        print(f"[INFO] Auto-detected source location (IP-based): {lat}, {lon}  ({city}, {region}, {country})  {org}")
        return lat, lon
    except Exception as e:
        print(f"[WARNING] Could not auto-detect location via IP: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser(description="HW1: RTT vs Distance (active measurements)")
    ap.add_argument("--servers", required=True, help="Path to servers.csv")
    ap.add_argument("--src-lat", type=float, help="Source latitude (optional if auto-detect works)")
    ap.add_argument("--src-lon", type=float, help="Source longitude (optional if auto-detect works)")
    ap.add_argument("--count", type=int, default=10, help="Ping count per host (default 10)")
    ap.add_argument("--timeout", type=int, default=2, help="Ping timeout seconds (default 2)")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep between hosts (default 0.2s)")
    ap.add_argument("--out", default="results.csv", help="Output CSV (default results.csv)")
    args = ap.parse_args()

    # Auto-detect source coordinates if not provided
    if args.src_lat is None or args.src_lon is None:
        loc = get_public_ip_location()
        if loc is None:
            print(
                "Source coordinates not provided and auto-detection failed.\n"
                "Please run again with --src-lat <value> --src-lon <value>.",
                file=sys.stderr
            )
            sys.exit(1)
        args.src_lat, args.src_lon = loc

    df = pd.read_csv(args.servers)
    required_cols = {"hostname", "latitude", "longitude"}
    if not required_cols.issubset(set(df.columns)):
        print(f"servers.csv must include columns: {sorted(required_cols)}", file=sys.stderr)
        sys.exit(1)

    src = (args.src_lat, args.src_lon)
    print(f"[INFO] Using source coordinates: {src[0]:.6f}, {src[1]:.6f}")

    rows = []
    for i, r in df.iterrows():
        host = str(r["hostname"]).strip()
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        label = str(r["label"]).strip() if "label" in df.columns else host

        dist_km = geodistance(src, (lat, lon)).km

        pr = run_ping(host, args.count, args.timeout)
        rows.append({
            "hostname": host,
            "label": label,
            "dst_lat": lat,
            "dst_lon": lon,
            "distance_km": dist_km,
            "rtt_avg_ms": pr.avg_ms,
            "ping_ok": pr.ok
        })

        print(f"[{i+1}/{len(df)}] {host:30s} dist={dist_km:8.1f} km  rtt_avg={pr.avg_ms if pr.avg_ms is not None else 'NA'} ms  ok={pr.ok}")
        time.sleep(args.sleep)

    res = pd.DataFrame(rows)
    res.to_csv(args.out, index=False)
    print(f"\nSaved: {args.out}")

    # Filter valid results for fitting/plot
    valid = res[(res["ping_ok"] == True) & (res["rtt_avg_ms"].notna())].copy()
    if len(valid) < 3:
        print("Not enough valid points to fit a line (need at least 3).", file=sys.stderr)
        sys.exit(0)

    x = valid["distance_km"].to_numpy()
    y = valid["rtt_avg_ms"].to_numpy()

    # Linear fit RTT = m * d + q
    m, q = np.polyfit(x, y, 1)

    # R^2
    y_hat = m * x + q
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    print(f"\nFit: RTT = m*d + q")
    print(f"m (ms/km) = {m:.6f}")
    print(f"q (ms)    = {q:.3f}")
    print(f"R^2       = {r2:.4f}")

    # Plot
    x_line = np.linspace(x.min(), x.max(), 200)
    y_line = m * x_line + q

    plt.figure()
    plt.scatter(x, y)
    plt.plot(x_line, y_line)
    plt.xlabel("Distance (km)")
    plt.ylabel("Average RTT (ms)")
    plt.title("RTT vs Physical Distance (Active Measurements)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()