# The sample data

`listings_sample.csv` is the original three-row schema example. `demo.csv` contains 126 generated
rows for tests and CI. It covers EUR, MDL and USD, with synthetic features, fixed-seed prices
and artificial reposts. Both files contain fictional observations.

Keep real snapshots local. Hashed listing identifiers are pseudonyms. The
[MLOps guide](../../docs/mlops.md#data-contract-and-evaluation) defines the input and output contracts.

## The columns

Each row represents one listing. The scraper keeps only the reviewed controls below and records
the source ad ID as a short hash (`listing_key`). Keep real exports private because maps, photo
references and free text can identify listings.

| Column | Meaning |
|---|---|
| `listing_key` | stable hash of the source ad ID for matching observations |
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
| `observed_at` | UTC time the current scraper fetched the listing details |
| `first_seen`, `last_seen` | legacy checkpoint dates for first entry and latest search match |

## Using your own data

Follow the [snapshot guide](../../docs/mlops.md#collect-a-private-snapshot) to collect data,
then [select a snapshot](../../docs/mlops.md#select-or-restore-a-dataset) for the real-data DVC
pipeline. Use the demo CSV for CI, Docker smoke checks and shared examples.
