(function () {
  "use strict";

  const MODE = window.SINTESI_MODE || "edit";
  const IS_STALE = window.SINTESI_STALE === true;
  const DATA = JSON.parse(document.getElementById("sintesi-json").textContent);
  const offerId = DATA.offer_id;
  const fixedContainer = document.getElementById("fixed-fields");
  const tablesContainer = document.getElementById("dynamic-tables");
  const saveStatus = document.getElementById("save-status");
  const saveButton = document.getElementById("save-btn");
  let errorBanner = document.getElementById("form-error");
  const lastFocusedSelects = new Map();
  let localCounter = 0;
  let dirty = false;
  const DRAFT_KEY = "windtre-sintesi-draft:" + MODE + ":" + (offerId || "new");

  function newLocalId() {
    localCounter += 1;
    return "r" + Date.now() + localCounter;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function setStatus(message) {
    saveStatus.textContent = message;
  }

  function clearError() {
    if (errorBanner) {
      errorBanner.hidden = true;
      errorBanner.textContent = "";
    }
    document.querySelectorAll(".input-error").forEach(function (node) {
      if (!node.closest(".modal")) { node.classList.remove("input-error"); }
    });
    document.querySelectorAll(".field-error").forEach(function (node) {
      if (!node.classList.contains("modal-field-error")) { node.remove(); }
    });
  }

  function showError(message, fieldId) {
    if (fieldId) {
      const field = document.getElementById(fieldId);
      if (field) {
        field.classList.add("input-error");
        field.insertAdjacentElement("afterend", el("p", "field-error", message));
        field.focus();
        field.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
    }
    if (!errorBanner) {
      const main = document.querySelector("main");
      if (main) {
        errorBanner = el("div", "error-banner");
        main.prepend(errorBanner);
      }
    }
    if (errorBanner) {
      errorBanner.textContent = message;
      errorBanner.hidden = false;
      errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      setStatus(message);
    }
  }

  function updateDirtyState() {
    const generateButton = document.getElementById("generate-btn");
    if (generateButton) {
      generateButton.disabled = dirty;
      generateButton.title = dirty
        ? "Salva prima le modifiche (Applica Modifiche) per generare la Sintesi"
        : "";
    }
    if (MODE === "edit" && saveButton) { saveButton.hidden = !dirty; }
    const discardButton = document.getElementById("discard-btn");
    if (discardButton) { discardButton.hidden = !dirty; }
    if (dirty) {
      setStatus("Modifiche non salvate: salva per generare la Sintesi");
    } else if (IS_STALE) {
      setStatus("Sintesi superata: rigenera per aggiornarla");
    } else {
      setStatus("");
    }
    if (saveStatus) { saveStatus.classList.toggle("dirty", dirty); }
  }

  function markDirty() {
    const wasClean = !dirty;
    dirty = true;
    saveDraft();
    if (wasClean) { updateDirtyState(); }
  }

  function markClean() {
    dirty = false;
    clearDraft();
    updateDirtyState();
  }

  function saveDraft() {
    try {
      window.localStorage.setItem(DRAFT_KEY, JSON.stringify(collectPayload()));
    } catch (error) { /* storage non disponibile */ }
  }

  function clearDraft() {
    try { window.localStorage.removeItem(DRAFT_KEY); } catch (error) { /* ignore */ }
  }

  function readDraft() {
    try {
      const raw = window.localStorage.getItem(DRAFT_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function refreshStatusBadge() {
    const badge = document.getElementById("status-badge");
    const statusSelect = document.getElementById("offer-status");
    if (!badge || !statusSelect) { return; }
    const selected = statusSelect.value;
    badge.textContent = selected.toUpperCase();
    badge.className = "tag status-" + selected;
  }

  function refreshAgcomBadge() {
    const badge = document.getElementById("agcom-badge");
    const agcomInput = document.getElementById("agcom-code");
    if (!badge || !agcomInput) { return; }
    const code = agcomInput.value.trim();
    badge.hidden = !code;
    if (code) { badge.textContent = "🏷️ " + code; }
  }

  function renderFixedFields() {
    fixedContainer.textContent = "";
    DATA.fixed_fields.forEach(function (field) {
      let section = fixedContainer.querySelector(
        'section[data-block="' + field.block_code + '"]'
      );
      if (!section) {
        section = el("section", "table-section");
        section.dataset.block = field.block_code;
        section.appendChild(el("h3", "", field.block_title || "Altri campi"));
        section.appendChild(el("div", "field-rows"));
        fixedContainer.appendChild(section);
      }
      const row = el("div", "field-row");
      const input = document.createElement("input");
      input.type = "text";
      input.id = "field-" + field.key;
      input.dataset.key = field.key;
      input.maxLength = 500;
      input.value = field.value || "";
      if (field.source_kind !== "input") { input.disabled = true; }
      const label = el("label", "", field.label);
      label.htmlFor = input.id;
      row.appendChild(label);
      row.appendChild(input);
      section.querySelector(".field-rows").appendChild(row);
    });
  }

  function voceSelect(block, selectedId) {
    const select = el("select", "voce-select");
    block.voci.forEach(function (voce) {
      const option = document.createElement("option");
      option.value = voce.id;
      option.textContent = voce.label;
      if (voce.id === selectedId) { option.selected = true; }
      select.appendChild(option);
    });
    select.addEventListener("focus", function () {
      lastFocusedSelects.set(block.code, select);
    });
    return select;
  }

  function firstVoceId(block) {
    return block.voci.length ? block.voci[0].id : "";
  }

  function separatorRow() {
    const row = el("tr", "group-separator");
    const cell = el("td");
    cell.colSpan = 3;
    row.appendChild(cell);
    return row;
  }

  function removeRow(row) {
    const tbody = row.closest("tbody");
    const previous = row.previousElementSibling;
    if (previous && previous.classList.contains("group-separator")) {
      previous.remove();
    }
    if (tbody) {
      tbody.querySelectorAll("tr[data-parent-local-id='" + row.dataset.localId + "']")
        .forEach(function (child) { child.remove(); });
    }
    row.remove();
    if (tbody) {
      const first = tbody.firstElementChild;
      if (first && first.classList.contains("group-separator")) { first.remove(); }
      updateEmptyState(tbody);
    }
    markDirty();
  }

  function addChild(block, parentRow) {
    let anchor = parentRow;
    let sibling = parentRow.nextElementSibling;
    while (sibling && sibling.dataset.parentLocalId === parentRow.dataset.localId) {
      anchor = sibling;
      sibling = sibling.nextElementSibling;
    }
    const childRow = createRow(block, {
      local_id: newLocalId(),
      parent_local_id: parentRow.dataset.localId,
      voce_id: firstVoceId(block),
      value: ""
    });
    anchor.after(childRow);
    const tbody = parentRow.closest("tbody");
    if (tbody) { updateEmptyState(tbody); }
    markDirty();
  }

  function updateEmptyState(tbody) {
    const emptyRow = tbody.querySelector("tr.empty-row");
    const hasRows = tbody.querySelector("tr.data-row") !== null;
    if (!hasRows && !emptyRow) {
      const row = el("tr", "empty-row");
      const cell = el("td", "",
        'Nessuna voce in questa tabella. Usa "Aggiungi padre" per iniziare.');
      cell.colSpan = 3;
      row.appendChild(cell);
      tbody.appendChild(row);
    } else if (hasRows && emptyRow) {
      emptyRow.remove();
    }
  }

  function createRow(block, row) {
    const localId = row.local_id || row.id;
    const parentLocalId = row.parent_local_id || row.parent_row_id || "";
    const voceId = row.voce_id || "";
    const tr = el("tr", parentLocalId ? "data-row child-row" : "data-row parent-row");
    tr.dataset.localId = localId;
    tr.dataset.parentLocalId = parentLocalId;
    tr.dataset.voceId = voceId;
    tr.dataset.block = block.code;

    const voceCell = document.createElement("td");
    voceCell.appendChild(voceSelect(block, voceId));

    const valueCell = document.createElement("td");
    const input = el("input", "value-input");
    input.type = "text";
    input.maxLength = 500;
    input.value = row.value || "";
    valueCell.appendChild(input);

    const actionsCell = document.createElement("td");
    const actions = el("div", "row-actions");
    if (!parentLocalId) {
      const childButton = el("button", "btn small secondary", "+ figlio");
      childButton.type = "button";
      childButton.addEventListener("click", function () { addChild(block, tr); });
      actions.appendChild(childButton);
    }
    const removeButton = el("button", "btn small danger-ghost remove-row", "×");
    removeButton.type = "button";
    removeButton.addEventListener("click", function () { removeRow(tr); });
    actions.appendChild(removeButton);
    actionsCell.appendChild(actions);

    tr.appendChild(voceCell);
    tr.appendChild(valueCell);
    tr.appendChild(actionsCell);
    return tr;
  }

  function addParent(block, card) {
    const tbody = card.querySelector("tbody");
    if (!tbody) { return; }
    if (tbody.querySelector("tr.data-row")) { tbody.appendChild(separatorRow()); }
    tbody.appendChild(createRow(block, {
      local_id: newLocalId(),
      parent_local_id: null,
      voce_id: firstVoceId(block),
      value: ""
    }));
    updateEmptyState(tbody);
    markDirty();
  }

  function renderBlock(block) {
    const card = el("section", "table-section block-card");
    card.dataset.block = block.code;
    card.classList.add(block.layout === "1_col" ? "layout-1-col" : "layout-2-col");

    const header = el("div", "card-header");
    const title = el("h3", "", block.title);
    title.appendChild(el("span", "layout-hint",
      block.layout === "1_col" ? "Tabella a 1 colonna" : "Tabella a 2 colonne"));
    header.appendChild(title);
    const actions = el("div", "row-actions");
    const addParentButton = el("button", "btn small secondary", "Aggiungi padre");
    addParentButton.type = "button";
    addParentButton.addEventListener("click", function () { addParent(block, card); });
    const newVoceButton = el("button", "btn small secondary", "Nuova voce…");
    newVoceButton.type = "button";
    newVoceButton.addEventListener("click", function () { createVoce(block); });
    actions.appendChild(addParentButton);
    actions.appendChild(newVoceButton);
    header.appendChild(actions);
    card.appendChild(header);

    const table = document.createElement("table");
    const tbody = el("tbody");
    tbody.dataset.block = block.code;
    const blockRows = DATA.rows.filter(function (row) { return row.block === block.code; });
    const parents = blockRows.filter(function (row) { return !row.parent_row_id; });
    parents.forEach(function (parent, index) {
      if (index > 0) { tbody.appendChild(separatorRow()); }
      tbody.appendChild(createRow(block, parent));
      blockRows
        .filter(function (row) { return row.parent_row_id === parent.id; })
        .forEach(function (child) { tbody.appendChild(createRow(block, child)); });
    });
    table.appendChild(tbody);
    card.appendChild(table);
    updateEmptyState(tbody);
    return card;
  }

  function renderTables() {
    tablesContainer.textContent = "";
    DATA.blocks.forEach(function (block) {
      tablesContainer.appendChild(renderBlock(block));
    });
  }

  function collectPayload() {
    const fixed = {};
    fixedContainer.querySelectorAll("input[data-key]").forEach(function (input) {
      if (!input.disabled) { fixed[input.dataset.key] = input.value; }
    });
    const rows = [];
    DATA.blocks.forEach(function (block) {
      const tbody = tablesContainer.querySelector("tbody[data-block='" + block.code + "']");
      if (!tbody) { return; }
      const parsed = Array.prototype.map.call(
        tbody.querySelectorAll("tr.data-row"),
        function (tr) {
          return {
            block: block.code,
            local_id: tr.dataset.localId,
            parent_local_id: tr.dataset.parentLocalId || null,
            voce_id: tr.querySelector("select.voce-select").value,
            value: tr.querySelector("input.value-input").value
          };
        }
      );
      parsed
        .filter(function (row) { return !row.parent_local_id; })
        .forEach(function (row) { rows.push(row); });
      parsed
        .filter(function (row) { return row.parent_local_id; })
        .forEach(function (row) { rows.push(row); });
    });
    const payload = { fixed: fixed, rows: rows };
    const nameInput = document.getElementById("offer-name");
    if (nameInput) { payload.name = nameInput.value.trim(); }
    const techSelect = document.getElementById("technology-id");
    if (techSelect) { payload.technology_id = techSelect.value || null; }
    const statusSelect = document.getElementById("offer-status");
    if (statusSelect) { payload.status = statusSelect.value; }
    const agcomInput = document.getElementById("agcom-code");
    if (agcomInput) { payload.agcom_code = agcomInput.value.trim(); }
    return payload;
  }

  function collectAnagrafica() {
    return {
      name: document.getElementById("offer-name").value.trim(),
      segment_id: document.getElementById("segment-id").value,
      technology_id: document.getElementById("technology-id").value || null
    };
  }

  function formatSpeedJs(value, direction) {
    const number = Number(value);
    if (!Number.isFinite(number)) { return ""; }
    return number.toFixed(2).replace(".", ",") + " Mbps in " + direction;
  }

  function setDerivedValue(key, value) {
    const input = document.querySelector('input[data-key="' + key + '"]');
    if (input) { input.value = value; }
  }

  function refreshTechnologyBadge() {
    const badge = document.getElementById("technology-badge");
    const select = document.getElementById("technology-id");
    if (!badge || !select) { return; }
    const option = select.selectedOptions[0];
    const url = option && option.dataset.badge ? option.dataset.badge : "";
    if (url) {
      badge.src = url;
      badge.alt = "Bollino " + option.textContent;
      badge.hidden = false;
    } else {
      badge.hidden = true;
      badge.removeAttribute("src");
      badge.alt = "Bollino tecnologia";
    }
  }

  function refreshDerivedFields() {
    const nameInput = document.getElementById("offer-name");
    if (nameInput) { setDerivedValue("nome_offerta", nameInput.value); }
    const techSelect = document.getElementById("technology-id");
    if (techSelect) {
      const option = techSelect.selectedOptions[0];
      const download = option && option.dataset.download ? option.dataset.download : "";
      const upload = option && option.dataset.upload ? option.dataset.upload : "";
      setDerivedValue("velocita_download", download ? formatSpeedJs(download, "Download") : "");
      setDerivedValue("velocita_upload", upload ? formatSpeedJs(upload, "Upload") : "");
    }
  }

  async function createOffer() {
    clearError();
    const anagrafica = collectAnagrafica();
    if (!anagrafica.name) {
      showError("Inserisci il nome dell'offerta", "offer-name");
      return;
    }
    setStatus("Creazione offerta…");
    try {
      const body = Object.assign({}, anagrafica, collectPayload());
      const response = await fetch("/api/offers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (response.status === 201) {
        const created = await response.json();
        markClean();
        window.location.href = "/offers/" + created.id + "?created=1";
        return;
      }
      const problem = await response.json().catch(function () { return null; });
      const detail = problem && typeof problem.detail === "string"
        ? problem.detail : "HTTP " + response.status;
      if (response.status === 422 && /nome/i.test(detail)) {
        showError(detail, "offer-name");
        return;
      }
      throw new Error(detail);
    } catch (error) {
      confirmModal.openError("Impossibile creare l'offerta: " + error.message);
    }
  }

  function formatDateTime(date) {
    const pad = function (value) { return String(value).padStart(2, "0"); };
    return pad(date.getDate()) + "/" + pad(date.getMonth() + 1) + "/" +
      date.getFullYear() + " " + pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  async function saveSintesi() {
    setStatus("Salvataggio…");
    try {
      const response = await fetch("/api/offers/" + offerId + "/sintesi", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectPayload())
      });
      if (!response.ok) {
        const problem = await response.json().catch(function () { return null; });
        const detail = problem && typeof problem.detail === "string"
          ? problem.detail : "HTTP " + response.status;
        if (response.status === 422 && /nome/i.test(detail)) {
          showError(detail, "offer-name");
        }
        throw new Error(detail);
      }
      markClean();
      setStatus("");
      const updated = document.getElementById("offer-updated-at");
      if (updated) {
        updated.textContent = formatDateTime(new Date());
      }
      confirmModal.openInfo("Modifiche applicate",
        "Le modifiche sono state applicate correttamente all'offerta.");
    } catch (error) {
      setStatus("");
      confirmModal.openError("Impossibile applicare le modifiche: " + error.message);
    }
  }

  async function generateDocx(force) {
    if (!force && dirty) {
      setStatus("Salva prima la Sintesi");
      return;
    }
    setStatus("Generazione in corso…");
    try {
      const url = "/api/offers/" + offerId + "/generate" + (force ? "?force=true" : "");
      const response = await fetch(url, { method: "POST" });
      const payload = await response.json().catch(function () { return null; });
      if (!response.ok) {
        const detail = payload && typeof payload.detail === "string"
          ? payload.detail : "HTTP " + response.status;
        throw new Error(detail);
      }
      if (payload && payload.generated === false) {
        setStatus("");
        confirmModal.open("Sintesi già aggiornata",
          "Non ci sono modifiche da includere: la Sintesi corrente è già aggiornata. " +
            "Vuoi generare comunque un nuovo file?",
          "Genera comunque",
          function () { generateDocx(true); },
          "Non generare");
        return;
      }
      setStatus("Documento generato");
      window.location.reload();
    } catch (error) {
      setStatus("");
      confirmModal.openError("Generazione non riuscita: " + error.message);
    }
  }

  async function createVoceRequest(block, label) {
    const normalized = label.trim().toLowerCase();
    const existing = block.voci.find(function (item) {
      return item.label.trim().toLowerCase() === normalized;
    });
    if (existing) {
      return 'La voce "' + existing.label +
        '" esiste già in questa tabella: scegli un altro nome.';
    }
    setStatus("Creazione voce…");
    try {
      const response = await fetch("/api/voci", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ block_id: block.id, label: label.trim() })
      });
      if (!response.ok) {
        const problem = await response.json().catch(function () { return null; });
        const detail = problem && typeof problem.detail === "string"
          ? problem.detail : "HTTP " + response.status;
        setStatus("");
        return "Creazione voce non riuscita: " + detail;
      }
      const created = await response.json();
      const voce = { id: created.id, label: created.label };
      const isNew = !block.voci.some(function (item) { return item.id === voce.id; });
      if (isNew) {
        block.voci.push(voce);
        const selects = tablesContainer.querySelectorAll(
          "tbody[data-block='" + block.code + "'] select.voce-select"
        );
        selects.forEach(function (select) {
          const option = document.createElement("option");
          option.value = voce.id;
          option.textContent = voce.label;
          select.appendChild(option);
        });
      }
      const target = lastFocusedSelects.get(block.code);
      if (target) { target.value = voce.id; }
      markDirty();
      setStatus("Voce creata");
      window.setTimeout(function () { if (!dirty) { setStatus(""); } }, 3000);
      return null;
    } catch (error) {
      setStatus("");
      return "Creazione voce non riuscita: " + error.message;
    }
  }

  function createVoce(block) {
    confirmModal.openPrompt("Nuova voce",
      'Nuova voce per "' + block.title + '":', "Nome della voce", "Crea voce",
      function (label) { return createVoceRequest(block, label); });
  }

  renderFixedFields();
  renderTables();

  document.addEventListener("input", function (event) {
    const target = event.target;
    if (!(target instanceof Element)) { return; }
    clearError();
    if (target.closest("#fixed-fields, #dynamic-tables, #offer-name, #segment-id, #agcom-code, #offer-status, #technology-id")) {
      markDirty();
      if (target.id === "agcom-code") { refreshAgcomBadge(); }
      if (target.id === "offer-name") { refreshDerivedFields(); }
    }
  });

  document.addEventListener("change", function (event) {
    const target = event.target;
    if (!(target instanceof Element)) { return; }
    if (target.closest("#fixed-fields, #dynamic-tables, #segment-id, #agcom-code, #offer-status, #technology-id")) {
      markDirty();
      if (target.id === "agcom-code") { refreshAgcomBadge(); }
      if (target.id === "offer-status") { refreshStatusBadge(); }
      if (target.id === "technology-id") {
        refreshDerivedFields();
        refreshTechnologyBadge();
      }
    }
  });

  const confirmModal = window.W3Modal;

  function confirmUnsaved(confirmLabel, action, messageOverride) {
    const title = MODE === "new" ? "Offerta non creata" : "Modifiche non salvate";
    const message = messageOverride || (MODE === "new"
      ? "L'offerta non è stata ancora creata. Se esci ora, i dati inseriti andranno persi."
      : "Ci sono modifiche non salvate. Se esci o ricarichi la pagina, andranno perse.");
    confirmModal.open(title, message, confirmLabel, action, "Resta qui", null,
      { confirm: "btn danger" });
  }

  function maybeShowCreatedMessage() {
    if (MODE !== "edit") { return; }
    const params = new URLSearchParams(window.location.search);
    if (params.get("created") !== "1") { return; }
    confirmModal.openInfo("Offerta creata",
      "L'offerta è stata creata correttamente. Puoi completare la Sintesi e applicare le modifiche con \"Applica Modifiche\".");
    if (window.history.replaceState) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }

  function restoreDraft(payload) {
    const nameInput = document.getElementById("offer-name");
    if (nameInput && typeof payload.name === "string") { nameInput.value = payload.name; }
    const techSelect = document.getElementById("technology-id");
    if (techSelect && "technology_id" in payload) {
      techSelect.value = payload.technology_id || "";
    }
    const statusSelect = document.getElementById("offer-status");
    if (statusSelect && payload.status) { statusSelect.value = payload.status; }
    const agcomInput = document.getElementById("agcom-code");
    if (agcomInput && typeof payload.agcom_code === "string") {
      agcomInput.value = payload.agcom_code;
    }
    if (payload.fixed) {
      fixedContainer.querySelectorAll("input[data-key]").forEach(function (input) {
        const key = input.dataset.key;
        if (!input.disabled && Object.prototype.hasOwnProperty.call(payload.fixed, key)) {
          input.value = payload.fixed[key];
        }
      });
    }
    if (Array.isArray(payload.rows)) {
      DATA.rows = payload.rows.map(function (row) {
        return {
          id: row.local_id,
          block: row.block,
          parent_row_id: row.parent_local_id || null,
          voce_id: row.voce_id,
          value: row.value
        };
      });
      renderTables();
    }
    refreshDerivedFields();
    refreshStatusBadge();
    refreshAgcomBadge();
    markDirty();
  }

  function maybeRestoreDraft() {
    const draft = readDraft();
    if (!draft) { return; }
    confirmModal.open("Modifiche non salvate",
      "Abbiamo recuperato delle modifiche non salvate. Vuoi riprenderle?",
      "Riprendi le modifiche",
      function () { restoreDraft(draft); },
      "Scarta",
      function () { clearDraft(); },
      { cancel: "btn danger-ghost" });
  }

  function requestSave() {
    clearError();
    const nameInput = document.getElementById("offer-name");
    if (nameInput && !nameInput.value.trim()) {
      showError("Inserisci il nome dell'offerta", "offer-name");
      return;
    }
    confirmModal.open("Applica modifiche",
      "Confermi di voler applicare le modifiche all'offerta?", "Applica", saveSintesi);
  }

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof Element) || !dirty) { return; }
    const link = target.closest("a[href]");
    if (!link) { return; }
    const href = link.getAttribute("href") || "";
    if (href.startsWith("#") || href.startsWith("http") || link.hasAttribute("download")) {
      return;
    }
    event.preventDefault();
    confirmUnsaved(MODE === "new" ? "Esci senza creare" : "Esci senza salvare", function () {
      dirty = false;
      clearDraft();
      window.location.href = link.href;
    });
  });

  if (MODE === "new") {
    saveButton.addEventListener("click", createOffer);
    refreshDerivedFields();
    refreshStatusBadge();
    refreshAgcomBadge();
    maybeRestoreDraft();
  } else {
    saveButton.addEventListener("click", requestSave);
    const generateButton = document.getElementById("generate-btn");
    if (generateButton) {
      generateButton.addEventListener("click", function () { generateDocx(false); });
    }
    const discardButton = document.getElementById("discard-btn");
    if (discardButton) {
      discardButton.addEventListener("click", function () {
        if (!dirty) { window.location.reload(); return; }
        confirmUnsaved("Ripristina", function () {
          dirty = false;
          clearDraft();
          window.location.reload();
        }, "Le modifiche non salvate andranno perse e l'offerta tornerà all'ultima versione salvata.");
      });
    }
    updateDirtyState();
    refreshStatusBadge();
    refreshAgcomBadge();
    refreshTechnologyBadge();
    maybeShowCreatedMessage();
    maybeRestoreDraft();
  }
})();
