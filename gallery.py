from __future__ import annotations

import json
from pathlib import Path


def _esc(s: str) -> str:
    s = s or ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_batch_gallery(batch_dir: str, batch_metadata: dict, variants: list[dict]) -> str:
    batch_path = Path(batch_dir)
    cards: list[str] = []

    for v in variants:
        vid = v["variant_id"]
        model = v.get("model", "")
        provider = v.get("provider", "")
        image_rel = v.get("image_rel", "")
        status = v.get("status", "ok")
        compact = v.get("structured_compact", {})
        parts = v.get("prompt_parts", {})

        compact_html = "".join(
            [f"<li><b>{_esc(k)}:</b> {_esc(str(val))}</li>" for k, val in compact.items() if val]
        )
        neg_list = "".join([f"<li>{_esc(x)}</li>" for x in parts.get("negative_constraints", [])])

        image_block = (
            f"<img src=\"{_esc(image_rel)}\" alt=\"variant {vid}\" loading=\"lazy\" />"
            if image_rel
            else f"<div class=\"img-missing\">No image generated<br/><small>{_esc(v.get('error', 'Unknown error'))}</small></div>"
        )

        cards.append(
            f"""
            <article class=\"card\" data-variant=\"{vid}\" data-provider=\"{_esc(provider)}\" data-model=\"{_esc(model)}\" data-ts=\"{_esc(v.get('timestamp',''))}\" data-prompt=\"{_esc(v.get('prompt_full',''))}\" data-image=\"{_esc(image_rel)}\">
              <div class=\"star-badge\" id=\"star-{vid}\" hidden>★</div>
              <div class=\"status {status}\">{_esc(status.upper())}</div>
              {image_block}
              <div class=\"meta\">
                <h3>Variant {vid}</h3>
                <div class=\"diff\">Difference focus: {_esc(v.get('difference_focus',''))}</div>
                <ul class=\"compact\">{compact_html}</ul>
                <p class=\"prov\">{_esc(provider)} / {_esc(model)}</p>

                <details>
                  <summary>Show prompt details</summary>
                  <div class=\"prompt-sections\">
                    <h4>Base prompt</h4>
                    <pre>{_esc(parts.get('base_prompt',''))}</pre>
                    <h4>Variant modifiers</h4>
                    <pre>{_esc(parts.get('variant_modifiers',''))}</pre>
                    <h4>Negative constraints</h4>
                    <ul>{neg_list}</ul>
                    <h4>Model settings</h4>
                    <pre>{_esc(json.dumps(parts.get('model_settings', {}), ensure_ascii=False, indent=2))}</pre>
                  </div>
                </details>

                <div class=\"actions\">
                  <button onclick=\"copyPrompt({vid})\">Copy prompt</button>
                  <button class=\"fav\" onclick=\"toggleFavorite({vid})\">☆ Favorite</button>
                  <button onclick=\"remixVariant({vid})\">Remix this</button>
                  <button onclick=\"editPromptFromVariant({vid})\">Edit prompt</button>
                  <button onclick=\"useAsBaseImage({vid})\">Use as base image</button>
                  <button onclick=\"openVideoPanel({vid})\">Make video</button>
                  <button onclick=\"upscaleVariant({vid})\">Upscale</button>
                  <a class=\"btn\" href=\"{_esc(v.get('metadata_rel',''))}\" target=\"_blank\">View metadata</a>
                  <a class=\"btn\" href=\"{_esc(image_rel)}\" target=\"_blank\">Open image</a>
                </div>

                <details id=\"video-panel-{vid}\" class=\"video-panel\">
                  <summary>Image-to-video workflow</summary>
                  <div class=\"video-grid\">
                    <label>Motion style
                      <select id=\"motion-style-{vid}\">
                        <option>Cinematic push-in</option>
                        <option>Fast chase motion</option>
                        <option>Slow documentary pan</option>
                        <option>Handheld realism</option>
                      </select>
                    </label>
                    <label>Duration
                      <select id=\"duration-{vid}\">
                        <option>3s</option>
                        <option>5s</option>
                        <option>8s</option>
                      </select>
                    </label>
                    <label>Video provider target
                      <select id=\"video-provider-{vid}\">
                        <option>Runway</option>
                        <option>Luma</option>
                        <option>Pika</option>
                        <option>Kling</option>
                      </select>
                    </label>
                  </div>
                  <button onclick=\"buildVideoPrompt({vid})\">Generate video prompt</button>
                  <pre id=\"video-prompt-{vid}\"></pre>
                </details>
              </div>
            </article>
            """.strip()
        )

    models = sorted({v.get("model", "") for v in variants if v.get("model")})
    providers = sorted({v.get("provider", "") for v in variants if v.get("provider")})

    html = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>T-Rex Batch {batch_metadata.get('batch_id','')}</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 20px; background: #0b0d12; color: #e8ecf1; }}
    h1,h2,h3,h4 {{ margin: 0 0 8px; }}

    .studio {{ background:#121826; border:1px solid #273148; border-radius:12px; padding:12px; margin-bottom:14px; }}
    .studio textarea {{ width:100%; min-height:80px; background:#0f1420; color:#e8ecf1; border:1px solid #294063; border-radius:8px; padding:10px; }}
    .studio-controls {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:8px; margin:10px 0; }}
    .studio-controls label {{ font-size:12px; color:#b8c6dd; display:flex; flex-direction:column; gap:4px; }}
    .studio-controls select, .studio-controls input {{ background:#24324a; color:#e8ecf1; border:1px solid #38507a; border-radius:8px; padding:6px 8px; }}
    .row {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }}
    button, .btn {{ background:#24324a; color:#e8ecf1; border:1px solid #38507a; border-radius:8px; padding:6px 10px; cursor:pointer; text-decoration:none; font-size:13px; }}
    button:hover, .btn:hover {{ filter: brightness(1.1); }}
    pre {{ white-space: pre-wrap; background:#0f1420; padding:8px; border-radius:8px; border:1px solid #243149; }}

    .prompt-studio {{ display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px; }}
    .panel {{ background:#101725; border:1px solid #243149; border-radius:10px; padding:10px; }}
    .panel ul {{ margin: 0; padding-left: 18px; }}

    .top {{ display:grid; grid-template-columns: 1fr auto; gap:12px; align-items:start; margin-top:12px; }}
    .summary {{ background:#121826; border:1px solid #273148; border-radius:10px; padding:10px; font-size:13px; color:#b9c6da; }}
    .summary b {{ color:#e8ecf1; }}
    .controls {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    .controls select {{ background:#24324a; color:#e8ecf1; border:1px solid #38507a; border-radius:8px; padding:6px 10px; }}

    .grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; margin-top: 18px; }}
    .card {{ position:relative; background:#141924; border:1px solid #242c3a; border-radius: 12px; overflow: hidden; }}
    .star-badge {{ position:absolute; top:8px; right:8px; background:#f5c34b; color:#2e2203; border-radius:999px; padding:2px 8px; font-weight:700; z-index:3; }}
    .status {{ position:absolute; top:8px; left:8px; border-radius:999px; padding:2px 8px; font-size:11px; font-weight:700; z-index:3; }}
    .status.ok {{ background:#224d33; color:#b6f2c9; }}
    .status.error {{ background:#5a2525; color:#ffc9c9; }}
    img {{ width:100%; height:220px; object-fit:cover; display:block; background:#111; }}
    .img-missing {{ height:220px; display:flex; align-items:center; justify-content:center; text-align:center; color:#d7a9a9; background:#271818; border-bottom:1px solid #3a2020; padding:10px; }}
    .meta {{ padding: 12px; }}
    .diff {{ color:#9fc0ff; font-size:12px; margin: 2px 0 6px; }}
    .compact {{ margin:0 0 6px 0; padding-left: 18px; color:#c2cede; font-size:12px; }}
    .prov {{ color:#8fa1bb; font-size: 12px; margin: 4px 0 8px; }}
    .prompt-sections h4 {{ margin: 10px 0 6px; color:#cfd8e8; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }}
    .fav.active {{ background:#5f4720; border-color:#b99042; }}
    .video-panel {{ margin-top:8px; }}
    .video-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin:8px 0; }}
    .video-grid label {{ font-size:12px; color:#b8c6dd; display:flex; flex-direction:column; gap:4px; }}
    .video-grid select {{ background:#24324a; color:#e8ecf1; border:1px solid #38507a; border-radius:8px; padding:6px; }}
  </style>
</head>
<body>
  <section class=\"studio\">
    <h2>Creation Workspace</h2>
    <textarea id=\"rawIdea\" placeholder=\"A realistic T-Rex running through shallow water like a National Geographic documentary\"></textarea>

    <div class=\"studio-controls\">
      <label>Provider<select id=\"genProvider\"><option>openai</option><option disabled>gemini (coming soon)</option></select></label>
      <label>Model<select id=\"genModel\"><option>gpt-image-1</option><option>gpt-image-1-mini</option><option>gemini-2.5-flash-image</option></select></label>
      <label>Variants<input id=\"genCount\" type=\"number\" value=\"4\" min=\"1\" max=\"8\"/></label>
      <label>Realism<select id=\"realismLevel\"><option>high</option><option>medium</option><option>ultra</option></select></label>
      <label>Style preset<select id=\"stylePreset\"><option>documentary</option><option>cinematic</option><option>studio photo</option></select></label>
      <label>Aspect ratio<select id=\"aspectRatio\"><option>3:2</option><option>16:9</option><option>1:1</option><option>9:16</option></select></label>
    </div>

    <div class=\"row\">
      <button onclick=\"oneClickGenerate()\">Generate</button>
      <button onclick=\"enhancePrompt()\">Preview prompt</button>
      <button onclick=\"copyEnhancedPrompt()\">Copy enhanced prompt</button>
      <button onclick=\"exportSelectedPrompts()\">Export selected prompts</button>
      <button onclick=\"exportBatchMetadata()\">Export batch metadata</button>
      <button onclick=\"exportFavorites()\">Export favorites.json</button>
      <button onclick=\"exportFavoriteBundleManifest()\">Export favorite bundle manifest</button>
    </div>
    <pre id=\"submitHelp\"></pre>
    <div class=\"panel\" style=\"margin-top:10px;\">
      <h4>Run status</h4>
      <pre id=\"runStatus\">Idle.</pre>
      <h4>Job history</h4>
      <pre id=\"jobHistory\">(empty)</pre>
    </div>

    <div class=\"prompt-studio\">
      <div class=\"panel\">
        <h4>Raw user input</h4><pre id=\"studioRaw\"></pre>
        <h4>Structured prompt fields</h4><pre id=\"studioStructured\"></pre>
      </div>
      <div class=\"panel\">
        <h4>Enhanced professional prompt</h4><pre id=\"studioEnhanced\"></pre>
        <h4>Negative constraints</h4><pre id=\"studioNegative\"></pre>
        <h4>Variation plan</h4><pre id=\"studioVariations\"></pre>
      </div>
    </div>
  </section>

  <div class=\"top\">
    <div class=\"summary\">
      <h2>Batch Summary</h2>
      <div><b>Batch:</b> {batch_metadata.get('batch_id','')}</div>
      <div><b>Visible variants:</b> <span id=\"summary-variants\">{len(variants)}</span></div>
      <div><b>Provider:</b> {batch_metadata.get('provider','')}</div>
      <div><b>Model:</b> {batch_metadata.get('model','')}</div>
      <div><b>Output path:</b> {_esc(str(batch_path))}</div>
      <div><b>Favorites:</b> <span id=\"fav-count\">0</span></div>
    </div>
    <div class=\"controls\">
      <select id=\"providerFilter\"><option value=\"\">All providers</option>{''.join([f'<option>{_esc(x)}</option>' for x in providers])}</select>
      <select id=\"modelFilter\"><option value=\"\">All models</option>{''.join([f'<option>{_esc(x)}</option>' for x in models])}</select>
      <select id=\"sortBy\"><option value=\"variant\">Sort: Variant ID</option><option value=\"timestamp\">Sort: Timestamp</option></select>
      <button onclick=\"toggleFavoritesOnly()\" id=\"favOnlyBtn\">Show favorites only: OFF</button>
      <button onclick=\"applyFilters()\">Apply</button>
      <button onclick=\"clearFavorites()\">Clear favorites</button>
    </div>
  </div>

  <section class=\"grid\" id=\"grid\">{''.join(cards)}</section>

  <script>
    const STORAGE_KEY = 'trex_batch_favorites_{batch_metadata.get('batch_id','')}';
    const BATCH_META = {json.dumps(batch_metadata, ensure_ascii=False)};
    let favoritesOnly = false;

    function getFavs() {{
      try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }} catch {{ return []; }}
    }}
    function setFavs(arr) {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
      renderFavs();
      updateSummary();
    }}

    function toggleFavorite(id) {{
      const favs = new Set(getFavs());
      if (favs.has(id)) favs.delete(id); else favs.add(id);
      setFavs(Array.from(favs).sort((a,b)=>a-b));
      applyFilters();
    }}

    function renderFavs() {{
      const favs = new Set(getFavs());
      document.querySelectorAll('.card').forEach(card => {{
        const id = Number(card.dataset.variant);
        const btn = card.querySelector('.fav');
        const star = card.querySelector('.star-badge');
        if (!btn) return;
        if (favs.has(id)) {{
          btn.classList.add('active'); btn.textContent = '★ Favorited';
          if (star) star.hidden = false;
        }} else {{
          btn.classList.remove('active'); btn.textContent = '☆ Favorite';
          if (star) star.hidden = true;
        }}
      }});
    }}

    async function safeCopy(text) {{
      try {{
        await navigator.clipboard.writeText(text || '');
        return true;
      }} catch {{
        window.prompt('Copy manually:', text || '');
        return false;
      }}
    }}

    function showNotice(msg) {{
      const el = document.getElementById('submitHelp');
      if (el) el.textContent = msg;
    }}

    function copyPrompt(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      const prompt = card?.dataset?.prompt || '';
      safeCopy(prompt);
    }}

    function exportFavorites() {{
      const payload = {{ batch_id: BATCH_META.batch_id, favorites: getFavs() }};
      downloadJson(payload, 'favorites.json');
    }}

    function exportBatchMetadata() {{ downloadJson(BATCH_META, 'batch_metadata.json'); }}

    function exportSelectedPrompts() {{
      const favs = new Set(getFavs());
      const prompts = [...document.querySelectorAll('.card')]
        .filter(c => favs.has(Number(c.dataset.variant)))
        .map(c => ({{ variant_id: Number(c.dataset.variant), prompt: c.dataset.prompt || '' }}));
      downloadJson({{ batch_id: BATCH_META.batch_id, prompts }}, 'selected_prompts.json');
    }}

    function exportFavoriteBundleManifest() {{
      const favs = new Set(getFavs());
      const files = [...document.querySelectorAll('.card')]
        .filter(c => favs.has(Number(c.dataset.variant)))
        .map(c => ({{ variant_id: Number(c.dataset.variant), image_rel: c.dataset.image || '' }}));
      downloadJson(
        {{
          note: 'Use this manifest to zip favorited outputs externally (safe fallback without browser FS privileges).',
          batch_id: BATCH_META.batch_id,
          files,
        }},
        'favorite_bundle_manifest.json'
      );
    }}

    function downloadJson(obj, name) {{
      const blob = new Blob([JSON.stringify(obj, null, 2)], {{ type: 'application/json' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
    }}

    function clearFavorites() {{ setFavs([]); applyFilters(); }}

    function toggleFavoritesOnly() {{
      favoritesOnly = !favoritesOnly;
      document.getElementById('favOnlyBtn').textContent = `Show favorites only: ${{favoritesOnly ? 'ON' : 'OFF'}}`;
      applyFilters();
    }}

    function updateSummary() {{
      const favCount = getFavs().length;
      document.getElementById('fav-count').textContent = String(favCount);
      const visible = [...document.querySelectorAll('.card')].filter(c => c.style.display !== 'none').length;
      document.getElementById('summary-variants').textContent = String(visible);
    }}

    function applyFilters() {{
      const pf = document.getElementById('providerFilter').value;
      const mf = document.getElementById('modelFilter').value;
      const favs = new Set(getFavs());
      const cards = [...document.querySelectorAll('.card')];

      cards.forEach(card => {{
        const id = Number(card.dataset.variant);
        const passProvider = !pf || card.dataset.provider === pf;
        const passModel = !mf || card.dataset.model === mf;
        const passFav = !favoritesOnly || favs.has(id);
        card.style.display = (passProvider && passModel && passFav) ? '' : 'none';
      }});

      const sortBy = document.getElementById('sortBy').value;
      const grid = document.getElementById('grid');
      const visibleCards = cards.filter(c => c.style.display !== 'none');
      visibleCards.sort((a,b) => {{
        if (sortBy === 'timestamp') return (a.dataset.ts || '').localeCompare(b.dataset.ts || '');
        return Number(a.dataset.variant) - Number(b.dataset.variant);
      }});
      visibleCards.forEach(c => grid.appendChild(c));
      updateSummary();
    }}

    // Creation workspace
    function parseIdea(raw) {{
      const lower = (raw || '').toLowerCase();
      return {{
        subject: raw || 'T-Rex subject',
        scene: lower.includes('water') ? 'Shallow water with realistic splashes' : 'Natural prehistoric environment',
        style: lower.includes('documentary') ? 'National Geographic documentary realism' : (document.getElementById('stylePreset').value || 'cinematic realism'),
        camera: lower.includes('close') ? 'Close telephoto framing, shallow depth of field' : 'Full-frame DSLR 70mm, dynamic framing',
        lighting: lower.includes('night') ? 'Low-light moonlit atmosphere' : 'Golden hour volumetric light',
        mood: lower.includes('intense') ? 'Intense, urgent, survival energy' : 'Epic, immersive, believable',
        constraints: ['No cartoon look', 'No extra limbs', 'No text', 'No watermark'],
      }};
    }}

    function buildEnhancedPrompt(s) {{
      return [
        s.subject,
        s.scene,
        s.style,
        s.camera,
        s.lighting,
        s.mood,
        `Realism level: ${{document.getElementById('realismLevel').value}}`,
        `Aspect ratio target: ${{document.getElementById('aspectRatio').value}}`,
      ].join(', ');
    }}

    function buildVariationPlan(s) {{
      return [
        'Variant A: stronger water splash and motion blur accents',
        'Variant B: softer sunlight and cooler mist',
        'Variant C: stronger rim light and dramatic contrast',
        'Variant D: ash haze atmosphere and denser particles',
      ];
    }}

    const STUDIO_DRAFT_KEY = `trex_studio_draft_${{BATCH_META.batch_id || 'default'}}`;

    function saveStudioDraft() {{
      const payload = {{
        rawIdea: document.getElementById('rawIdea').value,
        provider: document.getElementById('genProvider').value,
        model: document.getElementById('genModel').value,
        count: document.getElementById('genCount').value,
        realism: document.getElementById('realismLevel').value,
        stylePreset: document.getElementById('stylePreset').value,
        aspectRatio: document.getElementById('aspectRatio').value,
      }};
      localStorage.setItem(STUDIO_DRAFT_KEY, JSON.stringify(payload));
    }}

    function loadStudioDraft() {{
      try {{
        const raw = localStorage.getItem(STUDIO_DRAFT_KEY);
        if (!raw) return;
        const d = JSON.parse(raw);
        if (d.rawIdea != null) document.getElementById('rawIdea').value = d.rawIdea;
        if (d.provider != null) document.getElementById('genProvider').value = d.provider;
        if (d.model != null) document.getElementById('genModel').value = d.model;
        if (d.count != null) document.getElementById('genCount').value = d.count;
        if (d.realism != null) document.getElementById('realismLevel').value = d.realism;
        if (d.stylePreset != null) document.getElementById('stylePreset').value = d.stylePreset;
        if (d.aspectRatio != null) document.getElementById('aspectRatio').value = d.aspectRatio;
      }} catch {{}}
    }}

    function enhancePrompt() {{
      const raw = document.getElementById('rawIdea').value.trim();
      const structured = parseIdea(raw);
      const enhanced = buildEnhancedPrompt(structured);
      const variations = buildVariationPlan(structured);
      document.getElementById('studioRaw').textContent = raw || '(empty)';
      document.getElementById('studioStructured').textContent = JSON.stringify(structured, null, 2);
      document.getElementById('studioEnhanced').textContent = enhanced;
      document.getElementById('studioNegative').textContent = structured.constraints.join(', ');
      document.getElementById('studioVariations').textContent = variations.join('\\\\n');
      saveStudioDraft();
    }}

    function copyEnhancedPrompt() {{
      const txt = document.getElementById('studioEnhanced').textContent || '';
      safeCopy(txt);
    }}

    function buildStudioRequest() {{
      const raw = document.getElementById('rawIdea').value.trim();
      const structured = parseIdea(raw);
      const enhanced = buildEnhancedPrompt(structured);
      const variations = buildVariationPlan(structured);
      const n = Number(document.getElementById('genCount').value || 4);
      const safeN = Math.max(1, Math.min(8, Number.isFinite(n) ? n : 4));
      return {{
        raw_input: raw,
        structured_fields: structured,
        enhanced_prompt: enhanced,
        negative_constraints: structured.constraints,
        variation_plan: variations,
        controls: {{
          provider: document.getElementById('genProvider').value,
          model: document.getElementById('genModel').value,
          num_variants: safeN,
          realism: document.getElementById('realismLevel').value,
          style_preset: document.getElementById('stylePreset').value,
          aspect_ratio: document.getElementById('aspectRatio').value,
        }}
      }};
    }}

    const RUNNER_BASE = 'http://127.0.0.1:8765';
    let activeJobId = null;

    async function fetchJson(url, options = {{}}) {{
      const res = await fetch(url, options);
      const data = await res.json().catch(() => ({{}}));
      if (!res.ok) throw new Error(data.error || `HTTP ${{res.status}}`);
      return data;
    }}

    function setRunStatus(text) {{
      const el = document.getElementById('runStatus');
      if (el) el.textContent = text;
    }}

    function renderJobHistory(items) {{
      const el = document.getElementById('jobHistory');
      if (!el) return;
      if (!items || !items.length) {{
        el.textContent = '(empty)';
        return;
      }}
      const lines = items.slice(0, 12).map(j => {{
        return `${{j.created_at || ''}} | ${{j.job_id}} | ${{j.status}} | code=${{j.exit_code ?? '-'}} | ${{j.batch_folder || ''}}`;
      }});
      el.textContent = lines.join('\\n');
    }}

    async function refreshJobHistory() {{
      try {{
        const d = await fetchJson(`${{RUNNER_BASE}}/api/jobs`);
        renderJobHistory(d.jobs || []);
      }} catch (e) {{
        renderJobHistory([]);
      }}
    }}

    async function pollJob(jobId) {{
      activeJobId = jobId;
      for (;;) {{
        await new Promise(r => setTimeout(r, 1200));
        let job;
        try {{
          const d = await fetchJson(`${{RUNNER_BASE}}/api/jobs/${{jobId}}`);
          job = d.job;
        }} catch (e) {{
          setRunStatus(`Runner error: ${{e.message}}`);
          return;
        }}

        setRunStatus([
          `Job: ${{job.job_id}}`,
          `Status: ${{job.status}}`,
          `Exit code: ${{job.exit_code ?? '-'}}`,
          job.batch_folder ? `Batch: ${{job.batch_folder}}` : '',
          job.stderr_tail ? `Error: ${{job.stderr_tail}}` : '',
        ].filter(Boolean).join('\\n'));

        if (job.status === 'ok' || job.status === 'error') {{
          await refreshJobHistory();
          if (job.status === 'ok' && job.batch_folder) {{
            const target = `file://${{job.batch_folder}}/index.html`;
            window.location.href = target;
          }}
          return;
        }}
      }}
    }}

    async function oneClickGenerate() {{
      const req = buildStudioRequest();
      if (!(req.raw_input || '').trim()) {{
        showNotice('Please enter an idea first before generate.');
        return;
      }}
      if ((req.controls.provider || '').toLowerCase() !== 'openai') {{
        showNotice('Only OpenAI pipeline is implemented right now. Switch provider to openai.');
        return;
      }}

      enhancePrompt();
      setRunStatus('Submitting job...');
      try {{
        const d = await fetchJson(`${{RUNNER_BASE}}/api/run`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(req),
        }});
        showNotice(`Submitted job ${{d.job_id}}. Running locally...`);
        await refreshJobHistory();
        pollJob(d.job_id);
      }} catch (e) {{
        showNotice('Local runner is not reachable. Start it with:\\npython3 "/Users/William/Desktop/image making pipeline/local_runner_server.py"');
        setRunStatus(`Submit failed: ${{e.message}}`);
      }}
    }}

    // Card actions
    function remixVariant(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      const p = card?.dataset?.prompt || '';
      document.getElementById('rawIdea').value = p + ', remix with a fresh composition and micro-detail changes';
      enhancePrompt();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function editPromptFromVariant(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      document.getElementById('rawIdea').value = card?.dataset?.prompt || '';
      enhancePrompt();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function useAsBaseImage(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      const img = card?.dataset?.image || '';
      const raw = document.getElementById('rawIdea');
      raw.value = `${{raw.value}}\nUse as base image: ${{img}}`.trim();
      enhancePrompt();
    }}

    function upscaleVariant(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      const p = card?.dataset?.prompt || '';
      navigator.clipboard.writeText(`Upscale this image with detail preservation and natural texture fidelity. Prompt context: ${{p}}`);
      alert('Upscale instruction copied to clipboard.');
    }}

    function openVideoPanel(id) {{
      const panel = document.getElementById(`video-panel-${{id}}`);
      if (panel) panel.open = true;
    }}

    function buildVideoPrompt(id) {{
      const card = document.querySelector(`.card[data-variant='${{id}}']`);
      const basePrompt = card?.dataset?.prompt || '';
      const motion = document.getElementById(`motion-style-${{id}}`).value;
      const duration = document.getElementById(`duration-${{id}}`).value;
      const provider = document.getElementById(`video-provider-${{id}}`).value;
      const out = document.getElementById(`video-prompt-${{id}}`);
      const text = [
        `Provider target: ${{provider}}`,
        `Duration: ${{duration}}`,
        `Motion style: ${{motion}}`,
        'Video prompt:',
        `${{basePrompt}}, cinematic camera motion (${{motion}}), temporal consistency, realistic motion physics, preserve subject identity, no flicker, no distortion.`,
      ].join('\\n');
      out.textContent = text;
    }}

    renderFavs();
    applyFilters();
    loadStudioDraft();
    enhancePrompt();
  </script>
</body>
</html>
"""

    out = batch_path / "index.html"
    out.write_text(html, encoding="utf-8")
    return str(out)
