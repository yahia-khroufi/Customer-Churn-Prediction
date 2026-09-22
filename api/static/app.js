"use strict";

const labels = {
  gender: "Genre", SeniorCitizen: "Client senior", Partner: "En couple", Dependents: "Personnes à charge",
  tenure: "Ancienneté (mois)", MonthlyCharges: "Mensualité ($)", TotalCharges: "Total facturé ($)",
  Contract: "Type de contrat", PaperlessBilling: "Facture dématérialisée", PaymentMethod: "Mode de paiement",
  PhoneService: "Téléphonie", MultipleLines: "Lignes multiples", InternetService: "Accès internet",
  OnlineSecurity: "Sécurité en ligne", OnlineBackup: "Sauvegarde en ligne", DeviceProtection: "Protection des appareils",
  TechSupport: "Assistance technique", StreamingTV: "Streaming TV", StreamingMovies: "Streaming films"
};
const translations = {Yes:"Oui",No:"Non",Male:"Homme",Female:"Femme",0:"Non",1:"Oui",DSL:"ADSL","Fiber optic":"Fibre optique","No phone service":"Sans téléphonie","No internet service":"Sans internet","Month-to-month":"Mensuel","One year":"Un an","Two year":"Deux ans","Electronic check":"Chèque électronique","Mailed check":"Chèque postal","Bank transfer (automatic)":"Virement automatique","Credit card (automatic)":"Carte bancaire automatique"};
const groups = {"profile-fields":["gender","SeniorCitizen","Partner","Dependents"],"billing-fields":["tenure","Contract","MonthlyCharges","TotalCharges","PaymentMethod","PaperlessBilling"],"service-fields":["PhoneService","MultipleLines","InternetService","OnlineSecurity","OnlineBackup","DeviceProtection","TechSupport","StreamingTV","StreamingMovies"]};
const internetFields = ["OnlineSecurity","OnlineBackup","DeviceProtection","TechSupport","StreamingTV","StreamingMovies"];
const exampleNew = {gender:"Female",SeniorCitizen:0,Partner:"No",Dependents:"No",tenure:5,PhoneService:"Yes",MultipleLines:"No",InternetService:"Fiber optic",OnlineSecurity:"No",OnlineBackup:"No",DeviceProtection:"No",TechSupport:"No",StreamingTV:"Yes",StreamingMovies:"Yes",Contract:"Month-to-month",PaperlessBilling:"Yes",PaymentMethod:"Electronic check",MonthlyCharges:95.5,TotalCharges:477.5};
const exampleLoyal = {...exampleNew,Partner:"Yes",Dependents:"Yes",tenure:60,InternetService:"DSL",OnlineSecurity:"Yes",OnlineBackup:"Yes",DeviceProtection:"Yes",TechSupport:"Yes",Contract:"Two year",PaymentMethod:"Bank transfer (automatic)",MonthlyCharges:65,TotalCharges:3900};
const form = document.getElementById("customer-form");
const submit = document.getElementById("submit");
let lastResult = null;
let revision = 0;
let ready = false;
let busy = false;

