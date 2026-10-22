# Volunteer schedule maker

**You get:** a volunteer schedule where everyone takes fair turns and nobody is booked on a day they can't come.

**Status:** live

## The problem

Small groups run on volunteers: a church, a sports club, a weekend on-call list. Someone builds
the schedule by hand. They must share turns evenly and skip the days each person can't come. People
ask for help with this on Excel forums:

- "taking into account the days they are not available" ([Microsoft Tech Community](https://techcommunity.microsoft.com/discussions/excelgeneral/how-to-set-up-volunteer-rota/183931))
- "a spreadsheet can be made that will allocate these shifts out" ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5075313/create-an-excel-document-to-work-out-shifts))
- A sports club volunteer schedule by availability and role ([Chandoo forum](https://chandoo.org/forum/threads/allocate-duties-by-availability-and-role.45964/))

## What the page does

1. You type the names, the date range, the weekdays, and how many people each day needs.
2. You tick the days each person is away.
3. It gives everyone the same number of turns where it can, skips away days, and tries not to
   give anyone two turns in a row.
4. You print it, copy it as text, or save it as a CSV for a spreadsheet.

It works offline. It saves to your own browser only. It sends nothing.

## What is fake or missing

- No roles yet (for example, "reader" and "welcomer" on the same day).
- No limits per person, such as "at most twice a month".
- No way for volunteers to mark their own away days. One person types them all.
- Fair means "same number of turns". It does not weigh harder days.

## Pass mark

5 people say it made a real schedule for their group (in an issue, a comment or a message) by
2026-11-21. If not, it is retired.
