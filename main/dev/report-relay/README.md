# The report relay

**Report a problem / Suggest** in the toolkit files each report as an issue in a private GitHub repository, with
its zip of logs committed beside it, through this Cloudflare Worker. The Worker holds the GitHub token, so no secret
is in the toolkit or in this repository. Until the relay's address is set, reports are only saved in
`config/reports/`, or sent to the Discord webhook if one is set.

## Setting it up, once

1. **The reports repository.** On GitHub make a new **private** repository, `ProJ-Yeet/Medieval2-GUI-Toolkit-Reports`
   (any name works; change `REPORTS_REPO` in `wrangler.toml` to match). Add two labels in it: `bug` and `idea`.
2. **The token.** GitHub > Settings > Developer settings > Fine-grained tokens > Generate. Repository access: only
   the reports repository. Permissions: **Contents** read and write, **Issues** read and write. Nothing else.
3. **The Worker.** With a free Cloudflare account, from this folder:

   ```
   npx wrangler login
   npx wrangler deploy
   npx wrangler secret put GITHUB_TOKEN
   ```

   Paste the token when it asks. `deploy` prints the Worker's address, like
   `https://m2-gui-kit-reports.<you>.workers.dev`.
4. **The toolkit.** Put that address in `unittransfer/report.py` as `RELAY`, so every copy of the release sends
   to it. For one copy only, put it in `config/settings.json` as `report_relay`, or as the first line of
   `unittransfer/report_relay.txt`.

## What a report holds

`report.txt` (the words, the kind, the contact), `about.json` (version, Windows, where in the toolkit, mods), the screenshots,
`page_log.json` (every request, message and error the page met), `server_log_tail.txt`, `transfers.json` (the newest
transfer records, with what each was asked and wrote), `settings.json` (addresses and the contact taken out), a
picture of each mod in view (`mod_<name>.txt`: which core files it has and their sizes, how many units and models,
its packs, never its files), each mod's newest `system.log.txt` cut to fit, and the Armory model when ticked.
Before anything leaves, every text loses the Windows user name (in paths too), the computer's name, e-mail
addresses, Steam IDs, IP addresses and any words the reporter lists. **Show what is sent** in the dialog shows each
file as it goes.

## Answering

Comment on the issue. The reporter sees it in the dialog's **Answers to my reports** tab, which the toolkit checks
on start-up every few hours and on **Check now**; the report button then says how many are new. Their replies come
back as comments starting with **Reply from the reporter**. Closing the issue as completed or as not planned shows
them that too.
