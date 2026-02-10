# Text2trade - Product Requirements Document

## Overview
Text2trade is a minimal MVP scaffold for a trading platform web application.

## Original Problem Statement
Build a basic full-stack web app scaffold called Text2trade with:
- Home page, Login page, Empty Dashboard page
- Backend /health endpoint
- No business logic, no trading logic, no AI features
- Fast and minimal design for trading platform

## Architecture
- **Frontend**: React (CRA with Craco) + TailwindCSS
- **Backend**: FastAPI (Python)
- **Database**: None (placeholder only)
- **Theme**: "Tactical Bloomberg" - Dark mode, high contrast, Signal Green (#00E599) accent

## User Personas
1. **Traders**: Need fast, functional interfaces without distractions
2. **Developers**: Need clean scaffold to build upon

## Core Requirements (Static)
- [x] Home/Landing page with hero section
- [x] Login page (UI mockup, no auth)
- [x] Dashboard page (empty placeholder with grid layout)
- [x] /api/health endpoint
- [x] Dark theme with Signal Green primary color
- [x] JetBrains Mono + Inter typography
- [x] Heavily commented code

## What's Been Implemented
**Date: 2026-02-10**
- Created full scaffold with 3 pages (Home, Login, Dashboard)
- Backend server.py with /api/health and /api/ endpoints
- Tactical Bloomberg dark theme
- Sharp edges (no rounded corners)
- Monospace typography for headings
- All interactive elements have data-testid attributes
- Login form with client-side validation (mockup only)
- Dashboard with stat cards and widget placeholders

## File Structure
```
/app/
├── backend/
│   └── server.py           # FastAPI with /health endpoint
├── frontend/src/
│   ├── App.js              # Main routing
│   ├── pages/
│   │   ├── HomePage.js     # Landing page
│   │   ├── LoginPage.js    # Login mockup
│   │   └── DashboardPage.js # Empty dashboard
│   ├── index.css           # Global styles & CSS vars
│   ├── App.css             # Component animations
│   └── tailwind.config.js  # Theme configuration
└── design_guidelines.json  # Design system specs
```

## Prioritized Backlog

### P0 - Critical (Done)
- [x] Basic scaffold with all 3 pages
- [x] /health endpoint
- [x] Navigation between pages

### P1 - Important (Next Phase)
- [ ] Real authentication (JWT or OAuth)
- [ ] WebSocket connection for real-time data
- [ ] Price chart component
- [ ] Order book component

### P2 - Nice to Have
- [ ] User settings page
- [ ] Dark/Light theme toggle
- [ ] Mobile responsive improvements
- [ ] Trading history table

## Next Tasks
1. Implement authentication (JWT recommended for trading apps)
2. Add real-time WebSocket connection
3. Build price chart widget with mock data
4. Create order entry form
