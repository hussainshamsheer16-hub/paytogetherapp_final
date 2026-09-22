# PayTogether

## Deploy to Railway

This repository is ready to deploy from GitHub using Railway's Railpack
builder. `railway.json` installs dependencies, collects static files, runs
migrations before each release, and starts Gunicorn on Railway's assigned
`PORT`. It also exposes a lightweight `/health/` endpoint for Railway.

1. Push this project to a private GitHub repository. Do not commit a real
   `.env` file.
2. In Railway, create a project, select **Deploy from GitHub repo**, and pick
   the repository.
3. Add a **PostgreSQL** service before deploying the web service. In the web
   service's Variables tab, add
   `DATABASE_URL=${{Postgres.DATABASE_URL}}` (use the actual database service
   name if it is not `Postgres`). Do not use the local `db.sqlite3` file in
   production; Railway's app filesystem is ephemeral.
4. Add the following web-service variables:

   ```env
   DEBUG=false
   SECRET_KEY=<a-new-long-random-secret>
   STRIPE_SECRET_KEY=<your-stripe-secret-key>
   STRIPE_PUBLISHABLE_KEY=<your-stripe-publishable-key>
   STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-signing-secret>
   STRIPE_CURRENCY=usd
   ```

5. Deploy the service, then generate a public domain in **Settings →
   Networking**. Railway automatically exposes its domain to the application
   through `RAILWAY_PUBLIC_DOMAIN`. For a custom domain, also set:

   ```env
   ALLOWED_HOSTS=your-domain.example
   CSRF_TRUSTED_ORIGINS=https://your-domain.example
   ```

6. For persistent tour and profile image uploads, add a Railway Volume mounted
   at `/data`, then set `MEDIA_ROOT=/data/media` and `SERVE_MEDIA=true`. The
   application can serve those files, but a dedicated object store/CDN is a
   better choice as traffic grows. Without a Volume, Railway's filesystem is
   ephemeral and uploads will disappear on a redeploy.

After the first successful deployment, change the Stripe webhook endpoint to:

```text
https://<your-railway-domain>/api/payments/stripe/webhook/
```

Railway's official [Django deployment guide](https://docs.railway.com/guides/django)
and [PostgreSQL guide](https://docs.railway.com/databases/postgresql) describe
the GitHub and database-service setup used here.

## Stripe payments

This project uses Stripe Checkout for the existing tour settlement payment record (`SettlementPayment`). There is no separate ecommerce `Order` model in this project, so Stripe identifiers and payment state are stored on that existing order-like settlement record.

### Install

Install dependencies from the project directory:

```bash
.venv/bin/pip install -r requirements.txt
```

The official Stripe Python SDK is included in `requirements.txt`.

### Environment variables

Create a `.env` file beside `manage.py` and add:

```env
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_signing_secret
STRIPE_CURRENCY=usd
```

`STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are server-only values. They are never sent to browser JavaScript. `STRIPE_PUBLISHABLE_KEY` is reserved for client-side Stripe integrations; this implementation uses Stripe-hosted Checkout and does not need to expose it.

Use a Stripe-supported currency for your account. The settlement amount is calculated by Django from the database and converted to the currency's smallest unit before the Checkout Session is created.

### Run

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

### Stripe webhook

For local development, forward Stripe events to:

```text
POST /api/payments/stripe/webhook/
```

With the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/api/payments/stripe/webhook/
```

Copy the CLI `whsec_...` value into `STRIPE_WEBHOOK_SECRET`. In production, configure the same endpoint in the Stripe Dashboard and use its signing secret.

### Payment flow

1. A user opens a tour settlement and chooses **Pay with bank card**.
2. The browser sends only the tour and recipient IDs to `POST /api/payments/create-checkout-session/`.
3. Django verifies the authenticated user is part of the tour, calculates the settlement amount from expenses, rejects paid settlements, creates or reuses a pending payment record, and creates a Stripe Checkout Session.
4. The browser redirects to Stripe-hosted Checkout.
5. Stripe sends `checkout.session.completed` to the signed webhook.
6. Django verifies the webhook signature, paid status, amount, currency, metadata, and payment record, then atomically changes the record to `paid`.
7. The success page reads payment status from Django. Returning to the page alone never marks a payment paid.

Cancelled and failed Stripe events leave the payment non-paid (`cancelled` or `failed`) and the user can retry.

### API endpoints

- `POST /api/payments/create-checkout-session/` — authenticated tour participant creates/reuses card Checkout.
- `GET /api/payments/status/?session_id=...` — authenticated payer or recipient reads Django-confirmed status.
- `POST /api/payments/stripe/webhook/` — unsigned requests are rejected; Stripe signature verification is required.
- `GET /payments/success/?session_id=...` — status page; it does not approve payment.
- `GET /payments/cancel/` — cancellation page.

COD continues to use the existing recipient approval flow. Card payments are approved by the verified Stripe webhook, not by the recipient UI or success URL.

### Test mode

Use Stripe test keys and test card `4242 4242 4242 4242` with any future expiry and CVC. Run the focused integration tests with:

```bash
.venv/bin/python manage.py test apps.payments apps.reports
```

The tests mock Stripe API calls and cover ownership, amount tampering, already-paid records, invalid signatures, valid idempotent webhooks, and failed/cancelled payments.
