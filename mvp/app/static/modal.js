(function () {
  "use strict";

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function build() {
    const overlay = el("div", "modal-overlay");
    overlay.hidden = true;
    const dialog = el("div", "modal");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    const title = el("h3", "", "");
    const message = el("p", "modal-message", "");
    const fieldWrap = el("div", "modal-field");
    fieldWrap.hidden = true;
    const field = el("input", "modal-input");
    field.type = "text";
    field.maxLength = 100;
    const fieldError = el("p", "field-error modal-field-error");
    fieldError.hidden = true;
    fieldWrap.appendChild(field);
    fieldWrap.appendChild(fieldError);
    const actions = el("div", "modal-actions");
    const cancel = el("button", "btn secondary", "Resta qui");
    cancel.type = "button";
    const confirm = el("button", "btn");
    confirm.type = "button";
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    dialog.appendChild(title);
    dialog.appendChild(message);
    dialog.appendChild(fieldWrap);
    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    let pendingAction = null;
    let cancelAction = null;
    let submitAction = null;
    let promptMode = false;

    function setFieldError(messageText) {
      if (messageText) {
        fieldError.textContent = messageText;
        fieldError.hidden = false;
        field.classList.add("input-error");
      } else {
        fieldError.hidden = true;
        fieldError.textContent = "";
        field.classList.remove("input-error");
      }
    }

    function close() {
      overlay.hidden = true;
      pendingAction = null;
      cancelAction = null;
      submitAction = null;
      promptMode = false;
      fieldWrap.hidden = true;
      field.value = "";
      setFieldError(null);
      confirm.disabled = false;
    }

    cancel.addEventListener("click", function () {
      const pending = cancelAction;
      close();
      if (pending) { pending(); }
    });
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) { close(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !overlay.hidden) { close(); }
    });
    field.addEventListener("input", function () {
      if (promptMode) { setFieldError(null); }
    });
    field.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && promptMode) {
        event.preventDefault();
        confirm.click();
      }
    });
    confirm.addEventListener("click", async function () {
      if (promptMode) {
        const value = field.value.trim();
        if (!value) {
          setFieldError("Inserisci un nome per la voce");
          field.focus();
          return;
        }
        const submit = submitAction;
        confirm.disabled = true;
        let problemMessage = null;
        try {
          problemMessage = submit ? await submit(value) : null;
        } catch (error) {
          problemMessage = "Errore imprevisto: " + error.message;
        }
        confirm.disabled = false;
        if (overlay.hidden) { return; }
        if (problemMessage) {
          setFieldError(problemMessage);
          field.focus();
          return;
        }
        close();
        return;
      }
      const pending = pendingAction;
      close();
      if (pending) { pending(); }
    });

    return {
      open: function (titleText, messageText, confirmLabel, action,
                      cancelLabel, onCancel, options) {
        const styles = options || {};
        title.textContent = titleText;
        title.className = "";
        message.textContent = messageText;
        confirm.textContent = confirmLabel;
        confirm.className = styles.confirm || "btn";
        cancel.textContent = cancelLabel || "Resta qui";
        cancel.className = styles.cancel || "btn secondary";
        pendingAction = action;
        cancelAction = onCancel || null;
        submitAction = null;
        promptMode = false;
        fieldWrap.hidden = true;
        setFieldError(null);
        cancel.hidden = false;
        overlay.hidden = false;
        cancel.focus();
      },
      openInfo: function (titleText, messageText) {
        title.textContent = titleText;
        title.className = "modal-title-success";
        message.textContent = messageText;
        confirm.textContent = "OK";
        confirm.className = "btn";
        cancel.className = "btn secondary";
        pendingAction = null;
        cancelAction = null;
        submitAction = null;
        promptMode = false;
        fieldWrap.hidden = true;
        setFieldError(null);
        cancel.hidden = true;
        overlay.hidden = false;
        confirm.focus();
      },
      openError: function (messageText) {
        title.textContent = "Errore";
        title.className = "modal-title-error";
        message.textContent = messageText;
        confirm.textContent = "OK";
        confirm.className = "btn";
        cancel.className = "btn secondary";
        pendingAction = null;
        cancelAction = null;
        submitAction = null;
        promptMode = false;
        fieldWrap.hidden = true;
        setFieldError(null);
        cancel.hidden = true;
        overlay.hidden = false;
        confirm.focus();
      },
      openPrompt: function (titleText, messageText, placeholder, confirmLabel, onSubmit) {
        title.textContent = titleText;
        title.className = "";
        message.textContent = messageText;
        field.value = "";
        field.placeholder = placeholder || "";
        fieldWrap.hidden = false;
        setFieldError(null);
        confirm.textContent = confirmLabel;
        confirm.className = "btn";
        confirm.disabled = false;
        cancel.textContent = "Annulla";
        cancel.className = "btn secondary";
        submitAction = onSubmit;
        pendingAction = null;
        cancelAction = null;
        promptMode = true;
        cancel.hidden = false;
        overlay.hidden = false;
        field.focus();
      }
    };
  }

  window.W3Modal = build();
})();
