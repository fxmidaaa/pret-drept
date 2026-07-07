# Is this Chișinău apartment overpriced?

My first machine learning project. I scraped ~4500 real apartment **rental** listings from a 
Moldovan classifieds site, trained a model on them, and built a small app that estimates a 
**fair monthly rent** for an apartment and tells you if a listing is **overpriced** or 
**a good deal**.

The idea is: when you look for a flat to rent in Chișinău you never really know if the price is 
normal, too high or too low (unless you are a real estate agent or an analyst). So I made a tool 
that compares a listing against the whole market and explains *why* it thinks the rent is fair or not. 

**Live demo:** [pret-drept.onrender.com](https://pret-drept.onrender.com) (free-tier host, the first
request after idle can take ~30-60s to wake up).

--- 

## What does it predict? 

You give it an apartment (rooms, area, sector, floor, heating, furnishing, etc.) and it returns:
- an estimated **fair monthly rent** in EUR
- whether the asking rent is **overpriced / fair / a good deal**
- the top 5 reasons behind that number, so it's not just a black box spitting out a figure

---

## The data

- **Source:** [999.md](https://999.md) - apartments for **long-term (monthly) rent**, Chișinău only.
- **How:** 999.md is a JavaScript site, so a normal HTML scraper can't read it. But its frontend
  talks to a public **GraphQL API**, which returns every listing as clean structured JSON - price
  (with currency), area, rooms, floor, sector, heating type, furnishing, even GPS coordinates. So
  my scraper (`scrape.py`) just queries that API directly. No HTML parsing, no headless browser.
- **Responsibly:** I filter to exactly what I need server-side (monthly rent + Chișinău), use the
  API's built-in duplicate collapsing, add a short pause between requests, and save incrementally.
- **Size:** **4,528** listings scraped, **3,719 after cleaning** (drop the ones missing area/price/rooms,
  drop reposted duplicates, keep rent between 100 and 3000 EUR). On top of that, the worst 1% of
  rent-per-m² on each end gets cut - those are basically always someone fat-fingering the area or
  the price. The cutoffs (and the medians used to fill missing values) are computed on the training
  split only, so the validation rows never influence what the model trains on.
- **Currency:** ~95% are quoted in EUR, the rest in MDL/USD - I normalize everything to EUR at a
  fixed rate (19.5 MDL/EUR, BNM mid-2026).
- Collected July 2026.

---

## What the market actually looks like

Before training anything I spent some time just looking at the data
([`notebooks/eda.ipynb`](notebooks/eda.ipynb) has the full tour). A few things worth showing:

**Rent is heavily skewed.** Lots of normal flats, a long tail of expensive ones. Taking the log
makes it symmetric - that's the whole reason the model trains on `log(price)`:

![rent distribution](images/rent_distribution.png)

**Location matters most.** Centru goes for ~14.0 EUR/m² while the outer sectors sit around
9.2-10.8, with a clean centre-outward gradient in between:

![price per sector](images/price_per_sector.png)

**New build vs old Soviet stock is the biggest single gap: +41% per m²** (13.5 vs 9.6 EUR/m²):

![new build gap](images/newbuild_gap.png)

**And my favourite finding: autonomous heating is not actually a price driver.** Moldova went
through an energy crisis recently, so everyone assumes flats with their own heating rent for more -
and raw numbers agree (+9.9%). But autonomous heating is standard in new buildings, and new
buildings are expensive for other reasons too. Compare inside each building fund and the premium
vanishes completely. It was the new-building premium all along:

![heating premium](images/heating_premium.png)

Smaller stuff: each extra m² is worth ~13 EUR/month (small flats are pricier per m²), ground floor
is a real discount (-13%), and furnishing adds nothing - it's simply expected here.

---

## Cleaning and features

The JSON is clean in the sense that it's structured, but the values themselves are a mess. Fields
come in Romanian and Russian, people type ceiling height as "3", "28" or "280" depending on their
mood, and a third of the useful info is buried in the free-text ad. Almost all of the work in this
project lives in `features.py`, which turns each raw listing into the numbers the model actually sees.

The plain features are what you'd expect: rooms, area, floor and total floors, kitchen area, ceiling
height, balcony count, sector, building fund (new vs secondary), condition, who's selling (agency /
owner / developer), and a bunch of yes/no amenities - autonomous heating, furnished, elevator,
parking, AC, terrace and so on.

The three that took actual thought:

- **"what do the neighbours charge?"** For each apartment I find its 15 closest listings by GPS and
  take their median EUR/m². This is basically what a human does when judging a price - you look
  around. It ended up being the strongest single signal in the whole model. I compute it only from
  the training rows though, otherwise a listing would get to peek at its own neighbours and the
  scores would come out fake-good.
- **reading the ad text.** Around a third of listings leave the condition field empty but describe
  it in words ("euroreparație", "евроремонт"). I pull those back out with keyword matching in both
  languages. Same idea for spotting when rent already includes utilities, which quietly messes up
  the price otherwise.
