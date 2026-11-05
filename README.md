# Is this Chișinău apartment overpriced?

Engineering migration is underway against the frozen [architecture v1](docs/architecture/specification-v1.md).
The [alignment audit](docs/reports/m0-alignment.md) distinguishes historical functionality from
verified new foundations. See the [development guide](docs/development.md) for contract checks,
tests and current limitations. The original app/workflows described below are preserved; their
historical scores do not certify the new temporal/unseen-property evaluation protocol.

The Python wheel and source archive ship the engineering foundations. The source archive
includes synthetic contract, task lifecycle, and architecture tests. With the package dependencies
and `pytest` installed, run `python -m pytest` from the unpacked archive. The application, full
test suite, and linked project resources below are available in the repository checkout.

My first machine learning project. I scraped about 4,500 real apartment rental listings from a
Moldovan classifieds site, trained a model on them, and built a small app that estimates a fair
monthly rent and tells you whether a given listing is overpriced or a good deal.

The idea: when you're hunting for a flat to rent in Chișinău, you never really know if the asking
price is normal, too high, or too low, unless you happen to be an agent or an analyst yourself. So I
built a tool that compares a listing against the whole market and explains *why* it thinks the rent
is fair or not.

There's a live demo at [https://pret-drept-tm6owb5eka-ew.a.run.app](https://pret-drept-tm6owb5eka-ew.a.run.app).
It runs on Google Cloud Run, which spins the container down when nobody's using it, so the first
request after a quiet spell takes a few seconds to wake up.

---

## What does it predict?

You give it an apartment (rooms, area, sector, floor, heating, furnishing, and so on) and it hands
back:
- an estimated fair monthly rent in EUR
- a verdict: overpriced, fair, or a good deal
- the top five reasons behind that number, so it isn't just a black box handing you a figure

---

## The data

Everything comes from [999.md](https://999.md), filtered to long-term monthly rentals in Chișinău.
999.md is a JavaScript site, so a plain HTML scraper just reads an empty shell. Its frontend talks to
a public GraphQL API though, and that API returns every listing as clean structured JSON: price with
its currency, area, rooms, floor, sector, heating type, furnishing, even GPS coordinates. So
`scrape.py` queries the API directly. No HTML parsing, no headless browser. I try to be a decent
guest about it too: I filter server-side to exactly what I need, lean on the API's own duplicate
collapsing, pause between requests, and save as I go.

One thing on privacy, since this scrapes real ads. `scrape.py` keeps only a reviewed list of fields,
never contacts or the seller's name, and it stores the listing id as a one-way hash. The raw file it
writes stays on my machine: gitignored, never committed, never baked into the Docker image, never
published. What's public is a small synthetic sample plus the column schema in
[`data/sample/`](data/sample/), and a model that only ever holds coarse aggregates, never a single
listing's coordinates or price.

The historical snapshot was reported as 4,528 listings, with 3,557 after initial cleaning and
about 3,400 after further trimming. Legacy cleaning drops rows missing area, asking price, or
rooms, keeps asking rents between 100 and 2000 EUR, and deduplicates on coarse apartment
attributes together with asking price. This key can retain repeated apartments when their
asking price changes.

The legacy trainer uses a random 80/20 split. It fits rent-per-m² quantile bounds and imputation
medians on training data, then also trims validation rows by rent per m² and by their ratio to
the training-derived local market rate. Validation membership therefore depends on observed
asking prices. The reported scores describe the listings retained by these filters.

The historical profile put about 95% of listings in EUR and the rest in MDL or USD. The legacy
conversion uses a fixed 19.5 MDL/EUR rate. Project notes date the snapshot to July 2026, while
the CSV's missing observation timestamps limit the chronology that can be reconstructed.

---

## What the market actually looks like

Before training anything I spent a while just looking at the data. The
[`EDA notebook`](notebooks/eda.ipynb) contains the analysis code. Both public notebooks are
stored with cleared outputs and use the private dataset when run locally. The charts and
model comparison on this page summarize the results.

Rent is heavily skewed: lots of ordinary flats and a long tail of expensive ones. Taking the log
makes it roughly symmetric, which is the whole reason the model trains on `log(price)`.

![rent distribution](images/rent_distribution.png)

Location does most of the work. Centru goes for about 13.6 EUR/m² while the outer sectors sit around
8.5 to 10.9, with a clean centre-outward gradient in between.

![price per sector](images/price_per_sector.png)

The biggest single gap is new build versus old Soviet stock: +32% per m², 13.1 against 9.9 EUR/m².

![new build gap](images/newbuild_gap.png)

My favourite finding is that autonomous heating turns out not to be a price driver at all. Moldova
went through an energy crisis recently, so everyone assumes flats with their own heating rent for
more, and the raw numbers agree (+7%). But autonomous heating is standard in new buildings, and new
buildings cost more for other reasons anyway. Compare inside each building fund and the premium
disappears completely. It was the new-building effect all along.

![heating premium](images/heating_premium.png)

Smaller stuff: each extra m² is worth about 11 EUR/month (small flats are pricier per m²), the ground
floor is a real discount (-10%), furnishing adds nothing since here it's simply expected, and ads
that brag about a penthouse or a jacuzzi really do ask ~19% more per m².

---

## Cleaning and features

The JSON is clean in the sense that it's structured, but the values themselves are a mess. Fields
come in Romanian and Russian, people type ceiling height as "3", "28", or "280" depending on their
mood, and a third of the useful information is buried in the free-text ad. Almost all of the work in
this project lives in `features.py`, which turns each raw listing into the numbers the model actually
sees.

The plain features are what you'd expect: rooms, area, floor and total floors, kitchen area, ceiling
height, balcony count, sector, building fund (new vs secondary), condition, who's selling (agency,
owner, or developer), and a pile of yes/no amenities (autonomous heating, furnished, elevator,
parking, AC, terrace, and so on).

