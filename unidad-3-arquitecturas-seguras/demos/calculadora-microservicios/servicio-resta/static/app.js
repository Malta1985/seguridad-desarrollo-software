async function cargarVariante() {
  const el = document.getElementById("variante");
  try {
    const resp = await fetch("/salud");
    const datos = await resp.json();
    el.textContent = datos.servicio || "servicio desconocido";
  } catch (err) {
    el.textContent = "sin conexión con el servidor";
  }
}

async function calcular() {
  const a = Number(document.getElementById("op-a").value);
  const b = Number(document.getElementById("op-b").value);
  const resultadoEl = document.getElementById("op-resultado");
  const crudoEl = document.getElementById("op-crudo");
  resultadoEl.textContent = "Calculando...";
  try {
    const resp = await fetch("/operar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a, b }),
    });
    const datos = await resp.json();
    crudoEl.textContent = JSON.stringify(datos, null, 2);
    if (resp.ok) {
      resultadoEl.textContent = `Resultado: ${datos.resultado}`;
    } else {
      resultadoEl.textContent = `Error: ${datos.detail || "solicitud invalida"}`;
    }
  } catch (err) {
    resultadoEl.textContent = "Error de red: " + err;
  }
}

cargarVariante();
