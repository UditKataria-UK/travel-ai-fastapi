"use strict";

/* =========================================================
   AI Trip Planner · frontend logic
   - Sends the same POST request as before to the FastAPI backend
   - Renders structured fields exactly as returned by the API
   - Renders Markdown safely: marked -> DOMPurify (never raw innerHTML of LLM text)
   ========================================================= */

/* ---------- Config ---------- */
const API_URL = "https://travel-ai-fastapi.onrender.com/plan-trip";
const REQUEST_TIMEOUT_MS = 180000;   // abort a request after 3 minutes
const SLOW_NOTICE_MS = 20000;        // show the "taking longer" note after 20s
const MESSAGE_INTERVAL_MS = 4500;    // rotate loading messages

// Client-side sanity limits (edit freely; the backend contract is unchanged)
const LIMITS = {
    days: { min: 1, max: 60 },
    travelers: { min: 1, max: 50 },
    budget: { min: 1 },
};

// Describes what the planner does; these are NOT progress indicators.
const LOADING_MESSAGES = [
    "Gathering weather, places and hotels for your destination",
    "Drafting a day-wise itinerary around your budget",
    "Putting the final travel plan together",
];

/* ---------- DOM ---------- */
const $ = (id) => document.getElementById(id);

const tripForm = $("tripForm");
const loading = $("loading");
const loadingMessage = $("loadingMessage");
const loadingNote = $("loadingNote");
const tripResult = $("tripResult");
const submitBtn = $("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const chipButtons = tripForm.querySelectorAll(".chip");

// Order matches the visual order of the form (used for focusing the first error)
const fields = {
    destination: $("destination"),
    days: $("days"),
    budget: $("budget"),
    travelers: $("travelers"),
};

const prefersReducedMotion = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let isLoading = false;
let messageTimer = null;
let slowTimer = null;


/* =========================================================
   Small helpers (presentation only: they never change data)
   ========================================================= */

// Escape text before placing it inside an HTML template
function esc(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// Icon from the sprite in index.html
function icon(name, extraClass = "") {
    return `<svg class="icon ${extraClass}" aria-hidden="true" focusable="false"><use href="#i-${name}"></use></svg>`;
}

function isPresent(value) {
    return value !== null && value !== undefined && String(value).trim() !== "";
}

// Returns a finite number or NaN. Accepts numbers and numeric strings like "12,000".
function toNumber(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
    if (typeof value === "string" && value.trim() !== "") {
        const n = Number(value.replace(/,/g, "").trim());
        return Number.isFinite(n) ? n : NaN;
    }
    return NaN;
}

// "₹15,000" for numeric values; anything else is shown exactly as received
function formatMoney(value) {
    if (!isPresent(value)) return "—";
    const n = toNumber(value);
    return Number.isFinite(n)
        ? "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 })
        : String(value);
}

// Adds a unit only to plain numeric values ("18" -> "18°C"); "18°C" stays as is
function formatWithUnit(value, unit) {
    if (!isPresent(value)) return "—";
    return Number.isFinite(toNumber(value)) ? `${value}${unit}` : String(value);
}

function formatCount(value, singular) {
    if (!isPresent(value)) return "—";
    const n = toNumber(value);
    if (!Number.isFinite(n)) return String(value);
    return `${value} ${n === 1 ? singular : singular + "s"}`;
}

// Maps the backend's budget_status text to a visual tone.
// Unrecognised text falls back to "neutral" and is displayed unchanged.
function statusTone(status) {
    const s = String(status ?? "").toLowerCase();
    if (/\bnot\s+(over|exceed\w*|above|beyond)\b/.test(s)) return "good";
    if (/\b(over|exceed\w*|above|beyond|insufficient|short)\b/.test(s) || /\bnot\s+within\b/.test(s)) return "over";
    if (/\b(within|under|good|ok|okay|fits?|comfortable|affordable)\b/.test(s)) return "good";
    return "neutral";
}

function statusIcon(tone) {
    return tone === "good" ? "check" : tone === "over" ? "alert" : "info";
}

// Lets an API item be an object or a plain string
function asItem(entry) {
    if (typeof entry === "string") return { name: entry };
    return entry && typeof entry === "object" ? entry : {};
}

function emptyState(message) {
    return `<div class="empty-state">${icon("info")}<p>${esc(message)}</p></div>`;
}


/* =========================================================
   Safe Markdown rendering
   ========================================================= */

const markdownReady = () =>
    typeof marked !== "undefined" && typeof DOMPurify !== "undefined";

function configureMarkdown() {
    if (!markdownReady()) return;

    marked.use({
        gfm: true,
        breaks: false,
        renderer: {
            // Raw HTML written by the model is shown as visible text, never executed
            html(html) { return esc(html); },
            // No remote images; keep the alt text so no information is lost
            image(href, title, text) { return esc(text || ""); },
        },
    });

    // Links open in a new tab without leaking window.opener
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
        if (node.tagName === "A") {
            node.setAttribute("target", "_blank");
            node.setAttribute("rel", "noopener noreferrer");
        }
    });
}

