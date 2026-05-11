import base64
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_dt(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip()
    return pd.to_datetime(s, errors="coerce", utc=False)


def img_tag(path: str | None, alt: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (
        f'<img src="data:image/png;base64,{b64}" alt="{alt}" '
        'style="width:100%;height:auto;border-radius:14px;'
        'border:1px solid rgba(212,160,23,0.25);" />'
    )


def to_csv_cell(value) -> str:
    s = "" if value is None else str(value)
    if any(ch in s for ch in [",", '"', "\n", "\r"]):
        return '"' + s.replace('"', '""') + '"'
    return s


def main() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(base_dir, "mciu-votes-2026-04-11-08-40-03.csv")
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}")

    out_dir = os.path.abspath(os.path.dirname(__file__))
    os.makedirs(out_dir, exist_ok=True)

    raw = pd.read_csv(csv_path)
    expected = [
        "matric",
        "voterName",
        "position",
        "positionKey",
        "candidateId",
        "candidateName",
        "votedAt",
        "completedAt",
    ]
    for c in expected:
        if c not in raw.columns:
            raw[c] = ""

    df = raw.copy()
    df["matric"] = df["matric"].fillna("").astype(str).str.strip().str.upper()
    df["voterName"] = df["voterName"].fillna("").astype(str).str.strip()
    df["position"] = df["position"].fillna("").astype(str).str.strip()
    df["positionKey"] = df["positionKey"].fillna("").astype(str).str.strip().str.lower()
    df["candidateId"] = df["candidateId"].fillna("").astype(str).str.strip()
    df["candidateName"] = df["candidateName"].fillna("").astype(str).str.strip()
    df["votedAt_dt"] = parse_dt(df["votedAt"])
    df["completedAt_dt"] = parse_dt(df["completedAt"])

    summary = {
        "total_votes": int(len(df)),
        "unique_voters": int(df.loc[df["matric"] != "", "matric"].nunique()),
        "unique_candidates": int(df.loc[df["candidateId"] != "", "candidateId"].nunique()),
        "positions_voted": int(df.loc[df["positionKey"] != "", "positionKey"].nunique()),
        "missing_voter_names": int((df["voterName"] == "").sum()),
    }

    dup_pos = (
        df[df["matric"] != ""]
        .groupby(["matric", "positionKey"])
        .size()
        .reset_index(name="count")
        .query("count>1")
    )
    summary["duplicate_votes_same_position"] = int(len(dup_pos))

    by_position = df.groupby("positionKey").size().sort_values(ascending=False)
    by_candidate = (
        df.groupby(["positionKey", "candidateName", "candidateId"])
        .size()
        .reset_index(name="votes")
    )
    by_candidate_sorted = by_candidate.sort_values("votes", ascending=False)

    winners = (
        by_candidate.sort_values(["positionKey", "votes"], ascending=[True, False])
        .groupby("positionKey")
        .head(1)
        .reset_index(drop=True)
    )

    votes_per_voter = (
        df[df["matric"] != ""]
        .groupby("matric")
        .size()
        .reset_index(name="votes_cast")
        .sort_values(["votes_cast", "matric"], ascending=[False, True])
    )

    votes_per_voter.to_csv(os.path.join(out_dir, "votes_per_voter.csv"), index=False)
    by_position.reset_index(name="votes").to_csv(
        os.path.join(out_dir, "votes_by_position.csv"), index=False
    )
    winners[["positionKey", "candidateName", "votes"]].to_csv(
        os.path.join(out_dir, "leading_candidate_by_position.csv"), index=False
    )
    by_candidate_sorted.to_csv(os.path.join(out_dir, "votes_by_candidate.csv"), index=False)

    per_pos_imgs: list[tuple[str, str]] = []
    for pos_key in sorted(
        [k for k in df["positionKey"].unique() if isinstance(k, str) and k.strip()]
    ):
        sub = df[df["positionKey"] == pos_key]
        counts = sub.groupby("candidateName").size().sort_values(ascending=False)
        if counts.empty:
            continue
        fig = plt.figure(figsize=(10, 4.8))
        ax = plt.gca()
        ax.bar(counts.index.astype(str), counts.values, color="#d4a017")
        ax.set_title(f"Votes by Candidate — {pos_key}")
        ax.set_xlabel("Candidate")
        ax.set_ylabel("Votes")
        ax.tick_params(axis="x", labelrotation=20)
        plt.tight_layout()
        fname = f"position_{pos_key.replace(' ', '_')}_candidates.png"
        fpath = os.path.join(out_dir, fname)
        plt.savefig(fpath, dpi=170)
        plt.close(fig)
        per_pos_imgs.append((pos_key, fpath))

    votes_per_voter_img = os.path.join(out_dir, "votes_per_voter_hist.png")
    fig = plt.figure(figsize=(8.5, 4.2))
    ax = plt.gca()
    if len(votes_per_voter):
        bins = list(range(0, int(votes_per_voter["votes_cast"].max()) + 2))
        ax.hist(
            votes_per_voter["votes_cast"],
            bins=bins,
            align="left",
            rwidth=0.85,
            color="#1e3a8a",
        )
    ax.set_title("Votes Cast per Voter")
    ax.set_xlabel("Number of Votes Cast")
    ax.set_ylabel("Number of Voters")
    plt.tight_layout()
    plt.savefig(votes_per_voter_img, dpi=170)
    plt.close(fig)

    votes_over_time_img = None
    if df["votedAt_dt"].notna().any():
        per_hour = (
            df.dropna(subset=["votedAt_dt"])
            .set_index("votedAt_dt")
            .sort_index()
            .resample("h")
            .size()
        )
        if len(per_hour):
            votes_over_time_img = os.path.join(out_dir, "votes_over_time_hourly.png")
            fig = plt.figure(figsize=(10, 4))
            ax = plt.gca()
            ax.plot(per_hour.index, per_hour.values, color="#0b2a6f", linewidth=2)
            ax.fill_between(per_hour.index, per_hour.values, color="#0b2a6f", alpha=0.15)
            ax.set_title("Votes Over Time (Hourly)")
            ax.set_xlabel("Time")
            ax.set_ylabel("Votes")
            plt.tight_layout()
            plt.savefig(votes_over_time_img, dpi=170)
            plt.close(fig)

    votes_by_position_img = None
    if len(by_position):
        votes_by_position_img = os.path.join(out_dir, "votes_by_position.png")
        fig = plt.figure(figsize=(10, 4))
        ax = plt.gca()
        by_position.sort_index().plot(kind="bar", color="#1e3a8a", ax=ax)
        ax.set_title("Votes by Position")
        ax.set_xlabel("Position")
        ax.set_ylabel("Votes")
        plt.tight_layout()
        plt.savefig(votes_by_position_img, dpi=170)
        plt.close(fig)

    top_candidates_img = None
    top = by_candidate_sorted.head(12).copy()
    if len(top):
        top_candidates_img = os.path.join(out_dir, "top_candidates.png")
        top["label"] = top["positionKey"].astype(str) + " — " + top["candidateName"].astype(
            str
        )
        top = top.sort_values("votes", ascending=True)
        fig = plt.figure(figsize=(10, 6))
        ax = plt.gca()
        ax.barh(top["label"], top["votes"], color="#d4a017")
        ax.set_title("Top Candidates (Overall)")
        ax.set_xlabel("Votes")
        plt.tight_layout()
        plt.savefig(top_candidates_img, dpi=170)
        plt.close(fig)

    winners_rows = "".join(
        f"<tr><td>{p}</td><td>{n}</td><td style='text-align:right'>{int(v)}</td></tr>"
        for p, n, v in winners[["positionKey", "candidateName", "votes"]].itertuples(
            index=False, name=None
        )
    )
    pos_rows = "".join(
        f"<tr><td>{p}</td><td style='text-align:right'>{int(v)}</td></tr>"
        for p, v in by_position.items()
    )
    active_rows = "".join(
        f"<tr><td>{m}</td><td style='text-align:right'>{int(c)}</td></tr>"
        for m, c in votes_per_voter.head(15).itertuples(index=False, name=None)
    )
    per_pos_sections = ""
    for pos_key, path in per_pos_imgs:
        per_pos_sections += (
            f"<h3 style='margin:22px 0 10px'>Position Breakdown: {pos_key}</h3>"
            + img_tag(path, f"Votes by candidate — {pos_key}")
        )

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_path = os.path.join(out_dir, "mciu_voting_report.html")

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>MCIU Voting Descriptive Report</title>
<style>
  :root {{ --blue:#1e3a8a; --navy:#0b2a6f; --gold:#d4a017; --text:#0f172a; }}
  body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background: linear-gradient(135deg, var(--navy), var(--blue) 55%, var(--gold) 140%); color: var(--text); }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 28px 16px 60px; }}
  .top {{ background: rgba(255,255,255,0.92); border: 1px solid rgba(212,160,23,0.25); border-radius: 18px; padding: 18px; box-shadow: 0 18px 40px rgba(11,42,111,0.25); }}
  h1 {{ margin: 0 0 6px; font-size: 24px; }}
  .sub {{ color:#334155; font-size: 13px; }}
  .grid {{ display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
  .kpi {{ background:#fff; border:1px solid rgba(212,160,23,0.18); border-radius: 14px; padding: 12px; }}
  .kpi .k {{ font-size: 12px; color:#475569; }}
  .kpi .v {{ font-size: 22px; font-weight: 700; margin-top: 6px; }}
  .card {{ background:#fff; border:1px solid rgba(212,160,23,0.18); border-radius: 18px; padding: 18px; margin-top: 16px; }}
  h2 {{ margin: 0 0 10px; font-size: 18px; }}
  h3 {{ margin: 0 0 10px; font-size: 15px; }}
  table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px 6px; text-align:left; }}
  th {{ color:#334155; font-weight: 700; }}
  .note {{ color:#475569; font-size: 12px; line-height: 1.45; }}
  @media (max-width: 860px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <h1>MCIU Voting Portal — Descriptive Analysis Report</h1>
      <div class="sub">Generated {stamp} • Source file: {os.path.basename(csv_path)}</div>
      <div class="grid">
        <div class="kpi"><div class="k">Total Votes</div><div class="v">{summary['total_votes']}</div></div>
        <div class="kpi"><div class="k">Unique Voters</div><div class="v">{summary['unique_voters']}</div></div>
        <div class="kpi"><div class="k">Positions Voted</div><div class="v">{summary['positions_voted']}</div></div>
        <div class="kpi"><div class="k">Duplicate Votes</div><div class="v">{summary['duplicate_votes_same_position']}</div></div>
      </div>
      <p class="note" style="margin:12px 0 0">Duplicate votes are multiple votes by the same matric for the same positionKey.</p>
    </div>

    <div class="card">
      <h2>Votes by Position</h2>
      {img_tag(votes_by_position_img, 'Votes by position')}
      <div style="margin-top:12px">
        <table>
          <thead><tr><th>Position</th><th style="text-align:right">Votes</th></tr></thead>
          <tbody>{pos_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>Winners / Leading Candidates</h2>
      <table>
        <thead><tr><th>Position</th><th>Leading Candidate</th><th style="text-align:right">Votes</th></tr></thead>
        <tbody>{winners_rows}</tbody>
      </table>
      <div style="margin-top:14px">
        {img_tag(top_candidates_img, 'Top candidates overall')}
      </div>
    </div>

    <div class="card">
      <h2>Participation / Turnout</h2>
      <div style="display:grid; grid-template-columns: 1.25fr 0.75fr; gap: 14px; align-items:start;">
        <div>
          {img_tag(votes_per_voter_img, 'Votes cast per voter')}
          <p class="note" style="margin:10px 0 0">With 5 positions, the maximum expected is 5 votes per voter.</p>
        </div>
        <div>
          <h3>Most Active Voters</h3>
          <table>
            <thead><tr><th>Matric</th><th style="text-align:right">Votes Cast</th></tr></thead>
            <tbody>{active_rows}</tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Voting Over Time</h2>
      {img_tag(votes_over_time_img, 'Votes over time (hourly)')}
      <p class="note" style="margin:10px 0 0">Time series uses the votedAt timestamp in the CSV.</p>
    </div>

    <div class="card">
      <h2>Per-Position Candidate Results</h2>
      <p class="note">Bars show vote totals per candidate for each position.</p>
      {per_pos_sections}
    </div>

    <div class="card">
      <h2>Data Notes</h2>
      <ul class="note">
        <li>Total records analyzed: {summary['total_votes']} votes.</li>
        <li>Missing voterName values: {summary['missing_voter_names']}.</li>
        <li>Duplicate votes per positionKey: {summary['duplicate_votes_same_position']}.</li>
      </ul>
    </div>
  </div>
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("Report written:", report_path)
    print("Tables/charts written to:", out_dir)


if __name__ == "__main__":
    main()
