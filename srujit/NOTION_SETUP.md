# Notion Setup Guide (for the Meeting-to-Action Agent)

You need **two things** from Notion so our app can push tasks into it:
1. An **integration token** (the "password" our code uses to talk to Notion)
2. A **database ID** (which table the tasks land in)

Follow these steps once. Takes ~10 minutes.

---

## Part 1: Create the Integration (get the token)

1. Go to **https://www.notion.so/my-integrations** (log in with your Notion account).
2. Click **“+ New integration”**.
3. Give it a name, e.g. **`Meeting-to-Action Agent`**.
4. Under **Associated workspace**, pick your workspace.
5. Type = **Internal** (default). Leave it internal.
6. Click **Save**.
7. On the next screen, find **“Internal Integration Secret”** → click **Show**, then **Copy**.
   - It looks like `ntn_XXXXXXXX...` (older ones start with `secret_`).
8. Paste it into your `.env` file as:
   ```
   NOTION_API_KEY=ntn_your_copied_token
   ```

> 🔑 This token is a password. Never share it or commit it to git.

---

## Part 2: Create the Tasks Database (the table)

1. In Notion, create a **new page** (left sidebar → **+ Add a page**). Call it e.g. **“Meeting Tasks”**.
2. On the empty page, type `/database` and choose **“Table, Full page”** (a full-page database, not inline).
3. Set up these **properties (columns)** so they match what our agent produces. Click **+** next to the columns to add each one, and set its **type**:

   | Property name | Type | Notes |
   |---|---|---|
   | **Task** | Title | Already exists as the first column, just rename it to `Task`. This is the action item text. |
   | **Owner** | Text | Who's responsible (we keep it Text so unresolved/ambiguous owners still fit). |
   | **Deadline** | Date | Due date (can be empty). |
   | **Status** | Status *(or Select)* | e.g. `Not started`, `In progress`, `Done`. Used later by the follow-up checker. |
   | **Source Quote** | Text | The exact line from the transcript, proves where the task came from. |
   | **Meeting** | Text | Which meeting/date it came from. |

   > Property **names and types must match** what we put in the code. If you rename anything, tell me so I update the code.

---

## Part 3: Share the Database with the Integration (the step everyone forgets)

Creating the integration does **not** automatically give it access. You must connect it to this specific database:

1. Open your **Meeting Tasks** database page.
2. Click the **`•••`** (three dots) menu at the **top-right** of the page.
3. Scroll down to **“+ Add connections”** (older UI: **“Connections”** / **“Add connections”**).
4. Search for **`Meeting-to-Action Agent`** (your integration name) and select it.
5. Confirm. The integration can now read/write this database.

> ❗ If you skip this, the API returns "object not found", because the integration literally can't see the database.

---

## Part 4: Get the Database ID

1. Open the **Meeting Tasks** database as a **full page** in your browser.
2. Look at the URL. It looks like:
   ```
   https://www.notion.so/yourworkspace/246e1f0a1b2c3d4e5f6a7b8c9d0e1f23?v=...
   ```
3. The **32-character string** right before the `?` (here `246e1f0a1b2c3d4e5f6a7b8c9d0e1f23`) is the **Database ID**.
   - If it has dashes, that's fine too.
4. Paste it into `.env`:
   ```
   NOTION_DATABASE_ID=246e1f0a1b2c3d4e5f6a7b8c9d0e1f23
   ```

---

## ✅ Checklist
- [ ] Integration created; token copied into `.env` as `NOTION_API_KEY`
- [ ] Full-page database created with properties: Task, Owner, Deadline, Status, Source Quote, Meeting
- [ ] Integration **connected** to the database (Part 3)
- [ ] Database ID copied into `.env` as `NOTION_DATABASE_ID`

When all four are done, tell me, I'll write a 5-line test script that creates one task in your database so we confirm the connection works before building anything else.
