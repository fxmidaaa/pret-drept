# Is this Chișinău apartment overpriced?

My first machine learning project. I scraped ~4500 real apartment **rental** listings from a 
Moldovan classifieds, trained a model on them, and built a small app that estimates a 
**fair monthly rent** for an apartment and tells you if a listing is **overpriced** or 
**a good deal**.

The idea is: when you look for a flat to rent in Chișinău you never really know if the price is 
normal, too high or too low. (unless you are a real estate agent or an analyst). So I made a tool 
that compares a listing against the whole market and explains *why* it thinks the rent is fair or not. 

--- 

## What it predicts? 

You give it an apartment (rooms, area, sector, floor, heating, furnishing, etc/) and it returns:
- an estimated **fair monthly rent** in EUR
- whether the asking rent is **overpriced / fair / a good deal**

---

## The data

- **Source:** [999.md](https://999.md) - apartments for **long-term (monthly) rent**, Chișinău only.
- **How:** 999.md is a JavaScript site, so a normal HTML scraper can't read it. But its frontend
  talks to a public **GraphQL API**, which returns every listing as clean structured JSON - price
  (with currency), area, rooms, floor, sector, heating type, furnishing, even GPS coordinates. So
  my scraper (`scrape_999.py`) just queries that API directly. No HTML parsing, no headless browser.
- **Responsibly:** I filter to exactly what I need server-side (monthly rent + Chișinău), use the
  API's built-in duplicate collapsing, add a 1-second pause between requests, and save incrementally.
- **Size:** **4,463** listings scraped, **4,279 after cleaning** (drop missing area/price and trim
  the worst 1% of rent-per-m² values, which are almost always data-entry errors).
- **Currency:** ~95% are quoted in EUR, the rest in MDL/USD - I normalize everything to EUR at a
  fixed rate (19.5 MDL/EUR, BNM mid-2026).
- Collected July 2026.
