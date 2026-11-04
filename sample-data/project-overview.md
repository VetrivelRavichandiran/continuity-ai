# Autonomous Delivery Robot Development — Project Overview

**Project code:** ADR-1
**Organisation:** SYNAPTECH Robotics
**Project manager:** David Okafor
**Lead engineer:** Priya Nair
**Start date:** 3 May 2026
**Status:** Active — prototype phase

## 1. Purpose

ADR-1 develops a battery-powered autonomous delivery robot for last-mile parcel
delivery in urban environments. The robot is designed to carry up to 15 kg of
parcels over a 12 km route at speeds of up to 15 km/h, navigating sidewalks and
shared pedestrian zones.

## 2. Objectives

1. Ship a working prototype (v2) by 30 November 2026.
2. Pass thermal validation of the 48 V battery pack under full load (milestone M4).
3. Achieve a 95% delivery success rate on the standard 8 km test route.
4. Complete integration testing of the communication module before 10 December 2026.
5. Keep the bill of materials under the approved budget ceiling of $4,200 per unit.

## 3. Team

| Name | Role | Notes |
| --- | --- | --- |
| Priya Nair | Lead engineer | Departing the company on 15 November 2026 |
| Marcus Chen | Power systems engineer | Owns battery and thermal work |
| Elena Rodriguez | Software engineer | Owns navigation and communication software |
| David Okafor | Project manager | Owns planning, safety reviews and reporting |

## 4. System architecture (current)

The robot uses a **distributed architecture** adopted in August 2026. The
original design used a single centralised compute unit for all control. The
current architecture separates the functions:

- **Perception module** — stereo cameras and a forward LiDAR, running obstacle
  detection.
- **Navigation module** — route planning and localisation.
- **Communication module** — LoRa radio for telemetry plus a cellular fallback
  link for dispatch commands.
- **Motor system** — two hub motors driven by a dedicated motor controller.
- **Battery pack** — 48 V Li-ion, 1.5 kWh, with a passive cooling plate added
  in August 2026.
- **Compute unit** — runs perception and navigation; no longer responsible for
  motor control.

## 5. Milestones

| ID | Milestone | Target date | Status |
| --- | --- | --- | --- |
| M1 | Requirements frozen | 28 May 2026 | Completed |
| M2 | Prototype v1 assembled | 24 July 2026 | Completed |
| M3 | Integration testing | 30 September 2026 | In progress |
| M4 | Thermal validation | 31 October 2026 | Pending |
| M5 | Prototype v2 complete | 30 November 2026 | Pending |

## 6. Known constraints

- The lead engineer (Priya Nair) leaves on 15 November 2026; her knowledge must
  be transferred before that date.
- The vendor firmware v2.3 for the communication module is not yet released.
- Battery cell aging data is limited to three months of test cycles.