- **predicting log(price) instead of price.** Rent is heavily skewed toward the cheap end, so I
  train on the log and convert back at the end. Without this the handful of expensive flats dominate
  the error and the model basically ignores everything under 1000 EUR.

---

## Picking the model

`train.py` uses **XGBoost**. I didn't just reach for it because it's the popular choice - the whole
argument is in [`notebooks/model_selection.ipynb`](notebooks/model_selection.ipynb). There I take
the same data and the same split, and run a dumb baseline, linear regression, ridge, random forest,
gradient boosting and XGBoost through the exact same scoring, then confirm the order with 5-fold
cross-validation and tune the two best. Here's roughly where they land (RMSE in real EUR of rent):

| model | CV RMSE |
|---|---|
| dumb baseline (one price per m², times area) | ~387 |
| linear regression | 295 |
| gradient boosting | 272 |
| random forest, tuned | 258 |
| **XGBoost, tuned** | **252** |

So the model I ship is off by ~250 EUR RMSE - or about 170 EUR (~19% MAPE) on a typical listing,
since RMSE is inflated by the expensive tail. Rent in the dataset averages around 900. Not amazing,
but every model crushes the dumb baseline and even a straight line explains 71% of the variance,
which told me the features were pulling their weight before I ever touched a tree.

One honest footnote about where these numbers come from: the table above is 5-fold cross-validation
from the notebook - that's what picked the model and its settings. The model I actually ship is then
retrained by `train.py` on a single fixed 80/20 split (`random_state=42`, the same split the notebook
uses), and *its own* holdout scores get stamped into `model.joblib` (RMSE 271, MAE 169, MAPE 18.6%,
R² 0.75 - printed every time the API loads the model). Don't read too much into that exact 271: on a
~740-row holdout the RMSE swings by split, while the notebook's 5-fold CV puts the tuned model at
252 ± 13 EUR. This particular split is just a slightly unlucky one; the CV figure is the honest
headline.

The tuned XGBoost settings (found by random search in the notebook):

```
n_estimators=600, max_depth=6, learning_rate=0.05,
subsample=0.83, colsample_bytree=0.77, min_child_weight=7
```

---

## Where it falls short

Worth being upfront about this:

- It's built for normal flats, not luxury. I cap rent at 3000 EUR/month on purpose - the stuff above
  that is rare and all over the place, and it wrecked the metrics without teaching the model anything
  useful about ordinary apartments.
- It only knows what the listing says. A beautiful flat with a lazy description, or a scam with a
  great one, will fool it just like it'd fool you.
- It's a July 2026 snapshot. Prices move, so it needs re-scraping and re-training now and then to
  stay honest.

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

Rebuild everything from scratch:

```bash
python scrape.py    # grabs fresh listings into data/raw/listings.csv
python train.py     # cleans, trains, writes model.joblib
```

Or just try one prediction from the terminal - `python predict.py` runs the example apartment at the
bottom of that file.

Run the tests (they cover the cleaning rules, the features and the API):

```bash
python -m pytest
```

If you'd rather not install Python at all, there's a Dockerfile - it trains the model itself during
the build, so there's nothing to prepare beforehand:

```bash
docker build -t chisinau-rent .
docker run -p 8000:8000 chisinau-rent
```

---

## Trying the live API

It's deployed at [pret-drept.onrender.com](https://pret-drept.onrender.com) - the site itself, plus
a JSON API you can hit directly:

```bash
curl -X POST "https://pret-drept.onrender.com/predict" \
  -H "Content-Type: application/json" \
  -d '{"rooms": 2, "area": 50, "floor": 3, "total_floors": 9, "sector": "centru", "author": "agenție"}'
# expect: {"fair_price": 638, "listed_price": null, "drivers": [...]}
# add "price": <listed rent> to also get "deviation_pct" and a "verdict"
```

---

## What's where

```
scrape.py                  999.md GraphQL scraper -> data/raw/listings.csv
features.py                all the cleaning and feature engineering
train.py                   trains XGBoost, saves model.joblib
predict.py                 loads the model, makes one prediction + explanation
api.py                     FastAPI - /predict, /options, /health, serves the page
app/index.html             the one-page front end (form in, verdict out)
Dockerfile                 containerised API
notebooks/eda.ipynb        exploratory analysis
notebooks/model_selection.ipynb   the "why XGBoost" comparison
data/raw/listings.csv      the scraped data
images/                    charts from the EDA
tests/                     unit tests for the cleaning rules, features and the API
```

One thing I'm a little proud of: `features.py` is the only place the cleaning rules live, and
training, prediction and the API all import from it. So they can't quietly disagree about what
"ground floor" means or how a price gets converted. And `model.joblib` isn't just the model - it
also stores sensible defaults per sector, so the website can fill in the stuff a normal person would
never type (GPS coordinates, ceiling height, photo count) from just the sector you picked.

---

## Still on the list

- Github Actions (CI).
- A wider hyperparameter search - the current one was only 10 random tries, so 252 is more of a
  ceiling than the real best.
- Some kind of confidence range instead of a single number.
- Re-scraping on a schedule so it doesn't go stale.
- Eventually: sale prices too.