Three of them took actual thought:

- The local market rate. For each apartment I take the median EUR/m² of the flats in its own coarse
  (~1 km) grid cell, and fall back to the sector, then the whole city, when a cell is thin. That's
  basically what a person does when sizing up a price: you look around. It's one of the strongest
  signals in the model. I compute it from the training rows only, and the shipped model keeps just
  these cell and sector aggregates, each one an average over at least 15 listings. It never stores the
  individual coordinates or prices, so no single listing can be pulled back out of it.
- Reading the ad text. Around a third of listings leave the condition field empty but describe it in
  words ("euroreparație", "евроремонт"). I pull those back out with keyword matching in both
  languages. Same trick for spotting when the rent already includes utilities, which otherwise
  quietly throws the price off. The text is also the only place a flat admits it's fancy: in the
  structured fields a penthouse and a regular flat of the same size look identical (both just say
  "euroreparație"), so I also pull out a bathroom count ("2 blocuri sanitare", "2 санузла") and a
  premium flag for words like penthouse, jacuzzi or "clasă premium". Before that, the model priced
  every big flat in Centru like an average one.
- Training on log(price) instead of price. Rent skews hard toward the cheap end, so I fit on the log
  and convert back at the end. Without that, the handful of expensive flats dominate the error and
  the model basically ignores everything under 1000 EUR.

---

## Picking the model

`train.py` uses XGBoost. The [model-selection notebook](notebooks/model_selection.ipynb)
records the historical comparison with a simple baseline, linear regression, ridge, random
forest, and gradient boosting. The comparison used random splits and five random folds after
legacy cleaning and asking-price filters.

| model | Historical CV RMSE (EUR) |
|---|---|
| dumb baseline (one price per m², times area) | ~290 |
| linear regression | 249 |
| gradient boosting | 214 |
| random forest, tuned | 200 |
| **XGBoost, tuned** | **192** |

The legacy bundle's reported random validation scores were MAE 134 EUR, MAPE 16.1%, RMSE 188 EUR,
and R² 0.78. The trainer stores these scores in `model.joblib` after a fixed 80/20 random split
(`random_state=42`) and validation trimming. Their coverage is the retained historical
population. MAE averages absolute errors in euros, and RMSE gives more weight to large errors.