// Wrap tables so wide ones scroll inside the card instead of the page
function wrapTables(html) {
    const tpl = document.createElement("template");
    tpl.innerHTML = html;
    tpl.content.querySelectorAll("table").forEach((table) => {
        const wrap = document.createElement("div");
        wrap.className = "table-wrap";
        wrap.tabIndex = 0;
        wrap.setAttribute("role", "region");
        wrap.setAttribute("aria-label", "Scrollable table");
        table.replaceWith(wrap);
        wrap.appendChild(table);
    });
    return tpl.innerHTML;
}

// Markdown -> sanitized HTML. If the libraries failed to load, fall back to
// escaped plain text (still readable, still safe, nothing removed).
function renderMarkdown(markdown) {
    const source = String(markdown ?? "");
    if (!source.trim()) return "";
    if (!markdownReady()) return `<p class="plain-text">${esc(source)}</p>`;

    try {
        const dirty = marked.parse(source);
        const clean = DOMPurify.sanitize(dirty, {
            FORBID_TAGS: ["style", "form", "input", "button", "textarea", "select", "img", "svg", "math"],
            FORBID_ATTR: ["style"],
        });
        return wrapTables(clean);
    } catch (error) {
        console.error("Markdown rendering failed:", error);
        return `<p class="plain-text">${esc(source)}</p>`;
    }
}

// Inline-only Markdown (used for day titles)
function renderInline(text) {
    if (!markdownReady()) return esc(text);
    try {
        return DOMPurify.sanitize(marked.parseInline(String(text)), {
            ALLOWED_TAGS: ["strong", "em", "code", "del"],
            ALLOWED_ATTR: [],
        });
    } catch (error) {
        return esc(text);
    }
}

// itinerary / final_plan are expected to be Markdown strings, but if the API
// ever returns an array or object we show its content instead of dropping it.
function toMarkdown(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "string") return value;
    if (Array.isArray(value)) {
        return value
            .map((item) =>
                typeof item === "string"
                    ? item
                    : "```json\n" + JSON.stringify(item, null, 2) + "\n```"
            )
            .join("\n\n");
    }
    if (typeof value === "object") return "```json\n" + JSON.stringify(value, null, 2) + "\n```";
    return String(value);
}


/* =========================================================
   Itinerary: split Markdown into day sections
   (only changes how content is grouped, never what it says)
   ========================================================= */