function setStatus(ok) {
  ready = ok;
  for (const id of ["health-dot","side-dot"]) document.getElementById(id).className = "status-dot " + (ok ? "ok" : "error");
  document.getElementById("health-status").textContent = ok ? "Modèle disponible" : "Modèle indisponible";
  document.getElementById("side-status").textContent = ok ? "API connectée" : "API indisponible";
  submit.disabled = !ready || busy;
}
function changed() {
  revision += 1;
  if (lastResult) { document.getElementById("stale-notice").hidden = false; document.getElementById("download").disabled = true; }
}
function syncServices() {
  const phoneOff = form.elements.PhoneService.value === "No";
  const lines = form.elements.MultipleLines;
  if (phoneOff) lines.value = "No phone service";
  else if (lines.value === "No phone service") lines.value = "No";
  lines.disabled = phoneOff;
  for (const option of lines.options) option.hidden = !phoneOff && option.value === "No phone service";
  const internetOff = form.elements.InternetService.value === "No";
  for (const key of internetFields) {
    const field = form.elements[key];
    if (internetOff) field.value = "No internet service";
    else if (field.value === "No internet service") field.value = "No";
    field.disabled = internetOff;
    for (const option of field.options) option.hidden = !internetOff && option.value === "No internet service";
  }
}
function fillExample(example) {
  for (const [key,value] of Object.entries(example)) form.elements[key].value = value;
  syncServices(); changed();
}
function showError(message) {
  const error = document.getElementById("error-message");
  error.textContent = message; error.hidden = false;
}
function renderResult(result) {
  lastResult = {...result, analyzed_at: new Date().toISOString()};
  document.getElementById("empty-state").hidden = true;
  document.getElementById("result").hidden = false;
  document.getElementById("stale-notice").hidden = true;
  document.getElementById("download").disabled = false;
  const high = result.prediction === "Yes";
  document.getElementById("score").textContent = (result.churn_probability * 100).toLocaleString("fr-FR",{maximumFractionDigits:1,minimumFractionDigits:1});
  const fill = document.getElementById("risk-fill");
  fill.style.width = `${result.churn_probability * 100}%`; fill.style.background = high ? "#c88942" : "#208b71";
  const badge = document.getElementById("prediction-badge");
  badge.textContent = high ? "Départ prédit · Churn = Yes" : "Maintien prédit · Churn = No";
  badge.className = "prediction-badge" + (high ? " high" : "");
  document.getElementById("result-description").textContent = high ? "Le modèle classe ce profil parmi les clients susceptibles de partir. Ce signal peut aider à prioriser une analyse humaine." : "Le modèle classe ce profil parmi les clients susceptibles de rester. Cela ne garantit pas le comportement futur du client.";
  document.getElementById("result-model").textContent = result.model_name;
  if (matchMedia("(max-width:640px)").matches) document.getElementById("result-title").scrollIntoView({behavior:"smooth",block:"start"});
}
async function init() {
  try {
    const response = await fetch("/schema");
    if (!response.ok) throw new Error("Impossible de charger les champs du formulaire.");
    const schema = await response.json();
    for (const [group,keys] of Object.entries(groups)) {
      for (const key of keys) {
        const wrapper = document.createElement("div"); wrapper.className = "field";
        const label = document.createElement("label"); label.htmlFor = key; label.textContent = labels[key];
        let input;
        if (schema.categories[key]) {
          input = document.createElement("select");
          for (const value of schema.categories[key]) { const option = new Option(translations[value] ?? value, value); input.add(option); }
        } else {
          input = document.createElement("input"); input.type = "number"; input.min = "0";
          input.step = key === "tenure" ? "1" : "0.01";
          input.placeholder = key === "TotalCharges" ? "Facultatif" : "0";
        }
        input.id = key; input.name = key; input.required = key !== "TotalCharges";
        wrapper.append(label,input); document.getElementById(group).append(wrapper);
      }
    }
    fillExample(exampleNew);
    const health = await fetch("/health"); setStatus(health.ok);
    if (!health.ok) showError("Le modèle est indisponible. Vérifiez la sauvegarde du pipeline, puis rechargez la page.");
    const infoResponse = await fetch("/model-info");
    if (infoResponse.ok) {
      const info = await infoResponse.json(); document.getElementById("model-name").textContent = info.model_name;
      const metrics = info.evaluation?.metrics;
      if (metrics) {
        document.getElementById("metric-recall").textContent = (100 * metrics.recall).toFixed(1) + " %";
        document.getElementById("metric-f1").textContent = metrics.f1_score.toFixed(3);
        document.getElementById("metrics-caption").textContent = `Évaluation sur ${info.test_samples ?? "les"} clients du test réservé. Ces scores décrivent le modèle, pas la certitude d'une prédiction individuelle.`;
      }
    } else document.getElementById("model-name").textContent = "Indisponible";
  } catch (error) { setStatus(false); showError(error.message); }
}
form.addEventListener("input", changed);
form.addEventListener("change", () => { syncServices(); changed(); });
document.querySelectorAll("[data-example]").forEach(button => button.addEventListener("click", () => fillExample(button.dataset.example === "new" ? exampleNew : exampleLoyal)));
document.getElementById("reset").addEventListener("click", () => {
  fillExample(exampleNew); lastResult = null; document.getElementById("result").hidden = true;
  document.getElementById("empty-state").hidden = false; document.getElementById("error-message").hidden = true;
});
form.addEventListener("submit", async event => {
  event.preventDefault(); if (!ready || busy) return;
  const requestRevision = revision;
  document.getElementById("error-message").hidden = true;
  const payload = {};
  for (const key of Object.keys(labels)) {
    const value = form.elements[key].value;
    payload[key] = ["SeniorCitizen","tenure","MonthlyCharges","TotalCharges"].includes(key) ? (value === "" ? null : Number(value)) : value;
  }
  busy = true; submit.disabled = true; submit.textContent = "Analyse en cours…";
  try {
    const response = await fetch("/predict", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),signal:AbortSignal.timeout(20000)});
    const result = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(result.detail) ? result.detail.map(item => item.msg).join(" ") : result.detail;
      throw new Error(detail || "L'analyse n'a pas pu aboutir.");
    }
    if (revision !== requestRevision) throw new Error("Le profil a changé pendant l'analyse. Relancez-la avec les nouvelles valeurs.");
    renderResult(result);
  } catch (error) { showError(error.name === "TimeoutError" ? "Le serveur met trop de temps à répondre. Réessayez." : error.message); }
  finally { busy = false; submit.disabled = !ready; submit.textContent = "Analyser ce client ↗"; }
});
document.getElementById("download").addEventListener("click", () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)],{type:"application/json"}));
  const link = document.createElement("a"); link.href = url; link.download = "churn-prediction.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
init();
