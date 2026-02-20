<div align="center">

# **BangaloreNow**

**Your city, unfiltered.**

Bangalore is fragmented — events scattered across private platforms, closed ecosystems, and walled ticketing apps. There is no single, transparent, open source of truth.

BangaloreNow changes that.

🔗 **[bangalore-now-ospi-26.vercel.app](https://bangalore-now-ospi-26.vercel.app)**

</div>

---

## What Is BangaloreNow?

BangaloreNow is a full-stack civic data platform that aggregates, cleans, geocodes, and exposes Bangalore's event data as open, structured intelligence. Not another blog. Not another walled app. Infrastructure — built for the city, owned by the city.

The platform collects events from multiple sources, normalizes inconsistent data, deduplicates cross-platform listings, and surfaces everything through a filterable API and an interactive map frontend.

---

## 🏗️ Architecture

The system follows a structured ETL-driven pipeline:

**Data Sources** — district.in / Zomato, allevents.in, eventbrite.com

**Pipeline** — Cleaning & normalization → schema consolidation → Google Maps Geocoding (address → lat/lng) → cross-source deduplication → Supabase upsert

**Storage** — PostgreSQL (Supabase), indexed for spatial and filtered queries

**Backend** — FastAPI + SQLAlchemy ORM with filtering, pagination, sorting, and Haversine-based distance calculation

**Frontend** — React (Vite) + OpenStreetMap via Leaflet with dynamic markers, search panel, and responsive UI

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Leaflet (OpenStreetMap), Radix UI |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL via Supabase |
| External APIs | Google Maps Geocoding API |

---

## 👥 Contributors

| | |
|---|---|
| **Siddarth** | [github.com/SiddarthAA](https://github.com/SiddarthAA) |
| **Kushal** | [github.com/KBG05](https://github.com/KBG05) |
| **Raunak Bagaria** | [github.com/raunak-bagaria](https://github.com/raunak-bagaria) |
| **Gagana** | [github.com/GAGANA-P05](https://github.com/GAGANA-P05) |
| **Kaushik** | [github.com/kaushik-dwarakanath](https://github.com/kaushik-dwarakanath) |
| **SaiRishi** | [github.com/sairishigangarapu](https://github.com/sairishigangarapu) |
| **Lalith** | [github.com/lalithbseervi](https://github.com/lalithbseervi) |
| **Harsh Pandya** | [github.com/Seaweed-Boi](https://github.com/Seaweed-Boi) |

---

## 📖 Open Data

This project and its data are licensed under the **Open Data Commons Open Database License (ODbL) v1.0.**

The data will always remain free and open. You can use it, remix it, and build on top of it — but if you build on it, you must give back. The commons cannot be privatized.

---

<div align="center">

## Know your city. Own your city. Build its future.
🔗 **[bangalore-now-ospi-26.vercel.app](https://bangalore-now-ospi-26.vercel.app)**

</div>