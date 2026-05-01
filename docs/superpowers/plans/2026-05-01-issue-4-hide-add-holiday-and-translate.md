# Hide Add-Holiday Button for Non-Admins + Translate Portuguese UI to English

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide the "Add" holiday button completely for non-admin users (no flash on initial render) and translate all remaining Portuguese UI strings in the frontend to English so the UI is fully consistent with the rest of the site.

**Architecture:** Pure frontend visual/text change. Two files: `frontend/index.html` and `frontend/app.js`. The admin-visibility toggle already exists at `app.js:236-243` (`applyAdminVisibility()` is called from `pollStatus()`); the only missing piece is making the button start hidden in the HTML so non-admins never see it briefly during initial load. Translation work converts hard-coded Portuguese strings (titles, labels, placeholders, button text, alert/confirm messages, tooltips, modal headers) to English equivalents and switches the flatpickr date-picker locale from `pt` to default English.

**Tech Stack:** Vanilla HTML, vanilla JavaScript, flatpickr.

**Test strategy:** This is a visual/text-only change with no logic modifications. Per project workflow rules: "Pure documentation, configuration, or visual UI change without logic — skip tests." No tests required. The existing `applyAdminVisibility()` function already implements the show/hide logic correctly; this plan only changes the *initial* HTML state to match what `applyAdminVisibility()` will set for non-admins, eliminating a brief visual flash.

---

## File Structure

- `frontend/index.html` — add `hidden` attribute to `#newHolidayBtn`; translate Portuguese strings (section title, fieldset legend, hint, modal title, form labels/placeholders, button labels).
- `frontend/app.js` — translate Portuguese strings in render functions, modal titles, alert/confirm messages, tooltips; change flatpickr locale from `'pt'` to default English.

No files created. No files deleted.

---

### Task 1: Hide Add-Holiday button by default and translate `frontend/index.html`

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add `hidden` attribute to the Add-Holiday button**

In `frontend/index.html` line 69, change:

```html
<button id="newHolidayBtn" class="add-btn">
```

to:

```html
<button id="newHolidayBtn" class="add-btn" hidden>
```

This makes the button start hidden. The existing `applyAdminVisibility()` in `frontend/app.js:236-243` (called from `pollStatus()` after `/api/status` returns) removes the `hidden` attribute when `state.isAdmin` is true. Non-admins never see the button.

- [ ] **Step 2: Translate the holidays sidebar section title**

Line 68: change `<span class="sidebar-section__title">Feriados</span>` → `<span class="sidebar-section__title">Holidays</span>`.

- [ ] **Step 3: Translate the inline schedules fieldset (inside the account modal)**

Line 242: `<legend>Agendamentos</legend>` → `<legend>Schedules</legend>`

Line 244: `Salve a conta primeiro para configurar agendamentos.` → `Save the account first to configure schedules.`

Line 247: `+ Novo agendamento` → `+ New schedule`

Line 251: `placeholder="Descrição"` → `placeholder="Description"`

Line 256: keep — that's the toggle text "Active" needs to be translated too. Inspect: line 256 reads `<span class="toggle-text">Ativo</span>` → change to `<span class="toggle-text">Active</span>`.

Line 258: `<button type="button" id="scheduleInlineCancel" class="btn btn--ghost">Cancelar</button>` → `Cancel`.

Line 259: `<button type="button" id="scheduleInlineSave" class="btn btn--primary">Salvar agendamento</button>` → `Save schedule`.

- [ ] **Step 4: Translate the holiday modal**

Line 280: `<h3 id="holidayModalTitle" class="modal__title">Novo Feriado</h3>` → `New Holiday`.

Line 291: `<label class="form-label">Data</label>` → `Date`.

Line 292: change the placeholder text `dd/mm/aaaa` → `dd/mm/yyyy` (Portuguese `aaaa` = English `yyyy`; date format itself is unchanged).

Line 295: `<label class="form-label">Descrição</label>` → `Description`.

Line 296: `placeholder="Ex: Natal"` → `placeholder="e.g. Christmas"`.

Line 299: `<button type="button" id="holidayCancelBtn" class="btn btn--ghost">Cancelar</button>` → `Cancel`.

Line 300: `<button type="submit" class="btn btn--primary">Salvar</button>` → `Save`.

- [ ] **Step 5: Manual verification**

Open `frontend/index.html` and grep for any remaining Portuguese tokens:

```bash
grep -nE 'Feriado|Agendamento|Descri[çc][aã]o|Cancelar|Salvar|Editar|Deletar|Ativ[oa]|Desativar|Novo|Erro|Data inv|Apenas|J[áa] existe|Nenhum|aaaa' frontend/index.html
```

Expected: zero matches (all Portuguese tokens removed).

---

### Task 2: Translate Portuguese strings in `frontend/app.js`

**Files:**
- Modify: `frontend/app.js`

- [ ] **Step 1: Translate the holidays empty state**

Line 259: `<span style="font-size:11px">Nenhum feriado cadastrado.</span>` → `No holidays registered.`.

- [ ] **Step 2: Translate holiday list action tooltips**

Line 269: `title="Editar"` → `title="Edit"`.

Line 275: `title="Deletar"` → `title="Delete"`.

- [ ] **Step 3: Translate holiday modal title strings**

