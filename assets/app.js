const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit");
const promptEl = document.getElementById("prompt");
const relationshipEl = document.getElementById("relationship");
const parsedEl = document.getElementById("parsed");
const diagramEl = document.getElementById("diagram");
const selectionScreen = document.getElementById("gallery-selection");
const galleryView = document.getElementById("gallery-view");
const galleryLabel = document.getElementById("gallery-label");
const changeGalleryBtn = document.getElementById("change-gallery");
const resultModal = document.getElementById("result-modal");
const closeModalBtn = document.getElementById("close-modal");
const cards = Array.from(document.querySelectorAll(".card"));

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

function clearSelections() {
  Array.from(document.querySelectorAll("input[name='selected']")).forEach((input) => {
    input.checked = false;
  });
}

function filterGallery(galleryId) {
  cards.forEach((card) => {
    const filename = card.dataset.filename || "";
    const isMatch = filename.startsWith(`${galleryId}-`);
    card.hidden = !isMatch;
    const checkbox = card.querySelector("input[name='selected']");
    if (checkbox) {
      checkbox.disabled = !isMatch;
      if (!isMatch) {
        checkbox.checked = false;
      }
    }
  });
}

function showGallery(galleryId) {
  filterGallery(galleryId);
  galleryLabel.textContent = `Gallery ${galleryId}`;
  selectionScreen.hidden = true;
  galleryView.hidden = false;
  document.body.classList.remove("selection-only");
  setStatus("");
  clearSelections();
  resetOutput();
}

function showSelection() {
  selectionScreen.hidden = false;
  galleryView.hidden = true;
  document.body.classList.add("selection-only");
  setStatus("");
  clearSelections();
  resetOutput();
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
    if (resultModal?.showModal) {
      resultModal.showModal();
    }
    setStatus("Done.");
  } catch (error) {
    setStatus("Network error. Please try again.", true);
  } finally {
    submitBtn.disabled = false;
  }
}

Array.from(document.querySelectorAll("input[name='selected']")).forEach(
  (input) => input.addEventListener("change", enforceSelectionLimit)
);

Array.from(document.querySelectorAll("#gallery-selection [data-gallery]")).forEach(
  (button) => {
    button.addEventListener("click", () => {
      const galleryId = button.dataset.gallery;
      if (galleryId) {
        showGallery(galleryId);
      }
    });
  }
);

changeGalleryBtn?.addEventListener("click", showSelection);

closeModalBtn?.addEventListener("click", () => {
  if (resultModal?.open) {
    resultModal.close();
  }
});

submitBtn.addEventListener("click", runRelationship);

showSelection();
