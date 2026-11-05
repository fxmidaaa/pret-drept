# The sample data

`listings_sample.csv` is three made-up rows. Nothing in it is real: no real listing, no real
coordinate, no contact, no ad text. It's here for one reason, so you can see the exact columns the
pipeline expects without me having to ship anyone's actual rental ad to do it.

## Why the real data isn't here

Public listing data can contain personal or linkable information, including coordinates, ad text and
photo references. Git ignore rules cover raw snapshots, and the Docker build allowlist omits them.
These rules reduce accidental inclusion; they do not enforce storage permissions or establish anonymity.

The legacy bundle contains a fitted estimator, vectorizer, numeric defaults and market-rate summaries.
The grid and sector rent maps use medians with a default minimum of 15 rows per group. The global
fallback and coordinate/default statistics have no equivalent guard. A median can coincide with an
observed value, and aggregation alone does not prove that no listing can be inferred.

`test_bundle_ships_no_row_level_data` in [`tests/test_api.py`](../../tests/test_api.py) checks selected
top-level field names and scalar rent-map values. It does not inspect every nested/native payload,
verify cohort sizes or certify privacy. See the [A17 artifact review](../../docs/reports/a17-privacy-claims.md)
and [publication review procedure](../../docs/operations/artifact-publication-review.md).

## The columns

Each row illustrates the shape `scrape.py` writes. Checkpoint storage accepts only reviewed fields.
Dedicated contact and seller-name controls are excluded, but allowed text is not redacted and can
retain personal information. `listing_key` is a deterministic pseudonym: the first 16 hexadecimal
characters of SHA-1 over the source ID. Candidate IDs can be rehashed to match it. Changing this
format would require an explicit checkpoint migration; no such migration is made here.

| Column | Meaning |
|---|---|
| `listing_key` | deterministic hash pseudonym used for deduplication and resuming collection; not an anonymity guarantee |
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
| `Harta` | JSON `{"lat":…,"lon":…}`; coordinates are model inputs and also produce distance/grid features and coordinate defaults |
| `Fotografii` | photo references, used only to count how many there are |
| `Textul anunțului` | ad text, used only to pull out a few boolean flags (condition, utilities, lux, bathroom count) |
| `Tipul ofertei`, `Regiune`, `Localitate` | filter fields (monthly rent, Chișinău) |
| `price_value`, `price_unit` | rent amount and its currency (EUR, MDL, or USD) |
| `first_seen`, `last_seen` | when the scraper first and last saw this listing |

## Doing this with your own data

1. Collection needs separate authorization. Use the root README's
   [checkpoint instructions](../../README.md#running-it) to choose a compatible destination distinct
   from the historical snapshot. Keep raw observations under appropriate private storage controls.
2. Training from an authorized local snapshot writes a legacy candidate `model.joblib` containing
   fitted state and helper statistics. Training does not review or approve the artifact for sharing.
3. Follow the [development guide](../../docs/development.md) to run the relevant checks. Review the
   exact artifact, intended destination and disclosure risks before any separately authorized export.