A14's benchmark implementation is deferred to M2. The frozen architecture requires primary
future-market evaluation and a secondary view for previously unseen apartments, using the
same versioned evaluation records across candidates. The
[A14 handoff](docs/tasks/2026-11-05-evaluation-handoff/plan.md#m2-handoff) records the required
timestamped observations, immutable dataset releases, and reviewed property identities.

The legacy XGBoost settings came from the notebook's historical random search.

```
n_estimators=600, max_depth=6, learning_rate=0.05,
subsample=0.83, colsample_bytree=0.77, min_child_weight=7
```

---

## Where it falls short

Worth being upfront about a few things:

- Legacy cleaning limits asking rents to 100–2000 EUR, and further validation trims remove
  atypically priced listings. The API accepts a broader range of asking prices, so the reported
  scores cover a narrower population than requests the app can receive.
- It only knows what the listing says. A beautiful flat with a lazy description, or a scam with a
  great one, will fool it exactly the way it would fool you.
- The historical CSV has no observation timestamps, and its deduplication key includes asking
  price. Measuring future-market and unseen-property performance needs the M2 data history
  and reviewed identity policy.

---

## Running it

Python 3.13. First:

```bash
pip install -r requirements.txt
```

Start the app (you need a trained `model.joblib` for this):

```bash
uvicorn api:app --reload
# then open http://127.0.0.1:8000
```

Train from the existing private snapshot:

```bash
python train.py     # cleans, trains, writes model.joblib
```

For separately authorized collection, choose a working checkpoint distinct from the historical dataset:

```bash
python scrape.py --checkpoint data/checkpoints/listings.csv
```

The legacy `python scrape.py` command retains its default path, but now rejects incompatible files
before making requests. The historical snapshot uses `id` rather than the scraper's `listing_key`;
it requires a separately reviewed migration to a new destination, retaining the original. No
automatic conversion occurs. Compatible working checkpoints are saved atomically, and invalid,
duplicate, or missing listing keys cause an error instead of silently losing rows. The separate
checkpoint is not automatically used by `train.py` and is not an immutable dataset release.

Checkpoints accept only the reviewed feature/filter columns plus `listing_key`, `price_value`,
`price_unit`, `first_seen` and `last_seen`. Unexpected columns cause an error before collection or
saving; the existing file is preserved, including when it contains only a header. Names must match
exactly. Such files require a separately reviewed, versioned migration to a new destination, retaining
the original. Unapproved controls in fetched advertisements continue to be ignored. This column rule
does not detect personal information inside permitted text fields.

Failed or unavailable listing retrievals stay outside completed checkpoint state, so a later run
can retry them if they appear in search again. Rejection is saved only after retrieving and checking
the listing. Search failures stop collection; any unresolved retrieval makes the command exit with
status 1 after saving completed page progress. Error messages omit response bodies. Existing rejection
markers remain unchanged because their original cause cannot be recovered. There is no persistent
retry queue or guarantee that a listing will appear in a later search.

Or try a single prediction from the terminal: `python predict.py` runs the example apartment at the
bottom of that file.

Run the tests (they cover the cleaning rules, features, API, and checkpoint preservation):

```bash
python -m pytest
```

If you'd rather not install Python at all, there's a Dockerfile. It ships the inference code plus a
privacy-reviewed, pre-trained `model.joblib`. Training happens privately, not during the build, so you
need a trained model present first:

```bash
python train.py            # writes a reviewed model.joblib from your private data
docker build -t chisinau-rent .
docker run -p 8000:8000 chisinau-rent
```

---

## Trying the live API

It's deployed at [pret-drept-tm6owb5eka-ew.a.run.app](https://pret-drept-tm6owb5eka-ew.a.run.app): the site itself, plus a
JSON API you can hit directly:

```bash
curl -X POST "https://pret-drept-tm6owb5eka-ew.a.run.app/predict" \
  -H "Content-Type: application/json" \
  -d '{"rooms": 2, "area": 50, "floor": 3, "total_floors": 9, "sector": "centru", "author": "agenție"}'
# expect: {"fair_price": 638, "listed_price": null, "drivers": [...]}
# add "price": <listed rent> to also get "deviation_pct" and a "verdict"
```

---

## What's where

```
scrape.py                  999.md GraphQL scraper with validated atomic working checkpoints
features.py                all the cleaning and feature engineering
train.py                   trains XGBoost, saves model.joblib
predict.py                 loads the model, makes one prediction + explanation
api.py                     FastAPI - /predict, /options, /health, serves the page
app/index.html             the one-page front end (form in, verdict out)
Dockerfile                 containerised API (inference code + reviewed model)
notebooks/eda.ipynb        exploratory analysis source
notebooks/model_selection.ipynb   model comparison source
data/sample/               synthetic sample + column schema (real data stays private)
images/                    charts from the EDA
tests/                     tests for cleaning, features, the API and checkpoint preservation
```

One thing I'm a little proud of: `features.py` is the only place the cleaning rules live, and
training, prediction, and the API all import from it, so they can't quietly disagree about what
"ground floor" means or how a price gets converted. And `model.joblib` holds more than the model. It
also stores sensible per-sector defaults, so the site can fill in the things a normal person would
never type (typical coordinates, ceiling height, photo count) from just the sector you picked.
Everything it stores is an aggregate: per-sector and coarse ~1 km grid medians, never a per-listing
coordinate or price.

---

## Still on the list

- Github Actions (CI).
- A wider hyperparameter search after M2 establishes the versioned evaluation cohort.
- Some kind of confidence range instead of a single number.
- Scheduled acquisition with timestamped observation history and versioned dataset releases.
- Eventually: sale prices too.
