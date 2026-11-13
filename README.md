# Efficient AI (Vercel)

Send personalized emails to a CSV or Excel list from your own website on Vercel. Sign in with **Continue with Google**, or use a Gmail App password.

## Files

```
index.html       the app (interface)
api/google.py    "Continue with Google" sign-in
api/send.py      App-password (SMTP) sending, optional
README.md
```

No packages or build step needed.

## 1. Deploy to Vercel

1. Create a GitHub repo and upload these files, keeping the `api` folder.
2. In Vercel: **Add New > Project**, import the repo and click **Deploy**. Leave the framework preset as **Other**.
3. Note your site URL, e.g. `https://bulk-mailer-abc.vercel.app`.

## 2. Set up "Continue with Google" (one time, about 10 minutes)

In **console.cloud.google.com**, signed in as the Google account you'll send from:

1. **Create a project** from the project picker at the top, e.g. "Efficient AI".
2. **Enable the Gmail API**: APIs & Services > Library > search "Gmail API" > Enable.
3. **Set up the sign-in screen** (Google Auth Platform, or "OAuth consent screen"):
   - App name: Efficient AI. Support email: yours. Audience: **External**.
   - Under **Audience > Test users**, add your Gmail address. Only listed test users can sign in.
   - Under **Data Access**, add the scope `https://www.googleapis.com/auth/gmail.send`.
4. **Create the login keys**: Clients (or Credentials) > Create client > **Web application**.
   - **Authorized JavaScript origins**: your Vercel URL, e.g. `https://bulk-mailer-abc.vercel.app`
   - **Authorized redirect URIs**: the same URL
   - Click Create and copy the **Client ID** and **Client secret**.
5. In **Vercel > Settings > Environment Variables** add:

| Name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | the Client ID |
| `GOOGLE_CLIENT_SECRET` | the Client secret |

6. **Redeploy**: Deployments > the latest one > menu > Redeploy.

Open your site and click **Continue with Google**. Google will show **"Google hasn't verified this app"**. That's normal for your own app: click **Continue**, and make sure **"Send email on your behalf"** is ticked.

**Good to know about Google sign-in**
- While the app is in "Testing" mode, Google signs you out after **7 days**, so just click Continue with Google again. Removing that limit requires publishing the app and passing Google's verification, which isn't needed for personal use.
- You stay signed in on that browser, and long sending runs refresh the sign-in automatically.
- Emails go out through the Gmail API from your own account and appear in your Sent folder.

## 3. Optional: App-password method

If you'd rather not use Google sign-in, add these in Vercel instead and use **"Use an App password instead"** on the site:

| Name | Value |
|---|---|
| `SMTP_USER` | your email |
| `SMTP_PASS` | a Google **App password** (Google Account > Security > 2-Step Verification > App passwords) |
| `ACCESS_KEY` | any secret phrase. The site asks for it so strangers can't send from your account |
| `FROM_NAME` | optional sender name |

## Using the app

1. **Connect** with Google (or the access key) and set the **sender name**.
2. **Recipients**: drop in a `.csv`, `.xlsx` or `.xls` file and pick the email column. Invalid emails, duplicates and people already emailed are skipped.
3. **Message**: click a field chip such as `{Name}` to insert it. `{Name|there}` adds a fallback for empty cells. Attachments are optional, up to 3 MB.
4. **Sending pace**: random gap between emails and a daily limit.
5. Check the **Preview**, **Send a test to myself**, then **Start sending**.

**Keep the tab open while sending.** If you close it, reopen the site, load the list and press Start, and already-emailed people are skipped. Sent history is stored in your browser; use **Download sent history** to keep a copy.

Gmail allows about 500 emails a day, Google Workspace about 2,000. For cold outreach, start with 20 to 50 a day.

## Spam & delivery check
Records page > "Spam & delivery check". Add 2-3 of your own Gmail addresses as seed inboxes; during a run each seed gets a copy at the start and every 25 emails, and its real Spam/Inbox label is read via the Gmail API (gmail.readonly scope). Bounces are read from Mailer-Daemon notices in the sender mailbox. Sign out and in once to grant the extra "read email" permission.
