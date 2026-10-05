# Community feedback spam protection

New submissions require Cloudflare Turnstile verification, pass a hidden honeypot,
and are saved **unapproved**. Both the home page and community board show only
approved posts. The Django admin supports bulk approval and hiding.

The existing database limits each IP to five POST attempts per clock hour,
including failed checks. Counters are shared between web workers/dynos; no Redis
or paid service is required. Expired counters are removed on subsequent attempts.
Only an HMAC of the IP and hour is stored, not the raw IP. People sharing a network
share the limit. This reduces abuse; it does not replace moderation.

## 1. Create a free Turnstile widget

In the [Cloudflare dashboard](https://dash.cloudflare.com/), open **Turnstile**,
add a widget, and choose **Managed** mode. Register:

- `baltimorelifeline.site`
- `www.baltimorelifeline.site`
- Your exact Heroku app hostname if visitors use it (copy it from Heroku).

Copy the **site key** and **secret key**. There is no need to move DNS or hosting
to Cloudflare. See [Cloudflare's setup guide](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/).

## 2. Configure the Heroku app

In Heroku → `baltimore-lifeline` → **Settings → Reveal Config Vars**, add:

| Key | Value |
| --- | --- |
| `TURNSTILE_SITE_KEY` | Your public site key |
| `TURNSTILE_SECRET_KEY` | Your private secret key |
| `TURNSTILE_HOSTNAMES` | `baltimorelifeline.site,www.baltimorelifeline.site` plus any exact Heroku hostname you registered, separated by commas |

Do not include `https://`, paths, or wildcard domains in the hostname list.
Keep the secret in Heroku config; do not commit it or put it in HTML. The form
rejects submissions and disables its submit button until both keys are configured.
Invalid keys, failed verification, unexpected hostnames/actions, and verification
outages never result in saved feedback.

The app automatically trusts Heroku's rightmost `X-Forwarded-For` entry when the
`DYNO` environment variable is present. Locally it uses the direct peer IP. If you
change hosting or add a proxy/CDN in front of Heroku, review this configuration;
otherwise different visitors may share a proxy's limit. Do not blindly trust
the leftmost forwarded IP, which can be supplied by the client.

## 3. Deploy and migrate

Deploy these code changes through your usual Heroku deployment workflow, then run:

```sh
heroku run python manage.py migrate --app baltimore-lifeline
```

The migration creates the shared rate-limit table. Run it before testing feedback
submissions. This implementation does not deploy itself or change production data.

If you do not already have an admin account:

```sh
heroku run python manage.py createsuperuser --app baltimore-lifeline
```

## 4. Review posts and hide existing spam

Open `https://baltimorelifeline.site/admin/` → **Community feedbacks**.

- Filter **Approved → No** to review new submissions.
- Select legitimate posts → **Approve selected feedback (publish)** → **Go**.
- Select existing spam → **Hide selected feedback (mark unapproved)** → **Go**.
- For a clean slate, select all existing posts (use the select-all-results link
  if they span multiple pages), hide them, then approve the legitimate ones.
- Django's existing delete action can permanently remove selected spam if desired.

Existing posts are not automatically hidden or deleted because the code cannot
reliably distinguish legitimate feedback from spam. Already approved spam remains
visible until you hide it. The approval checkbox is also editable on individual posts.

## 5. Check the live setup

1. Open `/community/`, open the form, and confirm the bot check loads.
2. Submit feedback; you should see the review confirmation. It should not be public.
3. Approve it in admin; check that it appears on the community board and home page.
4. Hide it in admin; check that it disappears from both pages.
5. Six attempts from the same IP in one clock hour should return a rate-limit
   message. Failed validation also counts, so avoid locking yourself out during testing.

## Gmail approval notifications

New valid submissions can send an email from one Gmail account to another (or the
same account). The email includes the feedback title, type, name/alias, full text,
and a direct admin review link. Rejected submissions do not trigger email.

1. Sign into the **sending** Gmail account and enable **2-Step Verification** in
   [Google Account Security](https://myaccount.google.com/security).
2. Open [App passwords](https://myaccount.google.com/apppasswords), create one named
   `Baltimore Lifeline`, and copy the generated password. Use this app password,
   not your normal Gmail password. Keep it private.
3. In Heroku → `baltimore-lifeline` → **Settings → Reveal Config Vars**, add:

   | Key | Value |
   | --- | --- |
   | `EMAIL_HOST_USER` | The full Gmail address sending notifications |
   | `EMAIL_HOST_PASSWORD` | The generated Google app password |
   | `FEEDBACK_NOTIFICATION_EMAIL` | `bchang092@gmail.com` (the default if this config var is absent) |

4. Deploy the email changes. **No new database migration is needed for email.**
5. Submit a test through the live feedback form. Check the recipient's Inbox and
   Spam folder. The email's review link should open the saved feedback in admin;
   signing in is still required, and opening the link does not approve the post.

The SMTP server (`smtp.gmail.com`), port (`587`), and TLS are already configured.
`FEEDBACK_SITE_URL` defaults to `https://baltimorelifeline.site`; change it only if
you want review links to use a different trusted site address. The secret is read
only on the server. You do not need to send credentials in chat or edit source code.

If Google does not offer App passwords, check that 2-Step Verification is enabled.
Advanced Protection and some organization/security-key-only account configurations
do not allow them. Changing your Google account password revokes existing app
passwords; generate a replacement and update Heroku if that happens.
See [Google's app password instructions](https://support.google.com/accounts/answer/185833?hl=en).

Email is attempted once after the database commit. If configuration is missing or
delivery fails (including Gmail limits), feedback remains saved and unapproved,
and the app logs a message with its feedback ID. There is no automatic retry or
email backfill for old submissions. Continue checking the admin queue if Gmail
is unavailable. View delivery error messages with:

```sh
heroku logs --tail --app baltimore-lifeline
```

Automated tests use Django's in-memory email backend; they send no real mail.
Live Gmail delivery must be tested after you configure the credentials and deploy.

## Local development and automated tests

Use environment variables (this project does not automatically load `.env` files).
For local manual testing, create a separate development Turnstile widget that
allows `localhost` and `127.0.0.1`, then set its keys and hostnames:

```sh
export TURNSTILE_SITE_KEY=your-development-site-key
export TURNSTILE_SECRET_KEY=your-development-secret-key
export TURNSTILE_HOSTNAMES=localhost,127.0.0.1
python manage.py migrate
python manage.py runserver
```

Use a separate widget to keep local hostnames out of the production widget. The
backend checks both hostname and action; dummy responses may not provide matching
values, so the automated tests mock complete verification responses instead.

Run `python manage.py test`. Tests mock the verification service and cover pending
publication, moderation, invalid/missing/replayed tokens, hostname/action checks,
network failures, missing configuration, honeypots, length limits, shared counters,
counter expiry, forwarded-header spoofing, and CSRF protection.
