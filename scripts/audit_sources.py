"""Refresh pinned GitHub evidence and merge HOLDOUT-DTI + uniqueness audit into docs/sites.json."""
import base64
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SITES = [24, 25, 27, 28, 30, 31, 32, 33, 36]
CLAIMS = {
    24: ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477, "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros: 0.0859"),
    25: ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600, "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros: 0.0742"),
    27: ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449, "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite: 0.2250; h29: 0.2190"),
    28: ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710, "h27-4: 0.2708; h38-1: 0.2707; h32-1: 0.2649; s18: 0.0217; s21: 0.0206"),
    30: ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600, "gems30-MSDB1-edge44090-20261025-e7856ec3f14a: 0.1462"),
    31: ("h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708, "Identical 40,199-dot B=1 sibling of GEMSDOE28 h27-4"),
    32: ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778, "Highest ORGANIZER-CONFIRMED score among all GEMSDOE sites (37,654 dots, B=2)"),
    33: ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632, "gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros: 0.0963"),
    36: ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750, "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros: 0.1647"),
}


def gh(path: str) -> bytes:
    return subprocess.check_output(["gh", "api", path], stderr=subprocess.DEVNULL, timeout=60)


def load_refreshed_audit() -> dict[str, dict]:
    p = ROOT / "evidence" / "nine_site_refreshed_audit_20261027.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {row["repo"]: row for row in data.get("sites", [])}


def audit(n: int, audit_map: dict[str, dict]) -> dict:
    site_name = f"GEMSDOE{n}"
    repo = f"buffedlizard55-lab/{site_name}"
    m = audit_map.get(site_name, {})
    ov_champ = m.get("within_3px_of_02778_champion")
    ov_hk3 = m.get("within_3px_of_hk3_smgc")
    is_unique_vs_champ = (ov_champ <= 0.70) if isinstance(ov_champ, (int, float)) else None
    result = {
        "site": site_name,
        "repository": f"https://github.com/{repo}",
        "owner_reported_submission": CLAIMS[n][0],
        "owner_reported_value": CLAIMS[n][1],
        "other_confirmed_submissions": CLAIMS[n][2],
        "evidence_class": "ORGANIZER-CONFIRMED (leaderboard receipt in user prompt & repo)",
        "latest_inspected_download": m.get("inspected_path"),
        "latest_inspected_sha256": m.get("sha256"),
        "latest_emitted_dots": m.get("emitted_dots"),
        "latest_whole_array_finite": m.get("whole_array_finite"),
        "holdout_dti_static_hide_recover": m.get("static_hide_recover_dti"),
        "holdout_dti_sgmc_calibrated": m.get("sgmc_prevalence_calibrated_dti"),
        "within_3px_of_02778_champion": ov_champ,
        "within_3px_of_hk3_smgc": ov_hk3,
        "estimated_score": m.get("sgmc_prevalence_calibrated_dti"),
        "unique": is_unique_vs_champ,
        "ok_to_submit": bool(site_name == "GEMSDOE32"),
    }
    try:
        meta = json.loads(gh(f"repos/{repo}"))
        commit = json.loads(gh(f'repos/{repo}/commits/{meta["default_branch"]}'))["sha"]
        result["commit"] = commit
        for path in ["README.md", "registry/current_status.json"]:
            try:
                entry = json.loads(gh(f"repos/{repo}/contents/{path}?ref={commit}"))
                data = base64.b64decode(entry["content"])
                dest = ROOT / "evidence" / "upstream" / site_name / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                result.setdefault("sources", []).append(
                    {
                        "url": f"https://github.com/{repo}/blob/{commit}/{path}",
                        "local": str(dest.relative_to(ROOT)),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
            except subprocess.CalledProcessError:
                pass
    except (subprocess.SubprocessError, KeyError, ValueError) as exc:
        result["error"] = str(exc)
    return result


if __name__ == "__main__":
    audit_map = load_refreshed_audit()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(lambda n: audit(n, audit_map), SITES))
    rc_path = ROOT / "docs" / "run-card.json"
    promoted = {}
    if rc_path.exists():
        rc = json.loads(rc_path.read_text())
        promoted = {
            "site": "GEMSDOEkarage3",
            "repository": "https://github.com/karagemop466-tech/GEMSDOEkarage3",
            "candidate_id": rc.get("candidate_id"),
            "submission_file": rc.get("submission_file"),
            "submission_name": rc.get("submission_name"),
            "submission_note": rc.get("note"),
            "raster_sha256": rc.get("raster_sha256"),
            "holdout_dti_hide_recover_v3": rc.get("holdout_dti", {}).get("score"),
            "holdout_dti_hide_recover_ci95": rc.get("holdout_dti", {}).get("ci95"),
            "holdout_dti_sgmc_calibrated_v3": rc.get("holdout_dti", {}).get("off_catalogue_sgmc", {}).get("prevalence_calibrated_dti"),
            "max_3px_overlap_vs_registry": rc.get("correlation_overlap_vs_registry", {}).get("max_dot_overlap_3px"),
            "max_abs_spearman_vs_registry": rc.get("correlation_overlap_vs_registry", {}).get("max_rank_correlation"),
            "verdict": rc.get("verdict"),
            "ok_to_submit": rc.get("ok_to_submit"),
        }
    target = ROOT / "docs" / "sites.json"
    target.write_text(
        json.dumps(
            {
                "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "promoted_candidate": promoted,
                "sites": rows,
            },
            indent=2,
        )
        + "\n"
    )
