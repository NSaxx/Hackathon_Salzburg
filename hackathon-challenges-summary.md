# Salzburg Tourism Hackathon: Challenge Summary

Six challenges from the festival partners. Each team picks **exactly one**. The final decision is due **Saturday at 16:00** on the Challenge Board in the hangout area.
Challenge texts as presented on 7 November 2026; data and tech details as of 6 November.

## Overview

| # | Challenge | Phase | Partners | Core problem |
|---|-----------|-------|----------|--------------|
| 01 | Off-Season Potential Nobody Can Prove | Inspiration & Destination Planning | Destinations-Netzwerk Austria, dna | Fragmented data hides off-season potential |
| 02 | Hotel Data Nobody Has Time to Read | Pre-Arrival & On-Site Experience | Berchtold Consulting, NumBirds CRM | Hotel data never reaches staff who could act on it |
| 03 | Access Information Nobody Keeps Current | Planning, Booking & On-Site Experience | Mastercard, UnternehmerTUM | Accessibility info is missing and goes stale |
| 04 | Overnight Data Without Explanation | Destination Planning & Demand Management | TVB Paznaun-Ischgl | Forecast vs. actual deviations stay unexplained |
| 05 | Knowledge AI Assistants Cannot Find | Inspiration, Planning & On-Site Discovery | Upper Austria Tourism | Tourism data is disconnected, so AI cannot answer travellers |
| 06 | One Family Holiday, Four Booking Systems | Activity Discovery, Planning & Booking | Dialogschmiede GmbH for Serfaus-Fiss-Ladis | Families juggle many systems to find and book activities |

---

## 01: Off-Season Potential Nobody Can Prove

**Phase:** Inspiration & Destination Planning
**Partners/contacts:** Destinations-Netzwerk Austria, dna (Christina Wieser); Claudia Ritzenhoff, Philipp Mahlknecht, Michaela Auer, Verena Weitgasser
**Places:** Altenmarkt-Zauchensee, Eben, Radstadt, Wagrain-Kleinarl (pilot region: Salzburger Sportwelt)

**Core idea:** Use tourism data to find untapped off-season potential and turn scattered information into insights that decision-makers (supervisory boards, municipal councils, local businesses) can understand and trust.

**Background**
- dna survey of 53 destination organisations: 75.5% say searching for and compiling data is their biggest time sink; only 28% get data via automated interfaces.
- The data exists (availability, prices, mobile network, guest cards, weather) but sits in separate systems.
- Salzburger Sportwelt has two off-seasons (spring, autumn). 2024/25: 4.9M overnight stays, 59% in winter, February peak. April and May each had about 1.25M stays, less than a third of February.
- Numbers without context mislead: March 2025 stays fell 12.8% and April rose 36%, only because Easter moved.

**What is wanted**
1. Help a destination team find off-season potential by week, place, source market or guest segment, without a data analyst.
2. Turn findings into a case a board, council or local businesses understand and trust within a few minutes.
3. Make it scale to many destinations of different sizes while each data partner keeps control of its own data.

**Key questions the tool should answer:** When exactly do off-seasons start and end? Which guests come anyway, from which markets, and how much do they spend? Which off-season has more potential?

**Data and tech**
- Availability and prices (Lux Active), mobile network data (Hutchison Drei), all at the TTF Data Space
- Guest card data (feratel), COVID period to today, as files
- Cable cars (Snow Space, Shuttleberg, Zauchensee), summer season
- School holidays (Austria Tourism, open data), weather (GeoSphere, open data)
- Cable car opening hours (SLT, Intermaps), restaurant opening hours (Austrian Tourism Data)
- Availability (Austria Tourism), overnight stay forecast (Austria Tourism, open data), off-seasons
- Mobile network data for Wagrain-Kleinarl, Eben, Altenmarkt-Zauchensee, Radstadt
- Benchmarking with neighbouring regions (Schladming-Dachstein, Hochkönig, Zell am See-Kaprun)
- Staff from the tourism associations are on site.

**Sources:** dna member survey 2026 (n = 53); Land Salzburg, Tourismusstatistik 2024/25

---

## 02: Hotel Data Nobody Has Time to Read

**Phase:** Pre-Arrival & On-Site Experience
**Partners/contacts:** Berchtold Consulting (Philipp Berchtold); NumBirds CRM (Andrea Sartori)

**Core idea:** Hotels hold plenty of data (PMS, CRM, website clicks, pre-arrival mails, external info) but it rarely reaches the people dealing with guests. Surface what matters today so staff can act fast, without hours of reporting.

