# Security and privacy notes

- `server.py` binds only to `127.0.0.1` by default.
- The application is self-contained and does not load remote JavaScript or CSS.
- User text is rendered without executing imported HTML.
- Imported JSON is validated and subject to object-count limits.
- The map file is selected locally and is not uploaded by the bundled server.
- Location access is requested by the browser only after the user presses GPS.
- Do not publish exported JSON files containing personal notes or calibration coordinates.
- Do not expose the server by changing the bind address to `0.0.0.0` unless you understand the local-network risks.

Security reports should include the application version from `VERSION`, Android version, browser version, and exact reproduction steps.
