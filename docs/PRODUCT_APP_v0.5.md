# UI Polish v0.5 — Premium dark product surface

**Date:** 2026-07-13  
**Inspiration:** Linear-class dark product UI (precision, restrained accent, luminance stacking)

## Changes

- Inter + JetBrains Mono typography with tight display tracking  
- Near-black canvas, glass panels, indigo accent only on CTAs/status  
- Cleaner hierarchy: eyebrows, quieter labels, refined pills/buttons  
- Premium empty state, loading bar, modal Settings, noise/orb atmosphere  
- Sparkline stroke recolored to brand accent  
- All element IDs preserved for existing `app.js`

## Verify

```bash
smf-swarm serve --port 8790
# hard refresh browser
pytest -q
```
