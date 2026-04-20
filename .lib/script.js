const predictionsRoot = document.getElementById("predictions-root");
const exportInfo = document.getElementById("export-info");
const modeFilter = document.getElementById("mode-filter");
const leagueFilter = document.getElementById("league-filter");
const roundFilter = document.getElementById("round-filter");

const state = {
    upcomingLeagues: [],
    historyLeagues: [],
    generatedAt: "",
    filters: {
        mode: "UPCOMING",
        league: "ALL",
        round: "ALL",
    },
};

function getActiveLeagues() {
    return state.filters.mode === "HISTORY" ? state.historyLeagues : state.upcomingLeagues;
}

function extractRoundNumber(roundLabel) {
    const match = String(roundLabel || "").match(/(\d+)(?!.*\d)/);
    return match ? Number(match[1]) : null;
}

function compareRounds(first, second) {
    const firstNumber = extractRoundNumber(first);
    const secondNumber = extractRoundNumber(second);

    if (firstNumber !== null && secondNumber !== null && firstNumber !== secondNumber) {
        return firstNumber - secondNumber;
    }

    return String(first || "").localeCompare(String(second || ""), "cs");
}

function formatGeneratedAt() {
    if (!state.generatedAt) {
        return "";
    }

    const parsed = new Date(state.generatedAt.replace(" UTC", "Z").replace(" ", "T"));
    if (Number.isNaN(parsed.getTime())) {
        return `Posledni export: ${state.generatedAt}`;
    }

    return `Posledni export: ${new Intl.DateTimeFormat("cs-CZ", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(parsed)}`;
}

function getVisibleLeagues() {
    return getActiveLeagues()
        .map((league) => ({
            ...league,
            predictions: league.predictions.filter((prediction) => {
                const sameLeague =
                    state.filters.league === "ALL" || String(league.code) === state.filters.league;
                const sameRound =
                    state.filters.round === "ALL" || prediction.round === state.filters.round;
                return sameLeague && sameRound;
            }),
        }))
        .filter((league) => league.predictions.length > 0);
}

function updateExportInfo(visiblePredictions) {
    const exportLabel = formatGeneratedAt();

    if (!visiblePredictions.length) {
        exportInfo.textContent = exportLabel;
        return;
    }

    if (state.filters.mode === "HISTORY") {
        const winnerHits = visiblePredictions.filter((prediction) => prediction.winnerHit).length;
        const goalHits = visiblePredictions.filter((prediction) => prediction.goalLineHit).length;
        exportInfo.textContent = [
            exportLabel,
            `Zapasy: ${visiblePredictions.length}`,
            `Vitez: ${winnerHits}/${visiblePredictions.length}`,
            `Under/Over: ${goalHits}/${visiblePredictions.length}`,
        ]
            .filter(Boolean)
            .join(" | ");
        return;
    }

    exportInfo.textContent = [exportLabel, `Zapasy: ${visiblePredictions.length}`]
        .filter(Boolean)
        .join(" | ");
}

function createPredictionCard(prediction) {
    const goalLine = prediction.predictedGoalLine || "neuvedeno";
    const roundRow = prediction.round
        ? `<p class="card-meta">Kolo: ${prediction.round}</p>`
        : "";

    if (state.filters.mode === "HISTORY") {
        return `
            <article class="card">
                <h3 class="card-title">${prediction.homeTeam} vs ${prediction.awayTeam}</h3>
                <p class="card-meta">${prediction.matchDate}</p>
                ${roundRow}
                <div class="card-row">
                    <span class="card-label">Predikce</span>
                    <span class="card-value">${prediction.predictedWinner} | ${goalLine}</span>
                </div>
                <div class="card-row">
                    <span class="card-label">Skutecnost</span>
                    <span class="card-value">${prediction.actualWinner} | ${prediction.actualGoalLine}</span>
                </div>
            </article>
        `;
    }

    return `
        <article class="card">
            <h3 class="card-title">${prediction.homeTeam} vs ${prediction.awayTeam}</h3>
            <p class="card-meta">${prediction.matchDate}</p>
            ${roundRow}
            <div class="card-row">
                <span class="card-label">Vitez</span>
                <span class="card-value">${prediction.predictedWinner}</span>
            </div>
            <div class="card-row">
                <span class="card-label">Under/Over</span>
                <span class="card-value">${goalLine}</span>
            </div>
        </article>
    `;
}

