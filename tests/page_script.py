"""Run the served page's own script, so the browser seam is covered by tests.

Three regressions reached a release through this seam. Each was a template that
read something the server does not send, or called something that was not in
scope, and every one of them passed a test suite that only read the template as
text. Static checks cannot catch a ReferenceError; only running the script can.

The script is taken from the page the server actually serves, never from a copy,
and it runs against a real response from a real endpoint. What is stubbed here
is only the browser: a small DOM that records what the script writes into it.

Node is used because it is the one JavaScript engine already present wherever
this is developed. Where it is absent the tests using this helper skip rather
than fail, so the suite stays runnable without it.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEMPLATE_PATH = (
    Path(__file__).parent.parent
    / "src/aether/presentation/web/templates/index.html"
)

#: Enough of a document for the page script to load and render into. Every
#: element is created on demand and remembers what was assigned to it, so the
#: assertions read the same properties the browser would have set.
_HARNESS = """
const nodes = new Map();
function el(sel) {
  if (!nodes.has(sel)) {
    const node = {
    sel, textContent: '', _html: '', disabled: false, dataset: {},
    value: '',
    classList: { _s: new Set(), add(c){this._s.add(c);}, remove(c){this._s.delete(c);},
                 toggle(c,f){ f ? this._s.add(c) : this._s.delete(c); },
                 contains(c){ return this._s.has(c); } },
    scrollIntoView(){}, setAttribute(k,v){ this[k] = v; }, getAttribute(k){ return this[k] ?? null; },
    addEventListener(t,h){ (this._h ||= {})[t] = h; },
    appendChild(){}, remove(){},
    };
    // A <select> exposes the options its markup declares, which is what the
    // page reads to tell "nothing to compare against" from "nothing chosen".
    Object.defineProperty(node, 'innerHTML', {
      get(){ return this._html; },
      set(v){ this._html = v; this.options = [...String(v).matchAll(/<option value="([^"]*)"/g)].map((m) => ({ value: m[1] })); },
    });
    node.innerHTML = '';
    nodes.set(sel, node);
  }
  return nodes.get(sel);
}
globalThis.document = {
  querySelector: el,
  querySelectorAll: () => [],
  documentElement: el('html'),
  addEventListener(){},
};
globalThis.window = globalThis;
// Node supplies its own read-only navigator, so this one is defined over it.
Object.defineProperty(globalThis, 'navigator', {
  value: { language: LANGUAGE, languages: [LANGUAGE] }, configurable: true,
});
globalThis.localStorage = {
  _v: STORED,
  getItem(k){ return this._v[k] ?? null; },
  setItem(k,v){ this._v[k] = String(v); },
};
globalThis.fetch = async () => ({ ok: true, json: async () => ({ publishers: PUBLISHERS }) });

SCRIPT

RENDER

const out = {};
for (const [sel, node] of nodes) out[sel] = { html: node.innerHTML, text: node.textContent };
console.log(JSON.stringify(out));
"""


def node_available() -> bool:
    return shutil.which("node") is not None


def run_page_script(
    render: str, language: str = "en-GB", stored=None, publishers=()
) -> dict:
    """Execute the served page's script, then ``render``, and report the DOM.

    ``render`` is JavaScript run after the page has loaded, calling into the
    page's own functions. The result maps each selector the script touched to
    the text and markup left in it.
    """
    if not node_available():
        raise unittest.SkipTest("node is not installed")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    script = re.search(r"<script>([\s\S]*?)</script>", template).group(1)
    harness = (
        _HARNESS.replace("SCRIPT", script)
        .replace("RENDER", render)
        .replace("LANGUAGE", json.dumps(language))
        .replace("STORED", json.dumps(stored or {}))
        .replace("PUBLISHERS", json.dumps(list(publishers)))
    )

    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(harness)
        path = handle.name
    try:
        result = subprocess.run(
            ["node", path], capture_output=True, text=True, timeout=30
        )
    finally:
        Path(path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise AssertionError(f"the served page script failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout.strip().splitlines()[-1])
