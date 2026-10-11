(function () {
  "use strict";

  function normalizeName(value) {
    return value.trim().toLowerCase();
  }

  var existingNames = new Set(
    Array.prototype.map.call(
      document.querySelectorAll(".duplicate-offer"),
      function (button) { return normalizeName(button.dataset.offerName); }
    )
  );

  async function duplicateOffer(offerId, newName) {
    try {
      const response = await fetch("/api/offers/" + offerId + "/duplicate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName })
      });
      if (response.status === 201) {
        window.location.reload();
        return null;
      }
      const problem = await response.json().catch(function () { return null; });
      const detail = problem && typeof problem.detail === "string"
        ? problem.detail : "HTTP " + response.status;
      return "Duplicazione non riuscita: " + detail;
    } catch (error) {
      return "Duplicazione non riuscita: " + error.message;
    }
  }

  document.querySelectorAll(".duplicate-offer").forEach(function (button) {
    button.addEventListener("click", function () {
      const offerId = button.dataset.offerId;
      const offerName = button.dataset.offerName;
      window.W3Modal.openPrompt(
        "Duplica offerta",
        'Nuovo nome per la copia di "' + offerName + '":',
        "Nome offerta",
        "Duplica",
        function (newName) {
          if (existingNames.has(normalizeName(newName))) {
            return 'Un\'offerta con nome "' + newName + '" esiste già: scegli un altro nome.';
          }
          return duplicateOffer(offerId, newName);
        }
      );
    });
  });

  async function deleteOffer(offerId) {
    try {
      const response = await fetch("/api/offers/" + offerId, { method: "DELETE" });
      if (response.status === 204) {
        window.location.reload();
        return;
      }
      const problem = await response.json().catch(function () { return null; });
      const detail = problem && typeof problem.detail === "string"
        ? problem.detail : "HTTP " + response.status;
      throw new Error(detail);
    } catch (error) {
      window.W3Modal.openError("Eliminazione non riuscita: " + error.message);
    }
  }

  document.querySelectorAll(".delete-offer").forEach(function (button) {
    button.addEventListener("click", function () {
      const offerId = button.dataset.offerId;
      const offerName = button.dataset.offerName;
      window.W3Modal.open(
        "Eliminare l'offerta?",
        'L\'offerta "' + offerName + '" e i suoi dati (Sintesi, righe, documenti ' +
          "generati) verranno eliminati definitivamente. L'operazione non può " +
          "essere annullata.",
        "Elimina",
        function () { deleteOffer(offerId); },
        "Annulla",
        null,
        { confirm: "btn danger" }
      );
    });
  });
})();
