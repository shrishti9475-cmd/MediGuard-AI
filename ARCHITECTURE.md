#  System Architecture & Data Flow

This document provides a technical overview of how the **Personal Healthcare Monitor** operates, detailing the data flow, AI integration, and database schema.

## 1. Application Data Flow

The system is designed for seamless interaction between the user interface, the AI processing layer, and the local database:

1. **User Input:** The user interacts with the app via the Streamlit frontend (sending chat messages, uploading images/PDFs).
2. **AI Processing Layer (Groq API):** * The input is routed to the `agent.py` module.
   * Based on the selected persona (Medical, Arav, etc.), a strict system prompt is applied to ensure the AI stays within the healthcare/wellness domain.
   * For medical reports, PyMuPDF and Markdown extract the text, which is then analyzed by the Llama-3.3 model.
3. **Intent Classification & Tagging (The Secret Logging):** * If the user mentions taking medicine or completing a fitness activity, the AI is prompted to append a hidden regex tag to its response (e.g., `[LOG_MED: Disprin, 10 AM]` or `[LOG_FITNESS: Running, 30]`).
4. **Data Parsing:** The Streamlit app runs a Regex parser on the AI's output to intercept these tags before they are displayed to the user.
5. **Database Storage:** Extracted data points are securely pushed to `health.db` (SQLite) via `database.py`.
6. **UI Real-Time Update:** The sidebar and analytics charts automatically query the latest database rows and re-render the visual components.

---

## 2. Database Schema (SQLite)

The system uses a lightweight, serverless relational database (`health.db`) initialized automatically on startup.

### Table: `medications`
* `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
* `name` (TEXT) - Name of the medicine (extracted from AI tag)
* `time` (TEXT) - Scheduled or taken time

### Table: `fitness_logs`
* `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
* `activity` (TEXT) - Type of workout
* `duration` (TEXT) - Duration in minutes
* `date_logged` (TIMESTAMP) - Automatically generated timestamp

---

## 3. Security, Guardrails & Privacy

* **Environment Secrets Management:** API keys (Groq) are strictly isolated from the codebase and managed securely via Streamlit Cloud Secrets.
* **Transient Cloud Storage (MVP Phase):** For this deployment, the SQLite database is stored locally within the Streamlit container. When the instance sleeps, the data resets, ensuring user health data is not permanently exposed on a public server.
* **Strict AI Guardrails:** The Llama-3.3 model is hard-prompted to refuse out-of-domain queries (e.g., politics, coding, violence) using a fixed fallback mechanism. It acts as an empathetic assistant while maintaining a strict boundary for irrelevant content.
