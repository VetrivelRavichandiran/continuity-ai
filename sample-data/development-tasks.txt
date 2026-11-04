ADR-1 Development Task Records
Last updated: 2 October 2026
Owner of record: David Okafor (project management)

TASK LIST
=========

T-01  Requirements freeze
      Status: Completed (28 May 2026)
      Notes: Signed off by all four team members.

T-02  Prototype v1 assembly
      Status: Completed (24 July 2026)
      Notes: Assembled with centralised compute design; later reworked.

T-03  Architecture change to distributed design
      Status: Completed (14 August 2026)
      Owner: Priya Nair
      Notes: Motor control moved to dedicated controller. Centralised design
      could not meet the 50 ms control loop latency under perception load.

T-04  Motor controller selection
      Status: Completed (12 September 2026)
      Owner: Priya Nair
      Notes: Controller A (VoltDrive VD-480) selected over Controller B and C.
      Thermal performance was the deciding factor.

T-05  Motor testing on v1 prototype
      Status: In progress
      Owner: Marcus Chen
      Due: 20 October 2026
      Notes: Back-to-back thermal bench done. Full-load cycle testing ongoing.
      Final sign-off owner not yet assigned (Priya departing).

T-06  Communication module integration
      Status: In progress
      Owner: Elena Rodriguez
      Due: 30 September 2026 (slipped)
      Notes: 9 of 14 test cases executed and passed as of 28 September.
      Cases 10-14 blocked on the load bank, available early October.

T-07  Resolve communication timeout issue (ADR-142)
      Status: Blocked
      Owner: Elena Rodriguez
      Notes: Workaround applied (retry window raised to 3 seconds) on 20
      September. Root cause not confirmed. Spectrum survey not yet scheduled.
      Elena on leave 8-20 October.

T-08  Thermal validation of battery pack (milestone M4)
      Status: In progress
      Owner: Marcus Chen
      Due: 31 October 2026
      Notes: 29 September run showed 58 C at rear cell, above the 55 C limit.
      Passive cooling plate approved 10 October; validation with plate pending.

T-09  Fit passive cooling plate to battery compartment
      Status: Pending
      Owner: Marcus Chen
      Notes: Plate ordered; arrives week of 20 October.

T-10  Obtain vendor firmware v2.3 for communication module
      Status: Pending
      Owner: Elena Rodriguez
      Notes: Vendor has not released v2.3 yet. Keep-alive fix expected in it.

T-11  Prototype v2 build (milestone M5)
      Status: Pending
      Owner: Priya Nair (interim owner needed before 15 November)
      Due: 30 November 2026
      Notes: Depends on T-05, T-06, T-08 being complete.

T-12  Handover documentation for incoming engineer
      Status: Pending
      Owner: Priya Nair
      Due: 13 November 2026
      Notes: Must cover controller selection rationale, open thermal issue,
      ADR-142 status and the state of integration testing.

DEPENDENCIES
============

- T-11 depends on T-05, T-06, T-08.
- T-08 depends on T-09 (cooling plate fitted first).
- T-07 depends on the spectrum survey being scheduled.
- T-12 depends on T-05 and T-08 reaching a known state.

OPEN QUESTIONS
==============

- Who is responsible for final sign-off on motor testing after Priya leaves?
- Has the battery overheating issue been resolved with the cooling plate?
  (Results pending as of this update.)
- Is architecture document ADR-ARCH-007 final, or still a draft?
- Which communication protocol configuration is currently approved for the
  cellular fallback link?