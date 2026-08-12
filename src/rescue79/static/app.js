"use strict";

const digitButtons = [...document.querySelectorAll(".digit")];
const imageFile = document.querySelector("#imageFile");
const reviewButton = document.querySelector("#reviewButton");
const fileName = document.querySelector("#fileName");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
let expectedDigit = null;
let modelReady = false;
let originalUrl = null;

function updateButton() {
  reviewButton.disabled = !(modelReady && expectedDigit && imageFile.files.length === 1);
}

digitButtons.forEach((button) => {
  button.addEventListener("click", () => {
    expectedDigit = button.dataset.digit;
    digitButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    updateButton();
  });
});

imageFile.addEventListener("change", () => {
  const file = imageFile.files[0];
  fileName.textContent = file ? `선택한 사진: ${file.name}` : "아직 선택한 사진이 없습니다.";
  result.classList.add("hidden");
  updateButton();
});

async function health() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const body = await response.json();
    if (!response.ok || !body.ready) throw new Error(body.detail || "모델 준비 실패");
    modelReady = true;
    status.textContent = "준비되었습니다. 정답과 사진을 고른 뒤 검토를 시작하세요.";
  } catch (error) {
    status.textContent = `모델을 준비하지 못했습니다: ${error.message}`;
  }
  updateButton();
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function displayResult(body, file) {
  if (originalUrl) URL.revokeObjectURL(originalUrl);
  originalUrl = URL.createObjectURL(file);
  document.querySelector("#originalPreview").src = originalUrl;
  document.querySelector("#overlayPreview").src = `data:image/png;base64,${body.overlay_png_base64}`;

  const label = { CORRECT: "정답", INCORRECT: "오답", ABSTAIN: "판정 보류" }[body.verdict] || body.verdict;
  const verdict = document.querySelector("#verdict");
  verdict.textContent = label;
  verdict.className = `verdict ${body.verdict.toLowerCase()}`;
  setText("#reason", body.reason_ko);
  setText("#expected", body.expected_digit);
  setText("#predicted", body.predicted_digit ?? "결과 없음");
  setText("#quality", body.quality.pass ? "통과" : "판정 보류");
  setText("#personCount", String(body.quality.eligible_person_count));
  setText("#jointCount", `${body.quality.visible_joint_count} / 17`);
  setText("#score", body.score_uncalibrated == null ? "측정 안 됨" : body.score_uncalibrated.toFixed(5));
  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

reviewButton.addEventListener("click", async () => {
  const file = imageFile.files[0];
  if (!file || !expectedDigit) return;
  reviewButton.disabled = true;
  status.textContent = "사람과 관절을 찾는 중입니다. 처음에는 모델을 내려받아 몇 분 걸릴 수 있습니다…";
  const form = new FormData();
  form.append("expected_digit", expectedDigit);
  form.append("image", file, file.name);
  try {
    const response = await fetch("/api/review", { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "사진 검토에 실패했습니다.");
    displayResult(body, file);
    status.textContent = "검토가 끝났습니다. 원본과 관절선을 함께 확인하세요.";
  } catch (error) {
    status.textContent = `검토하지 못했습니다: ${error.message}`;
  } finally {
    updateButton();
  }
});

health();
