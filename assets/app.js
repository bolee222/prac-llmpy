const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit");
const promptEl = document.getElementById("prompt");
const relationshipEl = document.getElementById("relationship");
const parsedEl = document.getElementById("parsed");
const diagramEl = document.getElementById("diagram");
const modalEl = document.getElementById("result-modal");
const closeButtons = modalEl ? modalEl.querySelectorAll("[data-close]") : [];

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "";
}

function getSelectedIds() {
  return Array.from(document.querySelectorAll("input[name='selected']:checked")).map(
    (input) => input.value
  );
}

function enforceSelectionLimit(event) {
  const selected = getSelectedIds();
  if (selected.length > 2) {
    event.target.checked = false;
    setStatus("You can only select two images.", true);
  } else {
    setStatus("");
  }
}

function resetOutput() {
  relationshipEl.textContent = "";
  parsedEl.textContent = "";
  diagramEl.textContent = "";
}

function openModal() {
  if (!modalEl) return;
  modalEl.classList.add("open");
  modalEl.setAttribute("aria-hidden", "false");
}

function closeModal() {
  if (!modalEl) return;
  modalEl.classList.remove("open");
  modalEl.setAttribute("aria-hidden", "true");
}

async function runRelationship() {
  const selected = getSelectedIds();
  const prompt = promptEl.value.trim();

  if (selected.length !== 2) {
    setStatus("Select exactly two images before running.", true);
    return;
  }

  if (!prompt) {
    setStatus("Please enter a prompt.", true);
    return;
  }

  resetOutput();
  setStatus("Running...", false);
  submitBtn.disabled = true;

  try {
    const response = await fetch("/api/relationship", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_ids: selected, prompt }),
    });

    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || "Request failed.", true);
      return;
    }

    relationshipEl.textContent = data.relationship || "";
    parsedEl.textContent = JSON.stringify(data.parsed, null, 2);
    diagramEl.textContent = data.diagram || "";
    setStatus("Done.");
    openModal();
  } catch (error) {
    setStatus("Network error. Please try again.", true);
  } finally {
    submitBtn.disabled = false;
  }
}

Array.from(document.querySelectorAll("input[name='selected']")).forEach(
  (input) => input.addEventListener("change", enforceSelectionLimit)
);

submitBtn.addEventListener("click", runRelationship);

closeButtons.forEach((button) => {
  button.addEventListener("click", closeModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal();
  }
});