**Background**
- 27% of surveyed hotels run more than seven technology platforms; 27% spend more than 11 hours a week reconciling data; 91% still rely at least partly on manual reporting.
- Receptionists in 80 to 150 room hotels have no time to open four systems before a guest arrives.
- Examples: a guest who viewed the suite page twice gets the standard room; a family checks in before a rainy day and nobody mentions the indoor programme; occupancy drops below forecast during a school break and the hotel only notices on Monday.

**What is wanted**
1. Show hotel staff which guests and situations need attention today, without searching several systems.
2. Work out which combinations of hotel, guest and outside data (weather, events, holidays) change what a hotel should do, and which are noise.
3. Let staff without data or marketing expertise grasp a situation fast enough to act during a shift.

**Data and tech**
- Ibelsa demo account and API (access details to be announced)
- NumBirds demo account and API documentation

**Sources:** Hotel Operations Index 2026; ÖHV Technologieumfrage 2025

---

## 03: Access Information Nobody Keeps Current

**Phase:** Planning, Booking & On-Site Experience
**Partners/contacts:** Mastercard (Dirk Mühlenweg); UnternehmerTUM (Michael Stockerl)

**Core idea:** Accessibility goes beyond physical barriers: mobility, language, digital access, transport and payment. Collect reliable, constantly updated information and deliver it to travellers exactly when they need it.

**Background**
- Pilot context: Traunsee-Almtal, eastern gateway to the Salzkammergut.
- 14.1% of people in Austrian private households report lasting mobility impairments (Statistics Austria). Many more are stopped by other things: a pushchair, a sprained ankle, a weather warning only in German, an app-only ticket, the last bus at 17:00.
- A binary "accessible" label is useless. Real questions: How many steps lead to the entrance? Does the hiking bus take cash? When does the last bus leave in November?
- Answers change with season, weather and timetable. Locals (bus drivers, postal carriers, hosts) know them informally, but nobody collects them. A one-off survey is outdated within a year.

**What is wanted**
1. Collect what stops people (physical, digital, linguistic, financial) from residents, hosts, drivers and guests, and give them a reason to contribute.
2. Turn a single observation (e.g. "three steps, no handrail", "card only, no cash") into information a stranger can rely on, and keep it current without a central team.
3. Deliver the right information at the right moment: while booking, at the bus stop, at the trailhead or at the till.

**Data and tech**
- Partners bring existing infrastructure, timetable and trail data for the region, and access to local hosts and residents.
- Mobility data (VVOÖ, region), mobile network data (TTG)
- A vionmo representative is on site on both festival days.

**Sources:** Statistics Austria

---

## 04: Overnight Data Without Explanation

**Phase:** Destination Planning & Demand Management
**Partners/contacts:** TVB Paznaun-Ischgl (Raphael Tonitz)

**Core idea:** Destinations track overnight stays, forecasts and bed capacity but deviations stay unexplained. Find meaningful patterns, understand why forecast and reality differ, and spot changes early enough to steer demand.

**Background**
- TVB and Feratel provide 244 days of overnight data (summer 2026 through winter 2026/27) and 88 days of bed capacity for early winter.
- The datasets are reported side by side and rarely analysed together.
- A deviation is visible, but the cause (weather, source-market holidays, an event, forecast error, data gap) is unclear. Clarity usually comes too late to adjust marketing.

**What is wanted**
1. Show where demand falls behind forecast or the previous year, where capacity is tight or unused, and why.
2. Derive concrete marketing actions (what, when, where, for which market) and rank them by effect, lead time, feasibility and confidence.
3. Make each recommendation transparent about what it is based on and how reliable it is, given gaps, zero values and limited history.

**Data and tech**
- Overnight stay forecast, plus the overnight data above (daily stays for the previous year, forecast, actuals, bed capacity)
- Representatives are on site on both festival days.

---

## 05: Knowledge AI Assistants Cannot Find

**Phase:** Inspiration, Planning & On-Site Discovery
**Partners/contacts:** Upper Austria Tourism (Johannes Auer)

**Core idea:** Tourism content (TOURDATA) and open data (geodata, weather, water quality, cultural heritage) live in disconnected worlds. Connect and structure them so AI assistants, apps and websites can answer real traveller questions, and so Upper Austria shows up in AI answers.

