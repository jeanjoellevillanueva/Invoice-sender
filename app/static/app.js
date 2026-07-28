async function fetchConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    throw new Error("Failed to load config");
  }
  return response.json();
}

function monthOptions(currentMonth) {
  const [yearText, monthText] = currentMonth.split("-");
  let year = Number(yearText);
  let month = Number(monthText);
  const options = [];
  for (let i = 0; i < 12; i += 1) {
    const value = `${year}-${String(month).padStart(2, "0")}`;
    options.push(value);
    month -= 1;
    if (month === 0) {
      month = 12;
      year -= 1;
    }
  }
  return options;
}

function fillMonthSelect(config) {
  const select = document.getElementById("send_month");
  const previous = select.value;
  const options = monthOptions(config.current_month);
  select.innerHTML = options
    .map((value) => {
      const sent = config.sent_history && config.sent_history[value];
      const label = sent ? `${value} (sent)` : value;
      return `<option value="${value}">${label}</option>`;
    })
    .join("");
  if (previous && options.includes(previous)) {
    select.value = previous;
  } else {
    select.value = config.current_month;
  }
}

function fillForm(config) {
  document.getElementById("send_day").value = config.send_day;
  document.getElementById("recipient_email").value = config.recipient_email || "";
  fillMonthSelect(config);

  const smtp = config.smtp || {};
  document.getElementById("smtp_username").value = smtp.username || "";
  document.getElementById("smtp_password").value = "";
  document.getElementById("smtp_password").placeholder = smtp.password_set
    ? "App password saved — leave blank to keep"
    : "Gmail app password";
  document.getElementById("smtp_from_email").value = smtp.from_email || "";
  document.getElementById("smtp_from_name").value = smtp.from_name || "";

  const invoice = config.invoice || {};
  document.getElementById("invoice_prefix").value = invoice.prefix || "";
  document.getElementById("invoice_last_number").value = invoice.last_number ?? 0;
  document.getElementById("invoice_amount").value = invoice.amount ?? 0;
  document.getElementById("invoice_currency").value = invoice.currency || "Php";
  document.getElementById("description_template").value =
    invoice.description_template || "";

  const by = invoice.issued_by || {};
  document.getElementById("by_name").value = by.name || "";
  document.getElementById("by_address").value = by.address || "";
  document.getElementById("by_phone").value = by.phone || "";
  document.getElementById("by_email").value = by.email || "";

  const to = invoice.issued_to || {};
  document.getElementById("to_name").value = to.name || "";
  document.getElementById("to_address").value = to.address || "";
  document.getElementById("to_abn").value = to.abn || "";

  const pay = invoice.pay_to || {};
  document.getElementById("pay_bank").value = pay.bank_name || "";
  document.getElementById("pay_account_name").value = pay.account_name || "";
  document.getElementById("pay_account_number").value = pay.account_number || "";
  document.getElementById("pay_swift").value = pay.swift_code || "";

  const status = config.already_sent_this_month
    ? `Already sent for ${config.current_month}`
    : `Not sent yet for ${config.current_month}`;
  document.getElementById("status-line").textContent = status;
  document.getElementById("next-invoice").textContent =
    `Next invoice: ${config.next_invoice_preview}`;
  document.getElementById("history").textContent = JSON.stringify(
    config.sent_history || {},
    null,
    2,
  );
}

function showMessage(text, isError) {
  const el = document.getElementById("message");
  el.hidden = false;
  el.textContent = text;
  el.classList.toggle("error", Boolean(isError));
}

function collectPayload() {
  const password = document.getElementById("smtp_password").value;
  const payload = {
    send_day: Number(document.getElementById("send_day").value),
    recipient_email: document.getElementById("recipient_email").value.trim(),
    smtp: {
      username: document.getElementById("smtp_username").value.trim(),
      from_email: document.getElementById("smtp_from_email").value.trim(),
      from_name: document.getElementById("smtp_from_name").value.trim(),
    },
    invoice: {
      prefix: document.getElementById("invoice_prefix").value,
      last_number: Number(document.getElementById("invoice_last_number").value),
      amount: Number(document.getElementById("invoice_amount").value),
      currency: document.getElementById("invoice_currency").value,
      description_template: document.getElementById("description_template").value,
      issued_by: {
        name: document.getElementById("by_name").value,
        address: document.getElementById("by_address").value,
        phone: document.getElementById("by_phone").value,
        email: document.getElementById("by_email").value,
      },
      issued_to: {
        name: document.getElementById("to_name").value,
        address: document.getElementById("to_address").value,
        abn: document.getElementById("to_abn").value,
      },
      pay_to: {
        bank_name: document.getElementById("pay_bank").value,
        account_name: document.getElementById("pay_account_name").value,
        account_number: document.getElementById("pay_account_number").value,
        swift_code: document.getElementById("pay_swift").value,
      },
    },
  };
  if (password) {
    payload.smtp.password = password;
  }
  return payload;
}

async function saveConfig(event) {
  event.preventDefault();
  const response = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectPayload()),
  });
  const data = await response.json();
  if (!response.ok) {
    showMessage(data.detail || "Save failed", true);
    return;
  }
  fillForm(data);
  showMessage("Config saved.");
}

async function sendNow() {
  const button = document.getElementById("send-btn");
  button.disabled = true;
  try {
    const response = await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        month: document.getElementById("send_month").value,
        force: document.getElementById("send_force").checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      showMessage(data.detail || "Send failed", true);
      return;
    }
    if (data.skipped) {
      showMessage(data.message || "Already sent.", true);
    } else {
      showMessage(data.message || "Sent.");
    }
    fillForm(await fetchConfig());
  } catch (error) {
    showMessage(String(error), true);
  } finally {
    button.disabled = false;
  }
}

document.getElementById("config-form").addEventListener("submit", saveConfig);
document.getElementById("send-btn").addEventListener("click", sendNow);

fetchConfig()
  .then(fillForm)
  .catch((error) => showMessage(String(error), true));
