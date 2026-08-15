async function cargarVariante() {
  const el = document.getElementById("variante");
  try {
    const resp = await fetch("/api/salud");
    const datos = await resp.json();
    el.textContent = datos.servicio || "servicio desconocido";
  } catch (err) {
    el.textContent = "sin conexión con el servidor";
  }
}

const SIMBOLO_OPERACION = { suma: "+", resta: "−", multiplicacion: "×", division: "÷" };

let calcValorInicial = null;  
let calcPasos = [];            
let calcEntrada = "";        
let calcOperadorPendiente = null;
let calcTrasEvaluar = false;  

function calcActualizarPantalla() {
  const pantalla = document.getElementById("calc-pantalla");
  const expresionEl = document.getElementById("calc-expresion");

  pantalla.textContent = calcEntrada !== ""
    ? calcEntrada
    : (calcValorInicial !== null ? String(calcValorInicial) : "0");

  const partes = [];
  if (calcValorInicial !== null) partes.push(String(calcValorInicial));
  for (const paso of calcPasos) partes.push(SIMBOLO_OPERACION[paso.operacion], String(paso.operando));
  if (calcOperadorPendiente) partes.push(SIMBOLO_OPERACION[calcOperadorPendiente]);
  expresionEl.innerHTML = partes.length ? partes.join(" ") : "&nbsp;";
}

function calcDigito(d) {
  if (calcTrasEvaluar) calcLimpiar();
  if (d === "." && calcEntrada.includes(".")) return;
  if (calcEntrada === "0" && d !== ".") calcEntrada = "";
  calcEntrada += d;
  calcActualizarPantalla();
}

function calcBorrar() {
  calcTrasEvaluar = false;
  calcEntrada = calcEntrada.slice(0, -1);
  calcActualizarPantalla();
}

function calcLimpiar() {
  calcValorInicial = null;
  calcPasos = [];
  calcEntrada = "";
  calcOperadorPendiente = null;
  calcTrasEvaluar = false;
  document.getElementById("calc-mensaje").textContent = "";
  calcActualizarPantalla();
}

function calcOperador(nombreOperacion) {
  calcTrasEvaluar = false;
  if (calcValorInicial === null) {
    if (calcEntrada === "") return;
    calcValorInicial = Number(calcEntrada);
  } else if (calcEntrada !== "" && calcOperadorPendiente !== null) {
    calcPasos.push({ operacion: calcOperadorPendiente, operando: Number(calcEntrada) });
  }
  calcEntrada = "";
  calcOperadorPendiente = nombreOperacion;
  calcActualizarPantalla();
}

async function calcIgual() {
  if (calcValorInicial === null || calcOperadorPendiente === null || calcEntrada === "") return;

  const pasos = [...calcPasos, { operacion: calcOperadorPendiente, operando: Number(calcEntrada) }];
  const mensajeEl = document.getElementById("calc-mensaje");
  const pasosEl = document.getElementById("expr-pasos");
  const crudoEl = document.getElementById("expr-crudo");
  mensajeEl.textContent = "Calculando...";
  pasosEl.innerHTML = "";

  try {
    const resp = await fetch("/api/expresion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ valor_inicial: calcValorInicial, pasos }),
    });
    const datos = await resp.json();
    crudoEl.textContent = JSON.stringify(datos, null, 2);

    if (resp.status === 202) {
      mensajeEl.textContent = `Encolado, sin confirmar todavía: ${datos.detail}`;
    } else if (resp.ok) {
      for (const paso of datos.pasos || []) {
        const li = document.createElement("li");
        li.textContent = `${paso.operacion}: ${paso.operandos.join(" , ")} -> ${paso.resultado}`;
        pasosEl.appendChild(li);
      }
      mensajeEl.textContent = `= ${datos.resultado_final}`;
      calcValorInicial = datos.resultado_final;
      calcPasos = [];
      calcEntrada = "";
      calcOperadorPendiente = null;
      calcTrasEvaluar = true;
      cargarHistorial();
    } else {
      mensajeEl.textContent = `Error: ${datos.detail || "solicitud invalida"}`;
    }
  } catch (err) {
    mensajeEl.textContent = "Error de red: " + err;
  }
  calcActualizarPantalla();
}

async function cargarHistorial() {
  const filasEl = document.getElementById("historial-filas");
  try {
    const resp = await fetch("/api/historial?limite=20");
    const datos = await resp.json();
    filasEl.innerHTML = "";
    for (const op of datos.operaciones || []) {
      const tr = document.createElement("tr");
      const operandos = op.expresion
        ? `${op.operando_a} (${op.expresion})`
        : `${op.operando_a} , ${op.operando_b}`;
      tr.innerHTML =
        `<td>${op.id}</td><td>${op.tipo}</td><td>${operandos}</td>` +
        `<td>${op.resultado}</td><td>${op.creado_en}</td>`;
      filasEl.appendChild(tr);
    }
  } catch (err) {
    filasEl.innerHTML = `<tr><td colspan="5">Error de red: ${err}</td></tr>`;
  }
}

calcActualizarPantalla();
cargarVariante();
cargarHistorial();
