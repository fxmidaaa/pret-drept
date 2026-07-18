# The sample data

`listings_sample.csv` is three made-up rows. Nothing in it is real: no real listing, no real
coordinate, no contact, no ad text. It's here for one reason, so you can see the exact columns the
pipeline expects without me having to ship anyone's actual rental ad to do it.

## Why the real data isn't here

The training data is scraped from a public listings site, and even a rental ad carries personal stuff:
map coordinates, the free-text description, photo references. So the raw snapshot stays on my machine.
It's gitignored, never committed, never copied into the Docker image, never baked into the published
model. The only things that ever leave my machine are coarse aggregates: median EUR/m² over ~1 km
grid cells and over whole sectors, and each of those is an average of at least 15 listings, so no
single flat can be read back out.

There's a test that enforces this, by the way. `test_bundle_ships_no_row_level_data` in
[`tests/test_api.py`](../../tests/test_api.py) fails if any per-listing field ever sneaks into
`model.joblib`, so this isn't just a promise in a README.

## The columns

Each row is one listing, in the shape `scrape.py` writes it. And `scrape.py` is picky on purpose: it
only ever writes the reviewed allowlist below. The source id is stored as a short one-way hash
(`listing_key`), and contacts, phone numbers, and the seller's name are thrown away at collection
time, so they never hit disk at all.

| Column | Meaning |
|---|---|
| `listing_key` | one-way hash of the source id, used only for dedupe and resuming a scrape |
| `Sector` | city sector (Centru, Botanica, Râșcani, and so on) |
| `Număr de camere` | rooms |
| `Suprafață totală` | total area, m² |
| `Etaj` / `Număr de etaje` | floor / total floors |
| `Fond locativ` | new build vs secondary |
| `Starea apartamentului` | condition |
| `Tip clădire` | building type |
| `Încălzire autonomă`, `Mobilat`, `Ascensor`, `Loc de parcare` | amenities |
| `Balcon/ lojie` | balcony count |
| `Suprafață bucătărie`, `Inălțimea tavanelor` | kitchen area, ceiling height |
| `Terasă`, `Aparat de aer condiționat`, `Încălzire prin pardoseală`, `Geamuri panoramice` | more amenity flags |
| `Autorul anunțului` | who's posting (private person or agency) |
| `Harta` | JSON `{"lat":…,"lon":…}`, used only to derive a distance and a coarse grid cell |
| `Fotografii` | photo references, used only to count how many there are |
| `Textul anunțului` | ad text, used only to pull out a few boolean flags (condition, utilities, lux, bathroom count) |
| `Tipul ofertei`, `Regiune`, `Localitate` | filter fields (monthly rent, Chișinău) |
| `price_value`, `price_unit` | rent amount and its currency (EUR, MDL, or USD) |
| `first_seen`, `last_seen` | when the scraper first and last saw this listing |

## Doing this with your own data

1. Scrape your own listings with `python scrape.py`. It writes to `data/raw/listings.csv`, which stays
   private.
2. Run `python train.py`. It cleans the raw file, builds the features, and writes a `model.joblib`
   that holds aggregates only.
3. Run `python -m pytest`. If any row-level field ever slipped into the model, the privacy test above
   catches it.
