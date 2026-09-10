# Audio STT architecture

The backend is organized around three boundaries:

- `application/`: use cases and orchestration (`SessionManager`, mic testing).
- `infrastructure/`: device I/O, Faster-Whisper, and persistence adapters.
- `interfaces/`: HTTP and WebSocket delivery (currently hosted by `main.py`).

The current adapter modules re-export the stable implementations from `app/`.
This deliberate compatibility step lets us migrate one component at a time
without breaking the existing API or scripts. New code should import audio,
STT, and storage through `app.infrastructure.*`.

```text
interfaces (HTTP/WebSocket)
          ↓
application (session / mic-test use cases)
          ↓
infrastructure (audio router, VAD, Whisper, storage)
```

The next migration can move the implementation files behind these boundaries,
then introduce explicit protocols for audio capture, transcription, and event
publishing. That will allow CPU/GPU Whisper, alternate STT engines, and a Go API
gateway to be added without changing the application layer.
