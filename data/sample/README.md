# Sample data & data contract

`listings_sample.csv` is a **small, fully synthetic** sample (3 invented rows). It
exists so you can see the exact column schema the pipeline expects. **No real
listing, coordinate, contact, or ad text is distributed with this project.**

## Why the real data is not here

The training data is scraped from a public listings site and contains personal
and location information (map coordinates, free-text ads, photo references). That
raw snapshot is **private**: it is gitignored, never committed, never copied into
the Docker image, and never embedded in the published model. Only coarse
aggregates (median €/m² over ~1 km grid cells and city sectors, each requiring at
least 15 listings) ever leave your machine.

## Schema

Each row is one listing, as persisted by `scrape.py`. The scraper writes only the
reviewed **allowlist** of fields below — listing ids are stored as a short
non-reversible hash (`listing_key`), and contacts / phone / seller name are
dropped at collection time.

| Column | Meaning |
|---|---|
| `listing_key` | non-reversible hash of the source id (dedupe/resume only) |
| `Sector` | city sector (Centru, Botanica, Râșcani, …) |
| `Număr de camere` | rooms |
| `Suprafață totală` | total area, m² |
| `Etaj` / `Număr de etaje` | floor / total floors |
| `Fond locativ` | new vs secondary building |
| `Starea apartamentului` | condition |
| `Tip clădire` | building type |
| `Încălzire autonomă`, `Mobilat`, `Ascensor`, `Loc de parcare` | amenities |
| `Balcon/ lojie` | balcony count |
| `Suprafață bucătărie`, `Inălțimea tavanelor` | kitchen area, ceiling height |
| `Terasă`, `Aparat de aer condiționat`, `Încălzire prin pardoseală`, `Geamuri panoramice` | amenity flags |
| `Autorul anunțului` | author type (private person / agency) |
| `Harta` | JSON `{"lat":…,"lon":…}` — used only to derive distance + a coarse grid cell |
| `Fotografii` | photo references — used only to derive a photo **count** |
| `Textul anunțului` | ad text — used only to derive boolean flags (condition, utilities, lux, bathrooms) |
| `Tipul ofertei`, `Regiune`, `Localitate` | filter fields (monthly rent in Chișinău) |
| `price_value`, `price_unit` | rent amount + currency (EUR / MDL / USD) |
| `first_seen`, `last_seen` | scrape timestamps |

## Reproducing with your own private data

1. Collect your own listings with `scrape.py` (writes to `data/raw/listings.csv`,
   which stays private).
2. Run `python train.py` — it cleans the raw file, derives features, and writes a
   privacy-reviewed `model.joblib` containing aggregates only.
3. `python -m pytest` — `test_bundle_ships_no_row_level_data` fails if any
   row-level field ever slips into the artifact.
