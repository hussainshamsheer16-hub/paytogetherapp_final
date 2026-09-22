# Finalization Notes

This pass completed the project against the SRS/SDS documentation and polished the UI.

## Backend — what was missing and has now been built

- **`apps/expeness` (Expenses)** was empty boilerplate. Added:
  - `Expense` model (tour, paid_by, added_by, amount, category, description)
  - Category choices: Food / Travel / Hotel / Other (per the SDS)
  - List/create and retrieve/update/delete API endpoints, scoped per tour
  - Only the tour's creator or joined members can view/add expenses; only the
    person who logged an expense (or the tour creator) can edit/delete it
- **`apps/reports` (Reports)** was empty boilerplate. Added:
  - `GET /api/tours/<id>/report/` — total spend, each member's fair share
    (simple sum ÷ member count, per the SDS algorithm choice), each member's
    paid/owed balance, a category breakdown, and a minimal "who pays whom"
    settle-up suggestion
  - `GET /api/dashboard/summary/` — aggregates tours/members/expenses/balance
    across every tour a user is part of, for the dashboard stat cards
- **`apps/tour`**: added a members endpoint (`/api/tours/<id>/members/`)
  combining the creator and joined members for the UI's member list and the
  "paid by" picker.
- **`apps/accounts`**: added profile update (`PATCH /api/profile/update/`)
  and change-password (`POST /api/profile/change-password/`) endpoints for
  the Profile screen described in the SDS.
- **Bug fix**: `REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]` in
  `config/settings.py` was a 1-item tuple instead of a string, which crashed
  any list endpoint that didn't set its own `pagination_class` (this is why
  the new Expenses list would have failed). Fixed.
- Minor: `MinValueValidator` on `Expense.amount` now uses `Decimal("0.01")`
  instead of a bare float, avoiding a DRF warning.

All of the above was exercised end-to-end with an API-level smoke test
(register → login → create tour → join → log expenses → pull report →
verify a non-member is denied access) before this list was written.

## Frontend — completed + made more attractive

- **`base.html`**: dropped the legacy Bootstrap navbar/CSS entirely so the
  whole site now runs on one consistent Tailwind design system (a `brand` /
  `mint` color scale, Inter/Poppins fonts). New responsive navbar with a
  mobile menu, and a matching footer. Both are overridable per page via
  `{% block navbar %}` / `{% block footer %}` (used by the dashboard's own
  sidebar layout).
- **`home.html`**: the site root used to render an empty content block
  (literally a blank page under the navbar). Replaced with a real landing
  page — hero, feature grid, and a call to action.
- **Login / Register**: rebuilt without Bootstrap, matching the new design.
- **Dashboard**: wired the previously-static "0" stat cards to the new
  summary endpoint, and added a working profile drawer (edit username/phone,
  change password) backed by the new endpoints.
- **Tour detail page**: this page only ever showed the tour's own fields.
  Added the missing pieces from the SDS — a Members list, an Expenses table
  with an "Add expense" modal (category, amount, payer, description, with
  edit/delete for expenses you're allowed to manage), and a Report section
  (total spend, per-member share/paid/balance table, and settle-up
  suggestions).
- Unified the remaining tour pages (list, create, edit, join) onto the same
  `brand` accent color instead of the leftover default Tailwind blue.

## Running it

```bash
python -m venv myenv
source myenv/bin/activate        # myenv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser # optional
python manage.py runserver
```
