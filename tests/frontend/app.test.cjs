const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const {test} = require("node:test");
const vm = require("node:vm");

const html = readFileSync(join(__dirname, "../../app/index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const OPTIONS = {
  sector: ["botanica", "centru"], author: ["persoană fizică"],
  building_fund: ["secundar"], condition: ["necunoscut"]
};
const PREDICTION = {
  fair_price: 600, listed_price: null,
  drivers: [{feature: "Furnished", effect: "raises price"}]
};
const json = (value, status = 200) => new Response(JSON.stringify(value), {status});
const flush = () => new Promise(setImmediate);
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
};

// A narrow DOM test double exercises the served script offline. HTML-writing APIs
// fail immediately. Real-browser smoke checks separately verify DOM/layout behavior.
class Element {
  constructor(tagName, attributes = {}) {
    this.tagName = tagName.toUpperCase();
    this.attributes = new Map(Object.entries(attributes));
    this.id = attributes.id || "";
    this.value = attributes.value || "";
    this.checked = Object.hasOwn(attributes, "checked");
    this.disabled = Object.hasOwn(attributes, "disabled");
    this.hidden = Object.hasOwn(attributes, "hidden");
    this.children = [];
    this.listeners = {};
    this.className = "";
    this.text = "";
  }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
  set innerHTML(_) { assert.fail("Response content must not enter an HTML-writing API"); }
  set outerHTML(_) { assert.fail("Response content must not enter an HTML-writing API"); }
  insertAdjacentHTML() { assert.fail("Response content must not enter an HTML-writing API"); }
  appendChild(child) {
    assert.ok(child instanceof Element);
    if (this.tagName === "SELECT" && this.children.length === 0) this.value = child.value;
    this.children.push(child);
    return child;
  }
  replaceChildren(...children) {
    this.text = "";
    this.children = [];
    children.forEach(child => this.appendChild(child));
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  scrollIntoView() {}
}

function descendants(root) {
  return [root, ...root.children.flatMap(descendants)];
}

function boot({options = () => json(OPTIONS), predict = () => json(PREDICTION)} = {}) {
  const elements = new Map();
  for (const match of html.matchAll(/<(input|select|button|form|div)\b[^>]*\bid="[^"]+"[^>]*>/g)) {
    const attributes = Object.fromEntries([...match[0].matchAll(/\s([\w-]+)(?:="([^"]*)")?/g)]
      .map(([, name, value]) => [name, value ?? ""]));
    elements.set(attributes.id, new Element(match[1], attributes));
  }
  const document = {
    createElement: tag => new Element(tag),
    getElementById: id => elements.get(id) ||
      descendants(elements.get("result")).find(element => element.id === id) || null
  };
  const requests = [];
  const context = vm.createContext({document, fetch: async (url, init) => {
    requests.push({url, init});
    if (url === "/options") return options();
    assert.equal(url, "/predict", "No incidental network access is permitted");
    return predict(init);
  }});
  vm.runInContext(script, context, {filename: "app/index.html:inline-script"});
  return {
    context, requests, get: document.getElementById,
    submit: () => elements.get("form").listeners.submit({preventDefault() {}}),
    result: elements.get("result"), button: elements.get("submitBtn")
  };
}

test("options gate submission and preserve raw values, labels and default sector", async () => {
  const pending = deferred();
  const app = boot({options: () => pending.promise});
  assert.equal(app.button.disabled, true);
  await app.submit();
  assert.deepEqual(app.requests.map(request => request.url), ["/options"]);
  pending.resolve(json(OPTIONS));
  await flush();
  assert.equal(app.button.disabled, false);
  assert.equal(app.get("sector").value, "centru");
  assert.equal(app.get("author").value, "persoană fizică");
  assert.equal(app.get("author").textContent, "Owner (private person)");
  assert.equal(app.result.hidden, true);
});

for (const [name, options] of [
  ["HTTP failure", () => new Response("private trace", {status: 503})],
  ["network failure", () => { throw new TypeError("private network trace"); }],
  ["invalid JSON", () => new Response("<html>private proxy trace</html>")],
  ["missing category", () => json({sector: ["centru"]})],
  ["empty category", () => json({...OPTIONS, author: []})],
  ["invalid option type", () => json({...OPTIONS, condition: [42]})]
]) {
  test(`options ${name} stays disabled and explains recovery`, async () => {
    const app = boot({options});
    await flush();
    assert.equal(app.button.disabled, true);
    assert.equal(app.button.textContent, "Options unavailable");
    assert.equal(app.result.hidden, false);
    assert.match(app.result.textContent, /options could not be loaded.*Refresh the page/);
    assert.doesNotMatch(app.result.textContent, /private/);
    assert.equal(app.get("sector").children.length, 0);
    await app.submit();
    assert.equal(app.requests.length, 1);
  });
}

test("prediction without asking rent keeps price and drivers without a verdict", async () => {
  const app = boot();
  await flush();
  app.get("price").value = "";
  await app.submit();
  assert.equal(app.result.hidden, false);
  assert.match(app.result.textContent, /€600.*Furnished.*raises rent/);
  assert.equal(descendants(app.result).filter(node => node.className.startsWith("badge")).length, 0);
  const request = app.requests.find(request => request.url === "/predict");
  assert.equal(request.init.method, "POST");
  assert.equal(request.init.headers["Content-Type"], "application/json");
  const body = JSON.parse(request.init.body);
  assert.equal(body.price, null);
  assert.equal(body.kitchen_area, null);
  assert.equal(body.ceiling_height, null);
  assert.equal(body.rooms, 2);
  assert.equal(body.furnished, 1);
  assert.equal(body.author, "persoană fizică");
});

for (const [verdict, deviation, label, comparison] of [
  ["overpriced", 20, "Overpriced", /20% above/],
  ["good deal", -20, "Good deal", /20% below/],
  ["fair price", 0.1, "Fair price", /Right on the market rate/]
]) {
  test(`valid ${verdict} preserves the verdict and deviation`, async () => {
    const app = boot({predict: () => json({...PREDICTION, verdict, deviation_pct: deviation})});
    await flush();
    await app.submit();
    assert.match(app.result.textContent, comparison);
    assert.ok(descendants(app.result).some(node => node.textContent === label));
    assert.equal(app.button.disabled, false);
  });
}

test("driver and dropdown labels remain literal text, including prototype-like names", async () => {
  const hostile = '<img src=x onerror="globalThis.injected=true">';
  const app = boot({
    options: () => json({...OPTIONS, condition: [hostile, "__proto__", "constructor"]}),
    predict: () => json({...PREDICTION, drivers: [{feature: hostile, effect: "lowers price"}]})
  });
  await flush();
  assert.ok(app.get("condition").textContent.includes("<Img"));
  assert.doesNotMatch(app.get("condition").textContent, /function Object/);
  await app.submit();
  assert.ok(app.result.textContent.includes(hostile));
  assert.match(app.result.textContent, /lowers rent/);
  assert.equal(descendants(app.result).some(node => node.tagName === "IMG"), false);
  assert.equal(app.context.injected, undefined);
});

test("422 shows recognized field messages as text and associates controls", async () => {
  const hostile = "<b>Floor must not exceed floors in building</b>";
  const app = boot({predict: () => json({detail: [
    {loc: ["body", "floor"], msg: hostile, input: "private input", ctx: {secret: "private context"}},
    {loc: ["body", "floor"], msg: "duplicate message"},
    {loc: ["body", "unrecognized"], msg: "private unknown field"},
    {loc: ["body", "__proto__"], msg: "private prototype field"}
  ]}, 422)});
  await flush();
  await app.submit();
  assert.ok(app.result.textContent.includes(`Floor: ${hostile}`));
  assert.doesNotMatch(app.result.textContent, /private|duplicate message|server running|Estimated fair rent/);
  assert.equal(app.get("floor").getAttribute("aria-invalid"), "true");
  assert.equal(app.get("floor").getAttribute("aria-describedby"), "error-floor");
  assert.equal(app.get("error-floor").tagName, "LI");
  assert.equal(descendants(app.result).filter(node => node.tagName === "LI").length, 1);
  assert.equal(app.button.disabled, false);
});

for (const payload of [null, {detail: "private detail"}, {detail: [null, {loc: ["body", 0], msg: "private"}]}]) {
  test(`unusable 422 details use a safe validation summary: ${JSON.stringify(payload)}`, async () => {
    const app = boot({predict: () => json(payload, 422)});
    await flush();
    await app.submit();
    assert.match(app.result.textContent, /Please check the apartment details/);
    assert.doesNotMatch(app.result.textContent, /private|Estimated fair rent/);
  });
}

for (const [name, predict, message] of [
  ["500 JSON", () => json({detail: "private traceback"}, 500), /service could not complete/],
  ["503 HTML", () => new Response("private proxy trace", {status: 503}), /service could not complete/],
  ["400 response", () => json({detail: "private detail"}, 400), /service could not complete/],
  ["error with success-shaped body", () => json(PREDICTION, 500), /service could not complete/],
  ["network rejection", () => { throw new TypeError("private transport trace"); }, /Could not reach/],
  ["200 HTML", () => new Response("<html>private proxy trace</html>"), /unexpected response/],
  ["empty 200", () => new Response(""), /unexpected response/]
]) {
  test(`${name} does not enter success rendering and restores the button`, async () => {
    const app = boot({predict});
    await flush();
    await app.submit();
    assert.match(app.result.textContent, message);
    assert.doesNotMatch(app.result.textContent, /private|Estimated fair rent|Please check the apartment/);
    assert.equal(app.button.disabled, false);
    assert.equal(app.button.textContent, "Estimate fair rent");
  });
}

for (const [name, value] of [
  ["null payload", null], ["array payload", []], ["missing price", {}],
  ["string price", {...PREDICTION, fair_price: "invalid"}],
  ["zero price", {...PREDICTION, fair_price: 0}],
  ["negative price", {...PREDICTION, fair_price: -5}],
  ["nonfinite price", {...PREDICTION, fair_price: Infinity}],
  ["invalid drivers", {...PREDICTION, drivers: "text"}],
  ["invalid driver label", {...PREDICTION, drivers: [{feature: {}, effect: "raises price"}]}],
  ["unknown effect", {...PREDICTION, drivers: [{feature: "Location", effect: "unknown"}]}],
  ["unknown verdict", {...PREDICTION, verdict: "__proto__", deviation_pct: 0}],
  ["missing deviation", {...PREDICTION, verdict: "overpriced"}],
  ["invalid deviation", {...PREDICTION, verdict: "overpriced", deviation_pct: "20"}]
]) {
  test(`malformed success (${name}) is rejected before rendering`, async () => {
    const app = boot({predict: () => json(value)});
    await flush();
    await app.submit();
    assert.match(app.result.textContent, /unexpected response/);
    assert.doesNotMatch(app.result.textContent, /Estimated fair rent/);
  });
}

test("JSON numeric overflow is rejected, while unused extra fields remain compatible", async () => {
  const app = boot({predict: () => new Response('{"fair_price":1e999,"drivers":[]}')});
  await flush();
  await app.submit();
  assert.match(app.result.textContent, /unexpected response/);
  const parsed = app.context.parsePrediction({fair_price: 600, future_metadata: {version: 2}});
  assert.equal(parsed.fair_price, 600);
  assert.equal(parsed.drivers.length, 0);
});

test("errors and old estimates clear during a new request; duplicates are blocked and recovery works", async () => {
  const pending = deferred();
  let calls = 0;
  const app = boot({predict: () => {
    calls += 1;
    if (calls === 1) return json({detail: [{loc: ["body", "floor"], msg: "Floor exceeds building."}]}, 422);
    if (calls === 2) return pending.promise;
    return json(PREDICTION);
  }});
  await flush();
  await app.submit();
  assert.equal(app.get("floor").getAttribute("aria-invalid"), "true");
  const submission = app.submit();
  assert.equal(app.get("floor").getAttribute("aria-invalid"), null);
  assert.equal(app.get("floor").getAttribute("aria-describedby"), null);
  assert.equal(app.result.hidden, true);
  assert.equal(app.result.textContent, "");
  assert.equal(app.button.disabled, true);
  await app.submit();
  assert.equal(calls, 2);
  pending.resolve(json(PREDICTION));
  await submission;
  assert.match(app.result.textContent, /Estimated fair rent/);
  assert.equal(app.button.disabled, false);
  const next = app.submit();
  assert.equal(app.result.hidden, true);
  assert.equal(app.result.textContent, "");
  await next;
  assert.equal(calls, 3);
  assert.match(app.result.textContent, /Estimated fair rent/);
});
