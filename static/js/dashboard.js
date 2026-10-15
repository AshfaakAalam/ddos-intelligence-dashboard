(() => {
  "use strict";

  const API_URL = "/api/attacks";
  const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/attacks`;
  const FALLBACK_REFRESH_MS = 60_000;
  let globe = null;
  let socket = null;
  let fallbackTimer = null;
  let lastPayloadSignature = "";
  let socketHeartbeat = null;
  let ringsByKey = new Map();
  
  const $ = (id) => document.getElementById(id);
  const number = (value) => new Intl.NumberFormat().format(Number(value || 0));
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  function setStatus(status, message) {
    const dot = $("status-dot");
    dot.className = `status-dot ${status === "live" ? "is-live" : status === "stale" ? "is-stale" : "is-error"}`;
    $("connection-label").textContent = status === "live" ? "Data available" :
      status === "stale" ? "Showing last saved data" :
      status === "no_data" ? "No records returned" :
      status === "error" ? "Data source unavailable" : "Connecting";
    if (message) {
      $("notice").textContent = message;
      $("notice").classList.add("visible");
    } else {
      $("notice").classList.remove("visible");
    }
  }

  function initGlobe() {
    const container = $("attack-map");
    if (typeof Globe !== "function") {
      container.innerHTML = '<div class="globe-error">The 3D globe library could not load. Check your internet connection or CDN access.</div>';
      return;
    }
    container.innerHTML = "";
    globe = Globe()(container)
      .backgroundColor("#080c11")
      .globeImageUrl("https://unpkg.com/three-globe/example/img/earth-night.jpg")
      .bumpImageUrl("https://unpkg.com/three-globe/example/img/earth-topology.png")
      .showAtmosphere(true)
      .atmosphereColor("#426b98")
      .atmosphereAltitude(0.18)
      .arcsData([])
      .arcStartLat("startLat")
      .arcStartLng("startLng")
      .arcEndLat("endLat")
      .arcEndLng("endLng")
      .arcColor(() => ["rgba(255,65,85,0.9)", "rgba(255,176,0,0.9)"])
      .arcStroke((d) => Math.max(0.25, Math.min(1.4, 0.3 + (Number(d.percentage) || 0) / 40)))
      .arcAltitude((d) => d.sameCountry ? 0.01 : 0.22)
      .arcDashLength(0.42)
      .arcDashGap(0.22)
      .arcDashAnimateTime(1600)
      .pointsData([])
      .pointLat("lat")
      .pointLng("lng")
      .pointColor("color")
      .pointAltitude(0.012)
      .pointRadius(0.22)
      .pointResolution(8)
      .pointLabel((d) => `${escapeHtml(d.country)} (${escapeHtml(d.role)})`);
    globe.controls().autoRotate = true;
    globe.controls().autoRotateSpeed = 0.22;
    globe.controls().enableDamping = true;
    const resize = () => {
      if (globe) globe.width(container.clientWidth).height(Math.max(340, Math.min(600, container.clientWidth * 0.58)));
    };
    resize();
    window.addEventListener("resize", resize);
  }

  function validCoordinate(lat, lng) {
    return Number.isFinite(Number(lat)) && Number.isFinite(Number(lng)) &&
      Math.abs(Number(lat)) <= 90 && Math.abs(Number(lng)) <= 180;
  }

  function updateGlobe(attacks) {
    if (!globe) return;
    const arcs = [];
    const pointsByKey = new Map();
    attacks.forEach((attack) => {
      const startOk = validCoordinate(attack.source_latitude, attack.source_longitude);
      const endOk = validCoordinate(attack.target_latitude, attack.target_longitude);
      if (!startOk || !endOk) return;
      const startLat = Number(attack.source_latitude), startLng = Number(attack.source_longitude);
      const endLat = Number(attack.target_latitude), endLng = Number(attack.target_longitude);
      const sameCountry = attack.source === attack.target;
      arcs.push({ ...attack, startLat, startLng, endLat, endLng, sameCountry });
          if (sameCountry) {
            const ringKey = `${attack.source}:${startLat}:${startLng}`;
            if (!ringsByKey.has(ringKey)) ringsByKey.set(ringKey, { lat: startLat, lng: startLng });
          }
      const sourceKey = `source:${attack.source || attack.source_country}`;
      const targetKey = `target:${attack.target || attack.target_country}`;
      if (!pointsByKey.has(sourceKey)) pointsByKey.set(sourceKey, {
        lat: startLat, lng: startLng, country: attack.source_country, role: "source", color: "#ff4155"
      });
      if (!pointsByKey.has(targetKey)) pointsByKey.set(targetKey, {
        lat: endLat, lng: endLng, country: attack.target_country, role: "target", color: "#ffb000"
      });
    });
    globe.arcsData(arcs).pointsData(Array.from(pointsByKey.values())).ringsData(Array.from(ringsByKey.values()));
  }

  function updateTable(attacks) {
    $("record-count-label").textContent = `${number(attacks.length)} record${attacks.length === 1 ? "" : "s"}`;
    const body = $("attack-list");
    if (!attacks.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty-state">No valid records were returned in the latest observation.</td></tr>';
      return;
    }
    // Deliberately render the entire returned list; do not slice to top five.
    body.innerHTML = attacks.map((attack, index) => `
      <tr>
        <td class="rank-cell">${escapeHtml(attack.rank ?? index + 1)}</td>
        <td><span class="country-name">${escapeHtml(attack.source_country || attack.source || "Unknown")}</span><span class="country-code">${escapeHtml(attack.source || "")}</span></td>
        <td class="route-arrow">→</td>
        <td><span class="country-name">${escapeHtml(attack.target_country || attack.target || "Unknown")}</span><span class="country-code">${escapeHtml(attack.target || "")}</span></td>
        <td class="numeric share-cell">${Number(attack.percentage || 0).toFixed(2)}%</td>
      </tr>`).join("");
  }

  function renderPayload(data) {
    if (!data || typeof data !== "object") return;
    const attacks = Array.isArray(data.attacks) ? data.attacks : [];
    $("source-country-count").textContent = number(data.source_country_count);
    $("target-country-count").textContent = number(data.target_country_count);
    $("attack-count").textContent = number(data.attack_count ?? attacks.length);
    $("poll-interval").textContent = `${number(data.poll_interval_seconds || 300)} seconds`;
    $("last-updated").textContent = data.last_updated ? new Date(data.last_updated).toLocaleString() : "Not yet fetched";
        $("source-updated").textContent = data.source_timestamp ? String(data.source_timestamp) : "Not provided by endpoint";
    updateTable(attacks);
    updateGlobe(attacks);
    const signature = `${data.last_updated || ""}:${attacks.length}:${data.status || ""}`;
    if (signature !== lastPayloadSignature) {
      lastPayloadSignature = signature;
      // The globe's dash animation supplies motion between actual API observations.
    }
    const message = data.error
      ? `Cloudflare data could not be refreshed: ${data.error}. ${attacks.length ? "The last saved observation is still displayed." : "Check API_TOKEN and connectivity in the server configuration."}`
      : data.status === "no_data"
        ? "The API request succeeded, but no valid country-level records were returned."
        : "";
    setStatus(data.status || "waiting", message);
  }

  async function loadAttackData(force = false) {
    const button = $("refresh-button");
    button.disabled = true;
    button.textContent = "Refreshing…";
    try {
      const response = await fetch(`${API_URL}${force ? "?refresh=true" : ""}`, { headers: { "Accept": "application/json" } });
      if (!response.ok) throw new Error(`Dashboard API returned HTTP ${response.status}`);
      renderPayload(await response.json());
    } catch (error) {
      setStatus("error", `Could not load dashboard data: ${error.message}`);
    } finally {
      button.disabled = false;
      button.textContent = "↻ Refresh now";
    }
  }

  function connectWebSocket() {
    try {
      socket = new WebSocket(WS_URL);
      socket.addEventListener("open", () => {
            if (fallbackTimer) { clearInterval(fallbackTimer); fallbackTimer = null; }
            if (socketHeartbeat) clearInterval(socketHeartbeat);
            socketHeartbeat = setInterval(() => {
              if (socket && socket.readyState === WebSocket.OPEN) socket.send("ping");
            }, 25000);
          });
          socket.addEventListener("message", (event) => {
        try { renderPayload(JSON.parse(event.data)); } catch (error) { console.error("Invalid WebSocket payload", error); }
      });
      socket.addEventListener("close", () => {
        if (fallbackTimer) clearInterval(fallbackTimer);
        fallbackTimer = setInterval(() => loadAttackData(false), FALLBACK_REFRESH_MS);
        setTimeout(connectWebSocket, 5000);
      });
      socket.addEventListener("error", () => socket.close());
    } catch (error) {
      fallbackTimer = setInterval(() => loadAttackData(false), FALLBACK_REFRESH_MS);
    }
  }

  $("refresh-button").addEventListener("click", () => loadAttackData(true));
  initGlobe();
  loadAttackData(false);
  connectWebSocket();
})();
