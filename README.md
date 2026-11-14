# 🌍 AI-Powered Trip Planner

An AI-powered travel planning web application that generates personalized travel itineraries based on user preferences.

Built using **Python, FastAPI, LangGraph, LangChain, and Groq**, with a responsive frontend developed using HTML, CSS, and JavaScript.

## 🚀 Live Demo

🌐 **Live Website:** https://travel-ai-frontend-cxgq.onrender.com

💻 **GitHub Repository:** https://github.com/UditKataria-UK/travel-ai-fastapi

## ✨ Features

- 🤖 **AI-Powered Itinerary Generation** — Generate personalized day-wise travel plans.
- 🌤️ **Weather Information** — View destination weather information.
- 🏨 **Hotel Recommendations** — Explore recommended hotels for your destination.
- 📍 **Places to Visit** — Discover attractions and sightseeing locations.
- 🗓️ **Day-Wise Trip Planning** — Get organized itineraries based on trip duration.
- 💻 **Responsive User Interface** — Access the application through a modern web interface.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend | FastAPI, Uvicorn |
| AI Framework | LangGraph, LangChain |
| LLM | GPT-OSS 120B via Groq |
| Frontend | HTML, CSS, JavaScript |
| External APIs | SerpAPI, Open-Meteo |
| Deployment | Render |
| Version Control | Git, GitHub |
| Dependency Management | uv |

## 🏗️ System Architecture

```text
User
  |
  v
Frontend (HTML, CSS, JavaScript)
  |
  v
FastAPI Backend
  |
  v
LangGraph AI Workflow
  |
  +----> LLM (Groq)
  |
  +----> Weather Service
  |
  +----> Places & Hotel Services
  |
  v
Personalized Travel Plan
  |
  v
Frontend Results
```

## 📂 Project Structure

```text
weather_tool/
│
├── backend/
│   ├── agents/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── state.py
│   ├── api/
│   │   └── routes.py
│   ├── schemas/
│   │   ├── request.py
│   │   └── response.py
│   ├── services/
│   │   ├── hotels.py
│   │   ├── places.py
│   │   ├── serpapi.py
│   │   └── weather.py
│   ├── utils/
│   │   └── exceptions.py
│   ├── config.py
│   └── main.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .env
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/UditKataria-UK/travel-ai-fastapi.git
cd travel-ai-fastapi
```

### 2. Install Dependencies

Make sure Python and `uv` are installed.

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
OMNIROUTE_API_KEY=your_api_key
OMNIROUTE_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=openai/gpt-oss-120b

SERPAPI_API_KEY=your_serpapi_key

ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

For direct Groq access, use a valid Groq API key as `OMNIROUTE_API_KEY`. Alternatively, configure an accessible OmniRoute endpoint with its corresponding key and model name.

Never commit your `.env` file or expose API keys.

### 4. Start the Backend

```bash
uv run uvicorn backend.main:app --reload
```

Backend API:

http://127.0.0.1:8000

API Documentation:

http://127.0.0.1:8000/docs

### 5. Start the Frontend

Open another terminal:

```bash
cd frontend
python3 -m http.server 5500
```

Open:

http://localhost:5500

The frontend's API URL in `script.js` must point to the backend you want to use.

## ☁️ Deployment

The application is deployed on **Render** using two services:

- **Backend:** FastAPI Web Service
- **Frontend:** Static Site

Backend URL: https://travel-ai-fastapi.onrender.com

Frontend URL: https://travel-ai-frontend-cxgq.onrender.com

## 📸 Screenshots

Screenshots of the homepage, generated itineraries, weather information, and hotel recommendations will be added here.

## 🔮 Future Improvements

- Interactive maps and route visualization
- User authentication and saved itineraries
- Additional travel customization options
- Exporting travel plans as PDF
- Enhanced hotel and destination filtering

## 👨‍💻 Author

**Udit Kataria**

GitHub: https://github.com/UditKataria-UK

---

⭐ If you find this project useful, consider starring the repository!