const DAY_HEADING = /^ {0,3}(#{1,6})?[ \t]*(\*\*|__)?[ \t]*Day[ \t]*(\d+)(?:[ \t]*[-–—][ \t]*(\d+))?\b(.*)$/i;
const ANY_HEADING = /^ {0,3}(#{1,6})[ \t]+\S/;
const FENCE = /^ {0,3}(```|~~~)/;
// Same-level headings with these words end the last day (e.g. "## Budget Summary")
const SECTION_WORDS = /(tip|budget|summary|total|cost|note|packing|accommodation|transport|overview|conclusion|recommend|estimate|safety)/i;

function parseDayHeading(line) {
    const m = DAY_HEADING.exec(line);
    if (!m) return null;

    const [, hashes, bold, number, rangeEnd, rest] = m;
    // A plain line (no "#" or "**") must be short to count as a heading
    if (!hashes && !bold && line.trim().length > 100) return null;

    const title = rest
        .replace(/\*\*|__/g, "")
        .replace(/\s+#+\s*$/, "")
        .trim()
        .replace(/^[:\-–—.)\s]+/, "")
        .trim();

    return {
        level: hashes ? hashes.length : 0,
        number,
        label: `Day ${number}${rangeEnd ? "–" + rangeEnd : ""}`,
        title,
    };
}

function splitItinerary(markdown) {
    const blocks = [{ type: "intro", lines: [] }];
    let current = blocks[0];
    let dayLevel = 0;
    let inFence = false;

    for (const line of markdown.split(/\r?\n/)) {
        if (FENCE.test(line)) {
            inFence = !inFence;
            current.lines.push(line);
            continue;
        }

        if (!inFence) {
            const day = parseDayHeading(line);
            if (day) {
                current = { type: "day", ...day, lines: [] };
                blocks.push(current);
                dayLevel = day.level;
                continue;
            }

            const heading = ANY_HEADING.exec(line);
            if (heading && current.type === "day") {
                const level = heading[1].length;
                const endsDay = dayLevel === 0
                    ? level <= 2
                    : level < dayLevel || (level === dayLevel && SECTION_WORDS.test(line));
                if (endsDay) {
                    current = { type: "extra", lines: [line] };
                    blocks.push(current);
                    continue;
                }
            }
        }

        current.lines.push(line);
    }

    return blocks.filter((b) => b.type === "day" || b.lines.join("").trim() !== "");
}

function renderDay(block) {
    const body = renderMarkdown(block.lines.join("\n"));
    const name = block.title ? `<span class="day-name">${renderInline(block.title)}</span>` : "";

    return `
        <li class="day">
            <div class="day-marker" aria-hidden="true">${esc(block.number)}</div>
            <article class="card day-card">
                <h4 class="day-title"><span class="day-label">${esc(block.label)}</span>${name}</h4>
                ${body ? `<div class="prose">${body}</div>` : ""}
            </article>
        </li>
    `;
}

function renderItinerary(value) {
    const markdown = toMarkdown(value);
    if (!markdown.trim()) return emptyState("No itinerary was returned.");

    const blocks = splitItinerary(markdown);

    // No "Day N" headings found: render the whole itinerary as one formatted card
    if (!blocks.some((b) => b.type === "day")) {
        return `<div class="card prose-card"><div class="prose">${renderMarkdown(markdown)}</div></div>`;
    }

    let html = "";
    let timelineOpen = false;

    for (const block of blocks) {
        if (block.type === "day") {
            if (!timelineOpen) { html += `<ol class="timeline">`; timelineOpen = true; }
            html += renderDay(block);
        } else {
            if (timelineOpen) { html += `</ol>`; timelineOpen = false; }
            html += `<div class="card prose-card"><div class="prose">${renderMarkdown(block.lines.join("\n"))}</div></div>`;
        }
    }
    if (timelineOpen) html += `</ol>`;

    return `<div class="itinerary">${html}</div>`;
}


/* =========================================================
   Result sections
   ========================================================= */

function sectionHead(id, iconName, title, subtitle) {
    return `
        <div class="section-head">
            <span class="section-icon">${icon(iconName)}</span>
            <div>
                <h3 class="section-title" id="${id}-title">${esc(title)}</h3>
                <p class="section-sub">${esc(subtitle)}</p>
            </div>
        </div>
    `;
}

function renderJumpNav() {
    const links = [
        ["overview", "Overview"], ["weather", "Weather"], ["places", "Places"],
        ["hotels", "Hotels"], ["itinerary", "Itinerary"], ["budget", "Budget"], ["plan", "Final plan"],
    ];
    return `
        <nav class="jump-nav" aria-label="Trip sections">
            ${links.map(([id, label]) => `<a href="#section-${id}">${label}</a>`).join("")}
        </nav>
    `;
}

function renderOverview(data) {
    const tone = statusTone(data.budget_status);
    const statusText = isPresent(data.budget_status) ? String(data.budget_status) : "—";
    const destination = isPresent(data.destination) ? data.destination : "Your trip";

    const stat = (iconName, label, value, extra = "") => `
        <div class="stat ${extra}">
            <span class="stat-icon">${icon(iconName)}</span>
            <div class="stat-body">
                <span class="stat-label">${label}</span>
                <span class="stat-value">${value}</span>
            </div>
        </div>
    `;

    return `
        <section class="overview" id="section-overview" aria-labelledby="overview-title">
            <p class="eyebrow">${icon("sparkles")} Trip overview</p>
            <h2 id="overview-title">${esc(destination)}</h2>
            <div class="stat-grid">
                ${stat("calendar", "Duration", esc(formatCount(data.days, "day")))}
                ${stat("users", "Travelers", esc(formatCount(data.travelers, "traveler")))}
                ${stat("wallet", "Total budget", esc(formatMoney(data.budget)))}
                ${stat("trend", "Estimated cost", esc(formatMoney(data.estimated_cost)), "stat--wide")}
                ${stat("check", "Budget status",
                    `<span class="status-pill tone-${tone}">${icon(statusIcon(tone))}${esc(statusText)}</span>`,
                    "stat--wide stat--status")}
            </div>
        </section>
    `;
}

function renderWeather(weather) {
    const body = !weather
        ? emptyState("No weather data was returned.")
        : `<div class="weather-grid">${[
            { label: "Temperature", icon: "thermometer", tone: "warm", value: formatWithUnit(weather.temperature, "°C") },
            { label: "Humidity", icon: "droplets", tone: "cool", value: formatWithUnit(weather.humidity, "%") },
            { label: "Wind speed", icon: "wind", tone: "air", value: formatWithUnit(weather.wind_speed, " km/h") },
        ].map((w) => `
            <div class="card weather-card weather-card--${w.tone}">
                <span class="weather-icon">${icon(w.icon)}</span>
                <div>
                    <span class="weather-value">${esc(w.value)}</span>
                    <span class="weather-label">${w.label}</span>
                </div>
            </div>
        `).join("")}</div>`;

    return `
        <section class="section" id="section-weather" aria-labelledby="weather-title">
            ${sectionHead("weather", "thermometer", "Weather", "Weather data for your destination")}
            ${body}
        </section>
    `;
}

function renderPlaces(places) {
    const body = places.length
        ? `<div class="card-grid">${places.map((entry) => {
            const place = asItem(entry);
            return `
                <article class="card item-card">
                    <span class="item-icon">${icon("pin")}</span>
                    <div class="item-body">
                        <h4 class="item-name">${esc(isPresent(place.name) ? place.name : "Unnamed place")}</h4>
                        ${isPresent(place.rating) ? `<div class="meta"><span class="pill pill--rating">${icon("star")}${esc(place.rating)}</span></div>` : ""}
                        ${isPresent(place.address) ? `<p class="item-address">${icon("pin")}<span>${esc(place.address)}</span></p>` : ""}
                    </div>
                </article>
            `;
        }).join("")}</div>`
        : emptyState("No places were returned for this trip.");

    return `
        <section class="section" id="section-places" aria-labelledby="places-title">
            ${sectionHead("places", "pin", "Places to Visit", "Tourist places suggested for your trip")}
            ${body}
        </section>
    `;
}

function renderHotels(hotels) {
    const body = hotels.length
        ? `<div class="card-grid">${hotels.map((entry) => {
            const hotel = asItem(entry);
            const hasMeta = isPresent(hotel.rating) || isPresent(hotel.price);
            return `
                <article class="card item-card">
                    <span class="item-icon">${icon("bed")}</span>
                    <div class="item-body">
                        <h4 class="item-name">${esc(isPresent(hotel.name) ? hotel.name : "Unnamed hotel")}</h4>
                        ${hasMeta ? `<div class="meta">
                            ${isPresent(hotel.rating) ? `<span class="pill pill--rating">${icon("star")}${esc(hotel.rating)}</span>` : ""}
                            ${isPresent(hotel.price) ? `<span class="pill">${icon("wallet")}${esc(hotel.price)}</span>` : ""}
                        </div>` : ""}
                        ${isPresent(hotel.address) ? `<p class="item-address">${icon("pin")}<span>${esc(hotel.address)}</span></p>` : ""}
                    </div>
                </article>
            `;
        }).join("")}</div>
        <p class="section-note">${icon("info")}<span>Ratings and prices are shown as returned by the planner and may not reflect current availability.</span></p>`
        : emptyState("No hotels were returned for this trip.");

    return `
        <section class="section" id="section-hotels" aria-labelledby="hotels-title">
            ${sectionHead("hotels", "bed", "Hotel Recommendations", "Places to stay suggested for your trip")}
            ${body}
        </section>
    `;
}

function renderItinerarySection(data) {
    return `
        <section class="section" id="section-itinerary" aria-labelledby="itinerary-title">
            ${sectionHead("itinerary", "calendar", "Day-Wise Itinerary", "Your plan, day by day")}
            ${renderItinerary(data.itinerary)}
        </section>
    `;
}

function renderBudget(data) {
    const tone = statusTone(data.budget_status);
    const statusText = isPresent(data.budget_status) ? String(data.budget_status) : "—";
    const budget = toNumber(data.budget);
    const cost = toNumber(data.estimated_cost);

    // The meter only compares the two structured API values; it never edits them
    let meter = "";
    if (Number.isFinite(budget) && Number.isFinite(cost) && budget > 0 && cost >= 0) {
        const pct = Math.round((cost / budget) * 100);
        const caption = `Estimated cost is ${pct}% of your budget`;
        meter = `
            <div class="meter" role="img" aria-label="${esc(caption)}">
                <div class="meter-fill tone-${tone}" style="width:${Math.min(100, pct)}%"></div>
            </div>
            <p class="meter-caption">${esc(caption)}</p>
        `;
    }

    return `
        <section class="section" id="section-budget" aria-labelledby="budget-title">
            ${sectionHead("budget", "wallet", "Budget Summary", "How the planner's estimate compares with your budget")}
            <div class="card budget-panel">
                <div class="figures">
                    <div class="figure">
                        <span class="figure-label">Your budget</span>
                        <span class="figure-value">${esc(formatMoney(data.budget))}</span>
                    </div>
                    <div class="figure">
                        <span class="figure-label">Estimated cost</span>
                        <span class="figure-value">${esc(formatMoney(data.estimated_cost))}</span>
                    </div>
                    <div class="figure figure--status">
                        <span class="figure-label">Budget status</span>
                        <span class="status-pill tone-${tone}">${icon(statusIcon(tone))}${esc(statusText)}</span>
                    </div>
                </div>
                ${meter}
                <p class="section-note">${icon("info")}<span>These figures come from the planner's structured data. Cost estimates mentioned inside the written plan below are the AI's own text and may differ.</span></p>
            </div>
        </section>
    `;
}

function renderFinalPlan(data) {
    const body = renderMarkdown(toMarkdown(data.final_plan));
    return `
        <section class="section" id="section-plan" aria-labelledby="plan-title">
            <article class="card report">
                <div class="report-head">
                    <span class="section-icon">${icon("file")}</span>
                    <div>
                        <span class="report-tag">AI-generated</span>
                        <h3 class="report-title" id="plan-title">Final Travel Plan</h3>
                    </div>
                </div>
                <div class="prose">${body || emptyState("No final plan was returned.")}</div>
            </article>
        </section>
    `;
}

function renderResult(data) {
    const weather = data.weather && typeof data.weather === "object" ? data.weather : null;
    const places = Array.isArray(data.places) ? data.places : [];
    const hotels = Array.isArray(data.hotels) ? data.hotels : [];

    tripResult.innerHTML = [
        renderJumpNav(),
        renderOverview(data),
        renderWeather(weather),
        renderPlaces(places),
        renderHotels(hotels),
        renderItinerarySection(data),
        renderBudget(data),
        renderFinalPlan(data),
    ].join("");
}

function renderError(message) {
    tripResult.innerHTML = `
        <div class="card error-card" role="alert">
            <span class="error-icon">${icon("alert")}</span>
            <div>
                <h3 class="error-title">We couldn't plan this trip</h3>
                <p class="error-text">${esc(message)}</p>
                <button type="button" class="btn btn--secondary" data-action="retry">Try again</button>
            </div>
        </div>
    `;
}


/* =========================================================
   Loading state
   ========================================================= */

function startLoadingUI() {
    isLoading = true;
    submitBtn.disabled = true;
    submitBtn.classList.add("is-loading");
    btnText.textContent = "Planning your trip...";
    tripForm.setAttribute("aria-busy", "true");
    chipButtons.forEach((chip) => { chip.disabled = true; });

    let index = 0;
    loadingMessage.textContent = LOADING_MESSAGES[index];
    loadingNote.hidden = true;
    loading.hidden = false;

    messageTimer = setInterval(() => {
        index = (index + 1) % LOADING_MESSAGES.length;
        loadingMessage.textContent = LOADING_MESSAGES[index];
    }, MESSAGE_INTERVAL_MS);

    slowTimer = setTimeout(() => { loadingNote.hidden = false; }, SLOW_NOTICE_MS);
}

function stopLoadingUI() {
    isLoading = false;
    clearInterval(messageTimer);
    clearTimeout(slowTimer);
    loading.hidden = true;
    submitBtn.disabled = false;
    submitBtn.classList.remove("is-loading");
    btnText.textContent = "Generate Trip";
    tripForm.removeAttribute("aria-busy");
    chipButtons.forEach((chip) => { chip.disabled = false; });
}


/* =========================================================
   Validation
   ========================================================= */

function setFieldError(name, message) {
    const input = fields[name];
    const output = $(`${name}-error`);
    if (message) {
        output.textContent = message;
        output.hidden = false;
        input.setAttribute("aria-invalid", "true");
    } else {
        output.textContent = "";
        output.hidden = true;
        input.removeAttribute("aria-invalid");
    }
}

// Returns the request payload, or null if something is invalid
function validateForm() {
    const destination = fields.destination.value.trim();
    const days = Number(fields.days.value);
    const budget = Number(fields.budget.value);
    const travelers = Number(fields.travelers.value);
    const errors = {};

    if (!destination) errors.destination = "Enter a destination.";
    else if (destination.length < 2) errors.destination = "That destination looks too short.";
    else if (destination.length > 80) errors.destination = "Keep the destination under 80 characters.";

    if (!fields.days.value.trim() || !Number.isInteger(days) || days < LIMITS.days.min || days > LIMITS.days.max) {
        errors.days = `Enter a whole number from ${LIMITS.days.min} to ${LIMITS.days.max}.`;
    }

    if (!fields.budget.value.trim() || !Number.isFinite(budget) || budget < LIMITS.budget.min) {
        errors.budget = "Enter a budget of at least ₹1.";
    }

    if (!fields.travelers.value.trim() || !Number.isInteger(travelers) || travelers < LIMITS.travelers.min || travelers > LIMITS.travelers.max) {
        errors.travelers = `Enter a whole number from ${LIMITS.travelers.min} to ${LIMITS.travelers.max}.`;
    }

    let firstInvalid = null;
    for (const name of Object.keys(fields)) {
        setFieldError(name, errors[name] || "");
        if (errors[name] && !firstInvalid) firstInvalid = fields[name];
    }

    if (firstInvalid) {
        firstInvalid.focus();
        return null;
    }

    return { destination, days, budget, travelers };
}


/* =========================================================
   API
   ========================================================= */

async function readErrorMessage(response) {
    try {
        const body = await response.json();
        const detail = body && body.detail;
        if (typeof detail === "string" && detail.trim()) return detail;
        if (Array.isArray(detail) && detail.length) {
            return detail.map((d) => (d && d.msg) || JSON.stringify(d)).join("; ");
        }
    } catch (ignored) {
        // body was not JSON
    }
    return `The server responded with an error (HTTP ${response.status}).`;
}

function describeError(error) {
    if (error && error.name === "AbortError") {
        return "The request took too long and was cancelled. The server may be waking up, so please try again.";
    }
    if (error instanceof TypeError) {
        return "We couldn't reach the planner service. Check your internet connection and try again.";
    }
    return (error && error.message) || "Something went wrong.";
}

async function planTrip(payload) {
    startLoadingUI();
    tripResult.innerHTML = "";

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });

        if (!response.ok) throw new Error(await readErrorMessage(response));

        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            throw new Error("The server returned a response we couldn't read.");
        }
        if (!data || typeof data !== "object" || Array.isArray(data)) {
            throw new Error("The server returned an unexpected response format.");
        }

        renderResult(data);

        tripResult.focus({ preventScroll: true });
        tripResult.scrollIntoView({
            behavior: prefersReducedMotion() ? "auto" : "smooth",
            block: "start",
        });
    } catch (error) {
        console.error("Trip planning error:", error);
        renderError(describeError(error));
        tripResult.scrollIntoView({ behavior: "auto", block: "nearest" });
    } finally {
        clearTimeout(timeout);
        stopLoadingUI();
    }
}


/* =========================================================
   Events
   ========================================================= */

tripForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (isLoading) return;               // prevent duplicate submissions

    const payload = validateForm();
    if (payload) planTrip(payload);
});

// Clear a field's error as soon as the user edits it
Object.keys(fields).forEach((name) => {
    fields[name].addEventListener("input", () => setFieldError(name, ""));
});

// Destination quick-fill chips
chipButtons.forEach((chip) => {
    chip.addEventListener("click", () => {
        fields.destination.value = chip.dataset.destination;
        setFieldError("destination", "");
        fields.destination.focus();
    });
});

// "Try again" button inside the error card
tripResult.addEventListener("click", (event) => {
    if (event.target.closest("[data-action='retry']") && !isLoading) {
        if (typeof tripForm.requestSubmit === "function") tripForm.requestSubmit();
        else submitBtn.click();
    }
});

configureMarkdown();