Line 294: `$('holidayModalTitle').textContent = holiday ? 'Editar Feriado' : 'Novo Feriado';` → `$('holidayModalTitle').textContent = holiday ? 'Edit Holiday' : 'New Holiday';`.

- [ ] **Step 4: Translate holiday submit alerts**

Line 310: `alert('Data inválida. Use o formato dd/mm/aaaa');` → `alert('Invalid date. Use dd/mm/yyyy format');`.

Line 328: `alert('Apenas o admin pode editar feriados');` → `alert('Only admins can edit holidays');`.

Line 330: `alert('Já existe um feriado nessa data');` → `alert('A holiday already exists on that date');`.

Line 332: `alert('Data inválida (não pode ser passada)');` → `alert('Invalid date (cannot be in the past)');`.

Line 334: `alert(\`Erro: ${msg}\`);` → `alert(\`Error: ${msg}\`);`.

- [ ] **Step 5: Translate the holiday delete confirm and error**

Line 340: `if (!confirm('Deletar este feriado?')) return;` → `if (!confirm('Delete this holiday?')) return;`.

Line 345: `alert(\`Erro: ${e.message}\`);` → `alert(\`Error: ${e.message}\`);`.

- [ ] **Step 6: Translate inline schedule list strings**

Line 608: `<li class="schedules-inline__empty">Nenhum agendamento ainda.</li>` → `No schedules yet.`.

Line 619: `title="${s.enabled ? 'Desativar' : 'Ativar'}"` → `title="${s.enabled ? 'Disable' : 'Enable'}"`.

Line 627: `title="Editar"` → `title="Edit"`.

Line 632: `title="Deletar"` → `title="Delete"`.

- [ ] **Step 7: Translate inline schedule alerts and confirms**

Line 657: `alert(\`Erro: ${e.message}\`);` → `alert(\`Error: ${e.message}\`);`.

Line 674: `if (!confirm('Deletar este agendamento?')) return;` → `if (!confirm('Delete this schedule?')) return;`.

Line 681: `alert(\`Erro: ${e.message}\`);` → `alert(\`Error: ${e.message}\`);`.

Line 690: `alert('Expressão cron inválida. Use 5 campos, ex: "0 7 * * 1-5".');` → `alert('Invalid cron expression. Use 5 fields, e.g. "0 7 * * 1-5".');`.

Line 710: `alert(\`Erro: ${e.message}\`);` → `alert(\`Error: ${e.message}\`);`.

- [ ] **Step 8: Switch flatpickr locale to English**

Lines 770–776 currently:

```js
if (window.flatpickr) {
  flatpickr('#holidayDate', {
    dateFormat: 'd/m/Y',
    allowInput: true,
    locale: (flatpickr.l10ns && flatpickr.l10ns.pt) || 'default',
  });
}
```

Change to (drop the `pt` locale reference; use flatpickr's built-in default English):

```js
if (window.flatpickr) {
  flatpickr('#holidayDate', {
    dateFormat: 'd/m/Y',
    allowInput: true,
  });
}
```

The `index.html` `<script src=".../l10n/pt.js">` import is unused after this change. Leave it alone — removing the script tag is unrelated cleanup outside this issue's scope (just hide the button + translate text). The remaining `pt.js` script tag is harmless.

- [ ] **Step 9: Manual verification**

Grep for remaining Portuguese tokens:

```bash
grep -nE "Feriado|Agendamento|Descri[çc][aã]o|Cancelar|Salvar|Editar|Deletar|Ativ[oa]r|Desativar|Novo|Erro:|Data inv|Apenas|J[áa] existe|Nenhum|Express[ãa]o cron" frontend/app.js
```

Expected: zero matches.

---

### Task 3: Final cross-file verification

**Files:** none modified — verification only.

- [ ] **Step 1: Verify no Portuguese remains in frontend HTML/JS**

```bash
grep -rnE "Feriado|Agendamento|Cancelar|Salvar|Editar|Deletar|Ativ[oa]r|Desativar|Erro:|Nenhum|aaaa" frontend/index.html frontend/app.js
```

Expected: zero matches.

- [ ] **Step 2: Verify the Add-Holiday button starts hidden**

```bash
grep -n 'id="newHolidayBtn"' frontend/index.html
```

Expected: a single line containing both `id="newHolidayBtn"` and `hidden` (in any order).

- [ ] **Step 3: Verify `applyAdminVisibility` still toggles the same button**

```bash
grep -n "newHolidayBtn" frontend/app.js
```

Expected: matches in `applyAdminVisibility` (line ~237) and the click handler in `initEventListeners` (line ~764) — unchanged.

---

## Self-Review

**Spec coverage:**
- Issue body: "if user is common, button stays hidden, without user even knowing it exists" — covered by Task 1 Step 1 (`hidden` attribute) plus the existing `applyAdminVisibility()` logic.
- Issue comment: "convert texts that are in Portuguese to English" — covered by Task 1 Steps 2–4 (HTML) and Task 2 Steps 1–8 (JS + flatpickr locale).

**Placeholders:** none — all steps contain literal before/after text.

**Type consistency:** no types or function signatures changed; only string contents.

**Risk:** zero functional risk. The `hidden` HTML attribute is universally supported; the `applyAdminVisibility()` toggle already uses `setAttribute('hidden','')` / `removeAttribute('hidden')`. Translations are pure string edits.
