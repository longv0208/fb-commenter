# Stitch AI Prompts — FB Commenter Desktop

Dùng các prompt dưới trong Google Stitch (stitch.withgoogle.com) để gen UI,
sau đó copy HTML/CSS vào `desktop/renderer/views/`.

Style chung (prepend vào mọi prompt):

```
Dark theme desktop admin panel, dense information layout, Vietnamese labels,
Tailwind CSS, sidebar nav on left with 5 items (Dashboard, Tai khoan, Chay,
Logs, Cai dat), single main content area, no JS framework.
```

## 1. Dashboard / Account list

```
Redesign this dashboard page:
1. LAYOUT: dark background #0f1115, left sidebar 200px with nav
2. TABLE: accounts table with columns checkbox, name, page id, proxy host,
   status badge, last error, action buttons (Start/Stop)
3. BADGES: idle=gray, running=blue, done=green, error=red
4. BUTTONS: "Chay da chon" primary + "Dung tat ca" danger in toolbar above table
5. TOPBAR: app title + global stop button on right
```

## 2. Account form

```
Redesign this form page:
1. LAYOUT: two columns — left accounts list table (name, page id, proxy), right edit form
2. FORM FIELDS: account name (text), cookie (large textarea + file picker),
   page ID (text), proxy URL (text), profile directory (text + browse),
   comment list file (select), checkbox "use persistent profile"
3. BUTTONS: Save (primary), Delete (danger, only when editing), "+ Them" top right
4. MODAL alternative: keep as side-by-side card layout, no modal
```

## 3. Run control

```
Redesign this run panel:
1. LEFT COLUMN: multi-select checklist of accounts (name + page id per row)
2. RIGHT COLUMN: config form — mode radio (UID list / Campaign scan),
   campaign dropdown (shown when campaign mode), delay min/max number inputs,
   headless + dry-run + no-proxy checkboxes
3. BUTTONS: big "Bat dau" primary, red "Dung da chon"
4. BOTTOM CARD: live status table (account, mode, status badge, error)
```

## 4. Log viewer

```
Redesign this log viewer page:
1. TOOLBAR: account dropdown ("Tat ca account" + per account), level filter
   chips (INFO/WARN/ERROR/DEBUG toggles), search input, auto-scroll checkbox,
   Clear + Export buttons
2. LOG AREA: dark console style (#0a0c10), monospace font, colored levels
   (INFO green, WARN yellow, ERROR red, DEBUG gray), account tag in blue,
   auto-scroll to bottom, height fills remaining space
3. LOG LINE: timestamp muted, level colored, [account] accent, message
```

## 5. Settings

```
Redesign this settings page:
1. CARD 1 "Backend & duong dan": JEV API key (password), data root (text),
   default delay min/max (number pair), Save button
2. CARD 2 "Ve ung dung": app description, backend URL display
3. Keep cards max-width 560px, left aligned
```
