# Reliability TODO

## Done in this iteration
- [x] Centralized logging (`logging_config.py`) with console + rotating file logs (`logs/app.log`).
- [x] WB client diagnostics counters (requests/errors/status codes/last error).
- [x] Health checks via `GET /ping` for key WB domains from `docs/swagger/01-general.yaml`.
- [x] Dashboard button `API Diagnostics` to run health checks and show diagnostics summary.
- [x] CLI command `health`/`????????`/`???????????` in `main.py`.
- [x] More reliable dashboard startup via `.venv` in `run_dashboard.bat`.

## Next high-value steps
- [ ] Add structured JSON logs option for production log collectors.
- [ ] Add alerting rules (error-rate threshold, repeated 429/5xx).
- [ ] Add background heartbeat task storing periodic health snapshots.
- [ ] Add smoke test in CI for dashboard import/startup path.
- [ ] Add secret scanning + dependency vulnerability scan in CI.
- [ ] Add retry jitter and circuit-breaker for degraded WB endpoints.