function createLeagueSection(league) {
    return `
        <section class="league-section">
            <h2 class="league-title">${league.leagueName}</h2>
            <div class="card-list">
                ${league.predictions.map(createPredictionCard).join("")}
            </div>
        </section>
    `;
}

function populateLeagueFilter() {
    const activeLeagues = getActiveLeagues();
    const availableCodes = activeLeagues.map((league) => String(league.code));

    if (state.filters.league !== "ALL" && !availableCodes.includes(state.filters.league)) {
        state.filters.league = "ALL";
    }

    leagueFilter.innerHTML = `
        <option value="ALL">Vsechny ligy</option>
        ${activeLeagues
            .map((league) => `<option value="${league.code}">${league.leagueName}</option>`)
            .join("")}
    `;
    leagueFilter.value = state.filters.league;
}

function populateRoundFilter() {
    const filteredLeagues =
        state.filters.league === "ALL"
            ? getActiveLeagues()
            : getActiveLeagues().filter(
                  (league) => String(league.code) === state.filters.league
              );

    const rounds = new Set();
    filteredLeagues.forEach((league) => {
        league.predictions.forEach((prediction) => {
            if (prediction.round) {
                rounds.add(prediction.round);
            }
        });
    });

    const orderedRounds = Array.from(rounds).sort(compareRounds);
    if (state.filters.round !== "ALL" && !orderedRounds.includes(state.filters.round)) {
        state.filters.round = "ALL";
    }

    roundFilter.innerHTML = `
        <option value="ALL">Vsechna kola</option>
        ${orderedRounds.map((round) => `<option value="${round}">${round}</option>`).join("")}
    `;
    roundFilter.value = state.filters.round;
}

function renderEmptyState(text) {
    predictionsRoot.innerHTML = `<p class="empty-state">${text}</p>`;
}

function render() {
    const visibleLeagues = getVisibleLeagues();
    const visiblePredictions = visibleLeagues.flatMap((league) => league.predictions);

    updateExportInfo(visiblePredictions);

    if (!visibleLeagues.length) {
        renderEmptyState("Pro vybrane filtry nejsou dostupne zadne zapasy.");
        return;
    }

    predictionsRoot.innerHTML = visibleLeagues.map(createLeagueSection).join("");
}

function bindFilters() {
    modeFilter.addEventListener("change", (event) => {
        state.filters.mode = event.target.value;
        state.filters.league = "ALL";
        state.filters.round = "ALL";
        populateLeagueFilter();
        populateRoundFilter();
        render();
    });

    leagueFilter.addEventListener("change", (event) => {
        state.filters.league = event.target.value;
        populateRoundFilter();
        render();
    });

    roundFilter.addEventListener("change", (event) => {
        state.filters.round = event.target.value;
        render();
    });
}

async function loadPredictions() {
    exportInfo.textContent = "Nacitam export...";
    renderEmptyState("Chvili pockej, nacitam predikce.");

    try {
        const response = await fetch("/data/processed/upcoming_predictions.json", {
            cache: "no-store",
        });
        if (!response.ok) {
            throw new Error("Fetch failed");
        }

        const payload = await response.json();
        state.upcomingLeagues = payload.upcomingLeagues || payload.leagues || [];
        state.historyLeagues = payload.historyLeagues || [];
        state.generatedAt = payload.generated_at || "";

        populateLeagueFilter();
        populateRoundFilter();
        render();
    } catch (error) {
        exportInfo.textContent = "Export se nepodarilo nacist.";
        renderEmptyState("Nejdriv spust python -m src.predict --export-upcoming-json.");
    }
}

bindFilters();
loadPredictions();
