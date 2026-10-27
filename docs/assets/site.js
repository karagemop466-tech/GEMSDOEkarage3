(function () {
  "use strict";
  function checkSourcesInBrowser(feed, watch, leaderboard) {
    var sites = Array.isArray(feed.sources) ? feed.sources : [];
    if (!sites.length || !window.AbortController) return;
    var checks = sites.map(function (site) {
      if (typeof site.site !== "string" || !/^GEMSDOE(?:24|25|27|28|30|31|32|33|36)$/.test(site.site)) {
        return Promise.resolve({available: false});
      }
      var controller = new AbortController();
      var timer = window.setTimeout(function () { controller.abort(); }, 8000);
      var url = "https://api.github.com/repos/buffedlizard55-lab/" + site.site + "/commits/main";
      return fetch(url, {cache: "no-store", credentials: "omit", signal: controller.signal})
        .then(function (response) { if (!response.ok) throw new Error("metadata unavailable"); return response.json(); })
        .then(function (data) {
          if (typeof data.sha !== "string" || !/^[0-9a-f]{40}$/.test(data.sha)) throw new Error("invalid commit");
          return {available: true, changed: typeof site.snapshot_commit === "string" ? data.sha !== site.snapshot_commit : null};
        }).catch(function () { return {available: false}; })
        .finally(function () { window.clearTimeout(timer); });
    });
    Promise.all(checks).then(function (results) {
      if (!watch) return;
      var available = results.filter(function (r) { return r.available; }).length;
      var comparable = results.filter(function (r) { return r.changed !== null && r.changed !== undefined; }).length;
      var changed = results.filter(function (r) { return r.changed === true; }).length;
      var comparison = comparable ? changed + "/" + comparable + " comparable repos changed since snapshot" : "change comparison unavailable";
      var lb = leaderboard.available ? "leaderboard feed is a dated snapshot" : "leaderboard feed unavailable; last observation is stale";
      watch.textContent = "Browser metadata check " + new Date().toISOString() + " · " + available + "/" + sites.length + " repositories reachable · " + comparison + " · " + lb + ". No refresh approves a submission.";
    });
  }
  fetch("data/feed.json", {cache: "no-store"}).then(function (res) {
    if (!res.ok) throw new Error("Source feed unavailable");
    return res.json();
  }).then(function (feed) {
    var leader = feed.leaderboard || {};
    var obs = leader.last_observation;
    var score = document.getElementById("public-score");
    var detail = document.getElementById("public-score-detail");
    var watch = document.getElementById("watch-detail");
    if (score && detail && obs && typeof obs.score === "number" && obs.score >= 0 && obs.score <= 1) {
      score.textContent = typeof obs.display_score === "string" ? obs.display_score : obs.score.toFixed(4);
      var parsed = Date.parse(obs.observed_utc || "");
      var fresh = leader.available === true && Number.isFinite(parsed) && Date.now() - parsed < 12 * 60 * 60 * 1000;
      detail.textContent = (fresh ? "PUBLIC snapshot · " : "PUBLIC snapshot, stale · ") + (obs.observed_utc || "time unknown");
    }
    if (watch) {
      var sites = Array.isArray(feed.sources) ? feed.sources : [];
      var count = sites.filter(function (s) { return s.available === true; }).length;
      watch.textContent = "Snapshot checked " + (feed.checked_utc || "at an unknown time") + " · " + count + "/" + sites.length + " site metadata responses · " + (leader.available ? "leaderboard fetched" : "leaderboard unavailable; last observation is stale") + ". Refresh never approves a submission.";
      checkSourcesInBrowser(feed, watch, leader);
    }
  }).catch(function () {
    var watch = document.getElementById("watch-detail");
    if (watch) watch.textContent = "Source feed unavailable. No submission is approved.";
  });
})();