**Background**
- Hiking and cycling trails, sights, lakes, restaurants and events are maintained in TOURDATA.
- Guests increasingly ask AI assistants ("What should we do this afternoon?", "Can I swim in the Attersee today?", "Where can I buy local cider on the way to Steyr?").
- Without a link between TOURDATA and open data, assistants answer vaguely or not at all.

**What is wanted**
1. Connect TOURDATA and open data to answer concrete guest questions before, during and after a visit.
2. Package this as a small, reusable data service (e.g. an API or MCP tool) usable by apps, websites and AI agents.
3. Structure the data (e.g. schema.org, linked open data) so AI assistants and AI search understand and correctly represent Upper Austria.

**Possible focus areas** (combinations welcome)
- **Conditions:** is today the right day? Weather, water temperature, bathing water quality, closures, opening hours
- **Culinary:** where does regional food come from, who makes it, where can guests taste or buy it
- **Culture:** what happened here, who lived here, what did it look like before

**Evaluation hints**
- Teams show their services in a guest-facing demo (agent, chat, app or web).
- Reusable services count for more than a polished interface.
- Open standards that others in tourism can build on are valued.
- Transparent documentation of data sources, licences and update frequency is expected.

**Data and tech:** TOURDATA (Upper Austria Tourism), Open Data Upper Austria (data.ooe.gv.at), data.gv.at and any other open source of your choice. A representative is on site on both festival days.

---

## 06: One Family Holiday, Four Booking Systems

**Phase:** Activity Discovery, Planning & Booking
**Partners/contacts:** Dialogschmiede GmbH on behalf of Serfaus-Fiss-Ladis (Alexandra Horvath)

**Core idea:** Families must navigate several systems to find and book holiday activities. Help them find experiences matching their kids' ages, interests, time and weather, and turn plans into bookings with less effort.

**Background**
- Serfaus-Fiss-Ladis: about 175,000 guests and 955,000 overnight stays in summer 2025; 1.65M stays in winter 2025/26.
- Content sits in at least four systems: free events (Feratel), registration-based offers (Feratel Experience Shop), cable car experiences (Incert), and A to Z entries (Contwise). Each has its own detail page, design and booking flow.
- Families must compare age limits across pages, check dates against the weather and switch between registration forms and online checkouts. A family with kids aged 4 and 9 has to work out alone which offers suit both children and a rainy Tuesday.

**What is wanted**
1. Let a family quickly see which experiences fit their dates, kids' ages and interests, despite different system structures.
2. Turn a list of fitting experiences into workable days: realistic timing, weather, distances between places.
3. Make "this looks good" become registered or booked in as few steps as possible, whether the offer is free, needs registration or is paid online.

**Data and tech**
- Austrian Tourism Data as the source for events, POIs, tours, hotels and gastronomy
- Feratel (events), Feratel Experience Shop (registration offers), Incert (cable car experiences with online payment and deep links), Feratel/Contwise (providers, A to Z)
- Guest profile: travel dates, companions, kids' age groups (0 to 2, 3 to 6, 7 to 12, 13 to 17), interests
- Live context (open data, added by teams): weather, lift and trail status, opening hours, school holidays
- To be announced: sample data for one summer week (anonymised exports or API), Figma prototype, SFL design guidelines and app constraints

---

## Common Threads

- **Fragmented data** is the root problem in every challenge: it exists but is siloed, unconnected or unexplained.
- **Non-expert users** (managing directors, receptionists, families, travellers) should get insight without analysts or manual digging.
- **Actionable output:** the goal is a decision or action, not a dashboard of numbers.
- **Trust and transparency:** show data sources, reliability and context (01, 04, 05).
- **Scalability and reuse:** works across destinations, partners keep data control (01), reusable API/MCP services (05).
- **Context matters:** weather, holidays, events and timetables change what the data means (01, 02, 04, 06).

## Quick Comparison

| Challenge | Main user | Data richness | Type of solution |
|-----------|-----------|---------------|------------------|
| 01 | Destination managers | Very rich, many sources | Analytics + storytelling |
| 02 | Hotel staff | Demo APIs (details TBA) | Daily briefing / alerting |
| 03 | Travellers and locals | Limited, must be crowdsourced | Crowdsourcing + delivery |
| 04 | TVB / marketing | One focused dataset | Explanatory analytics + recommendations |
| 05 | AI assistants, apps | Open data + TOURDATA | API/MCP service + structured data |
| 06 | Families | Several systems, sample data TBA | Planner + booking flow |

## Deadline

**Pick exactly one challenge by Saturday 16:00** and register on the Challenge Board in the hangout area.
