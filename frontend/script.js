const tripForm = document.getElementById("tripForm");
const loading = document.getElementById("loading");
const tripResult = document.getElementById("tripResult");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");

// Hide loading initially
loading.style.display = "none";


// ============================================================
// HELPERS (presentation only - they never change the data)
// ============================================================

// Escape text so API content is shown safely inside HTML
function esc(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// Show itinerary lines that start with "Day X" as headings
function formatItinerary(text) {
    return String(text ?? "")
        .split("\n")
        .map(line => {
            const clean = line.replace(/^#+\s*/, "").replace(/\*\*/g, "").trim();
            if (/^day\s*\d+/i.test(clean)) {
                return `<div class="day-heading">${esc(clean)}</div>`;
            }
            return esc(line) + "\n";
        })
        .join("");
}

// Pick a badge colour from the status text
function statusClass(status) {
    const s = String(status || "").toLowerCase();
    if (s.includes("over") || s.includes("exceed") || s.includes("above")) return "over";
    if (s.includes("within") || s.includes("under") || s.includes("good") || s.includes("ok")) return "good";
    return "";
}

function setButtonLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.classList.toggle("is-loading", isLoading);
    btnText.textContent = isLoading ? "Planning your trip..." : "✦ Generate My Trip";
}


// ============================================================
// FORM SUBMIT
// ============================================================

tripForm.addEventListener("submit", async function (event) {

    event.preventDefault();


    // GET USER INPUT
    const destination = document.getElementById("destination").value.trim();
    const days = Number(document.getElementById("days").value);
    const budget = Number(document.getElementById("budget").value);
    const travelers = Number(document.getElementById("travelers").value);


    // BASIC VALIDATION
    if (!destination || days <= 0 || budget <= 0 || travelers <= 0) {

        tripResult.innerHTML = `
            <div class="error">
                <strong>❌ Invalid input</strong>
                <p>Please enter valid trip details.</p>
            </div>
        `;

        return;
    }


    // SHOW LOADING
    loading.style.display = "block";

    loading.innerHTML = `
        <h3>✦ AI is planning your trip</h3>
        <p>Finding places, hotels, weather and building your itinerary...</p>
        <div class="loading-bars"><span></span><span></span><span></span></div>
    `;

    tripResult.innerHTML = "";
    setButtonLoading(true);


    // API REQUEST
    try {

        const response = await fetch(
            "https://travel-ai-fastapi.onrender.com/plan-trip",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    destination: destination,
                    days: days,
                    budget: budget,
                    travelers: travelers
                })
            }
        );


        // HANDLE HTTP ERRORS
        if (!response.ok) {

            let errorMessage = "Something went wrong.";

            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (jsonError) {
                console.log("Could not read error response.");
            }

            throw new Error(errorMessage);
        }


        // GET JSON RESPONSE
        const data = await response.json();

        console.log("Trip Planner Response:", data);

        const weather = data.weather;


        // PLACES HTML
        let placesHTML = "";

        if (data.places && data.places.length > 0) {

            placesHTML = data.places.map(place => `
                <div class="card item-card">
                    <h4>📍 ${esc(place.name || "Unknown place")}</h4>
                    ${place.rating ? `<div class="meta"><span class="pill">⭐ ${esc(place.rating)}</span></div>` : ""}
                    ${place.address ? `<div class="address">${esc(place.address)}</div>` : ""}
                </div>
            `).join("");

        } else {
            placesHTML = `<div class="card empty">No places found.</div>`;
        }


        // HOTELS HTML
        let hotelsHTML = "";

        if (data.hotels && data.hotels.length > 0) {

            hotelsHTML = data.hotels.map(hotel => `
                <div class="card item-card">
                    <h4>🏨 ${esc(hotel.name || "Unknown hotel")}</h4>
                    <div class="meta">
                        ${hotel.rating ? `<span class="pill">⭐ ${esc(hotel.rating)}</span>` : ""}
                        ${hotel.price ? `<span class="pill">💰 ${esc(hotel.price)}</span>` : ""}
                    </div>
                    ${hotel.address ? `<div class="address">📍 ${esc(hotel.address)}</div>` : ""}
                </div>
            `).join("");

        } else {
            hotelsHTML = `<div class="card empty">No hotels found.</div>`;
        }


        // FINAL RESULT
        tripResult.innerHTML = `

            <!-- TRIP OVERVIEW -->
            <section class="card overview">
                <h2>${esc(data.destination)}</h2>
                <div class="stats">
                    <div class="stat"><small>Days</small><strong>${esc(data.days)}</strong></div>
                    <div class="stat"><small>Travelers</small><strong>${esc(data.travelers)}</strong></div>
                    <div class="stat"><small>Budget</small><strong>₹${esc(data.budget)}</strong></div>
                </div>
            </section>

            <!-- WEATHER -->
            <section>
                <h3 class="section-title">🌤 Weather</h3>
                <div class="weather-grid">
                    <div class="card weather-card">
                        <div class="w-icon">🌡</div>
                        <div class="w-value">${esc(weather.temperature)}°C</div>
                        <div class="w-label">Temperature</div>
                    </div>
                    <div class="card weather-card">
                        <div class="w-icon">💧</div>
                        <div class="w-value">${esc(weather.humidity)}%</div>
                        <div class="w-label">Humidity</div>
                    </div>
                    <div class="card weather-card">
                        <div class="w-icon">💨</div>
                        <div class="w-value">${esc(weather.wind_speed)} km/h</div>
                        <div class="w-label">Wind Speed</div>
                    </div>
                </div>
            </section>

            <!-- PLACES -->
            <section>
                <h3 class="section-title">📍 Places to Visit</h3>
                <div class="grid">${placesHTML}</div>
            </section>

            <!-- HOTELS -->
            <section>
                <h3 class="section-title">🏨 Recommended Hotels</h3>
                <div class="grid">${hotelsHTML}</div>
            </section>

            <!-- ITINERARY -->
            <section>
                <h3 class="section-title">🗓 Itinerary</h3>
                <div class="card text-card">
                    <div class="rich-text itinerary-text">${formatItinerary(data.itinerary)}</div>
                </div>
            </section>

            <!-- BUDGET -->
            <section>
                <h3 class="section-title">💰 Budget</h3>
                <div class="card budget-card">
                    <div>
                        <small>Estimated Cost</small>
                        <div class="cost">₹${esc(data.estimated_cost)}</div>
                    </div>
                    <div>
                        <small>Budget Status</small><br>
                        <span class="status ${statusClass(data.budget_status)}">${esc(data.budget_status)}</span>
                    </div>
                </div>
            </section>

            <!-- FINAL AI PLAN -->
            <section class="card final-card">
                <div class="tag">✦ AI GENERATED TRIP PLAN</div>
                <h3>Final AI Trip Plan</h3>
                <div class="rich-text">${esc(data.final_plan)}</div>
            </section>
        `;

    }


    // ERROR HANDLING
    catch (error) {

        console.error("Trip planning error:", error);

        tripResult.innerHTML = `
            <div class="error">
                <strong>❌ Unable to plan the trip</strong>
                <p>${esc(error.message)}</p>
                <p>Please try again.</p>
            </div>
        `;

    }


    // ALWAYS HIDE LOADING
    finally {

        loading.style.display = "none";
        setButtonLoading(false);

    }

});