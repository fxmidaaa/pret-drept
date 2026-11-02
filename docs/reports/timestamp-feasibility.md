# 999.md timestamp feasibility — 2026-11-02

**Result: publication-related dates are available through the live public GraphQL API. No frozen architectural decision needs to be relaxed merely because the existing CSV omitted them.** Availability is verified; historical backfill, immutability and suitability for official temporal evaluation are not established by this small probe.

## Verified primary evidence

Read-only schema introspection of [999.md GraphQL](https://999.md/graphql) returned query type `Query`, operation `advert(input: AdvertInput!)` and result type `Advert`. Its date fields are:

| Field | Live schema description | Type |
|---|---|---|
| `posted` | Ad POSTED DATE | `String!` |
| `reseted` | Ad PUBLISH, REPUBLISH ETC.. DATE | `String!` |
| `expire` | Ad DATE EXPIRE | `String!` |

Each accepts `input: DatetimeFormat`, whose fields are `format`, `locale`, `getDiff`, `prefix`, `timezone`. No authentication or account credentials were supplied. The robots document was also inspected; its default rules do not list `/graphql`. That is technical access evidence, not a legal determination or blanket permission for bulk acquisition.

A listing was independently obtained from public `searchAds` (monthly Chișinău apartment filter, limit 1), then queried for dates only. **No private CSV identifiers were used in the successful request.** The public example was [listing 105794529](https://999.md/ro/105794529); the read completed at `2026-11-02T17:26:41.093358+00:00`, HTTP 200. Returned values:

```json
{
  "posted_default": "",
  "posted_utc": "2026-11-02T17:25:39Z",
  "republished_utc": "2026-11-02T17:25:39Z",
  "expires_utc": "2026-12-02T17:25:39Z"
}
```

All three explicit UTC values parsed as offset-aware ISO timestamps. The default date was empty, so merely adding `posted` without formatting is insufficient. A first formatting probe using `YYYY-MM-DDTHH:mm:ssZ` returned the literal pattern and failed ISO parsing. The following explicit layout was then verified successfully:

```graphql
query PublicationTimes($i: AdvertInput!) {
  advert(input: $i) {
    posted(input: {
      format: "2006-01-02T15:04:05Z07:00"
      timezone: "UTC"
      getDiff: false
      prefix: false
    })
    reseted(input: {
      format: "2006-01-02T15:04:05Z07:00"
      timezone: "UTC"
      getDiff: false
      prefix: false
    })
    expire(input: {
      format: "2006-01-02T15:04:05Z07:00"
      timezone: "UTC"
      getDiff: false
      prefix: false
    })
  }
}
```

This proves current field accessibility and a working representation on one public listing. It does not establish completeness across old/deleted listings, stability over time, an immutable first-ever publication date, original versions of prices/features, or authorization for continuous scraping. The sample has equal posting/republication dates, so their distinct lifecycle behavior is supported by schema descriptions, not experimentally established with a republishing operation. No mutation, paid operation or republishing was performed.

## Architectural interpretation

Keep specification §9.3's four distinct concepts:

* `source_posted_at`: source-reported posting date; do not assert immutable first publication without additional evidence.
* `source_republished_at`: source-reported publish/republish event (`reseted`); do not rename it as a generic price/feature update time.
* `observed_at`: when this actual price/feature payload was collected; record an explicit UTC collection time and acquisition provenance.
* Feature availability and prediction cutoff: determine whether each input was available at the evaluated prediction time.

These are proposed data-layer field spellings for reviewed implementation, not an activated split-policy change. `expire` may be retained as source lifecycle metadata; it is not automatically an eligible predictor at historical cutoffs.

The existing `scrape.py` requests none of these three source fields. It records date-only first/last seen values, updates last-seen without re-fetching known listings, and overwrites listing-key rows. Therefore adding source dates alone will not create the immutable observation history required by the architecture. A reviewed ingestion increment should request validated source times, record collection times, retain successive observations and keep lifecycle metadata outside uncontrolled predictive features.

For the supplied historical CSV, a date fetched **today** is new enrichment observed today. It must not silently be represented as a date known at the July/August collection. A listing may have been republished, edited or removed. Pairing an old posting date with a later observed price can create leakage if the pair is presented as a historical observation. Publication-based splitting could be studied as a separately described retrospective cohort; it does not automatically certify the official future-market protocol or resolve property duplication.

Recommended sequence: preserve the historical snapshot; establish its acquisition provenance if logs exist; review any date-only enrichment separately; implement timestamp-aware append-only observations after acquisition review; generate reviewed development/protected split manifests when their chronology and property identity are defensible. No fabricated dates, filesystem modification dates or listing-ID age estimates are acceptable substitutes.

## Approval boundary and remaining verification

Automatic approval review rejected a proposed date-only test using three source IDs from the private CSV, because it would export private-derived identifiers to an external service without sufficiently explicit authorization. The rejected action did not execute. The successful substitute used independently discovered public data and did not bypass that restriction. Historical private-ID lookups remain unperformed; they would need explicit authorization before any retry.

No raw data or trained model was changed, no identifiers from the private snapshot were sent, and no bulk acquisition occurred. No temporal benchmark was run or policy revised. The timestamp-capability question is resolved positively; observation provenance and official temporal evaluation remain separate gates.
