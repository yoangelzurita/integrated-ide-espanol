/**
 * Lógica del simulador web de Integrated
 */

// Registro de Service Worker para funcionamiento 100% offline
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').then((reg) => {
      console.log('Integrated Service Worker registrado con éxito:', reg.scope);
    }).catch((err) => {
      console.warn('Error al registrar Service Worker:', err);
      lblEstado.textContent = `No se pudo habilitar el modo offline: ${err.message}`;
    });
  });
}

// Variables del DOM
const editorEspanol = document.getElementById('editorEspanol');
const cppSalida = document.getElementById('cppSalida');
const comboPlacas = document.getElementById('comboPlacas');
const comboEjemplos = document.getElementById('comboEjemplos');
const comboPuerto = document.getElementById('comboPuerto');
const btnMonitorSerial = document.getElementById('btnMonitorSerial');
const btnIniciadorSegundoPlano = document.getElementById('btnIniciadorSegundoPlano');
const panelMonitorSerial = document.getElementById('panelMonitorSerial');
const estadoMonitorSerial = document.getElementById('estadoMonitorSerial');
const comboVelocidadSerie = document.getElementById('comboVelocidadSerie');
const btnConectarMonitor = document.getElementById('btnConectarMonitor');
const btnLimpiarMonitor = document.getElementById('btnLimpiarMonitor');
const btnCerrarMonitor = document.getElementById('btnCerrarMonitor');
const salidaMonitorSerial = document.getElementById('salidaMonitorSerial');
const formEnviarSerie = document.getElementById('formEnviarSerie');
const entradaMonitorSerial = document.getElementById('entradaMonitorSerial');
const comboFinLinea = document.getElementById('comboFinLinea');
const btnEnviarSerie = document.getElementById('btnEnviarSerie');
const btnElegirUsb = document.getElementById('btnElegirUsb');
const btnAyudaPuertos = document.getElementById('btnAyudaPuertos');
const btnTraducir = document.getElementById('btnTraducir');
const btnCargarPlaca = document.getElementById('btnCargarPlaca');
const btnActualizarPuertos = document.getElementById('btnActualizarPuertos');
const btnCopiarCpp = document.getElementById('btnCopiarCpp');
const btnDescargarIno = document.getElementById('btnDescargarIno');
const btnGuardarProyecto = document.getElementById('btnGuardarProyecto');
const btnAbrirProyecto = document.getElementById('btnAbrirProyecto');
const archivoProyecto = document.getElementById('archivoProyecto');
const btnBiblioteca = document.getElementById('btnBiblioteca');
const btnExpandirBiblioteca = document.getElementById('btnExpandirBiblioteca');
const modalBiblioteca = document.getElementById('modalBiblioteca');
const btnCerrarModal = document.getElementById('btnCerrarModal');
const listaComandos = document.getElementById('listaComandos');
const detalleComando = document.getElementById('detalleComando');
const buscCmd = document.getElementById('buscCmd');
const lblEstado = document.getElementById('lblEstado');
const badgeEstado = document.getElementById('badgeEstado');
const progresoCarga = document.getElementById('progresoCarga');
const estadoCarga = document.getElementById('estadoCarga');
const porcentajeCarga = document.getElementById('porcentajeCarga');
const barraProgresoCarga = document.getElementById('barraProgresoCarga');
const salidaCarga = document.getElementById('salidaCarga');
const detalleSalidaCarga = document.querySelector('.detalle-salida-carga');
const modalPuertos = document.getElementById('modalPuertos');
const btnCerrarPuertos = document.getElementById('btnCerrarPuertos');
const textoDiagnosticoPuertos = document.getElementById('textoDiagnosticoPuertos');
const listaAutocompletado = document.getElementById('listaAutocompletado');
const avisoArchivoLocal = document.getElementById('avisoArchivoLocal');
const btnAbrirLocalhost = document.getElementById('btnAbrirLocalhost');
let controladorMonitorSerial = null;
const nombresHostLocal = ['127.0.0.1', 'localhost'];
const origenIniciador = nombresHostLocal.includes(location.hostname)
  ? location.origin
  : 'http://127.0.0.1:8765';
const urlApiLocal = ruta => `${origenIniciador}/api/${ruta}`;
btnIniciadorSegundoPlano.hidden = !nombresHostLocal.includes(location.hostname);

function cambiarEstadoMonitorSerial(conectado, mensaje, conectando = false) {
  estadoMonitorSerial.textContent = mensaje;
  btnConectarMonitor.disabled = conectado || conectando;
  btnEnviarSerie.disabled = !conectado;
  comboPuerto.disabled = conectado || conectando;
  comboVelocidadSerie.disabled = conectado || conectando;
  comboPlacas.disabled = conectado || conectando;
}

function agregarSalidaMonitor(texto) {
  salidaMonitorSerial.textContent += texto;
  if (salidaMonitorSerial.textContent.length > 50000) {
    salidaMonitorSerial.textContent = salidaMonitorSerial.textContent.slice(-40000);
  }
  salidaMonitorSerial.scrollTop = salidaMonitorSerial.scrollHeight;
}

async function conectarMonitorSerial() {
  if (location.protocol === 'file:') {
    cambiarEstadoMonitorSerial(false, "Abre Integrated desde el iniciador local.");
    return;
  }
  const puerto = comboPuerto.value;
  if (!puerto) {
    cambiarEstadoMonitorSerial(false, "Selecciona primero un puerto.");
    return;
  }
  if (controladorMonitorSerial) return;

  const controlador = new AbortController();
  controladorMonitorSerial = controlador;
  const query = new URLSearchParams({
    puerto,
    baud: comboVelocidadSerie.value
  });
  cambiarEstadoMonitorSerial(false, `Conectando a ${puerto}…`, true);
  try {
    const respuesta = await fetch(`${urlApiLocal('serial/read')}?${query}`, {
      cache: 'no-store',
      signal: controlador.signal
    });
    if (!respuesta.ok) {
      const datos = await respuesta.json();
      throw new Error(datos.error || `HTTP ${respuesta.status}`);
    }
    if (!respuesta.body) throw new Error("El navegador no permite leer el monitor serial.");

    cambiarEstadoMonitorSerial(true, `Conectado a ${puerto} · ${comboVelocidadSerie.value} baudios`);
    const lector = respuesta.body.getReader();
    const decodificador = new TextDecoder();
    let buffer = '';
    const procesarEvento = linea => {
      if (!linea.trim()) return;
      const evento = JSON.parse(linea);
      if (evento.tipo === 'datos') {
        agregarSalidaMonitor(evento.texto);
      } else if (evento.tipo === 'estado') {
        cambiarEstadoMonitorSerial(true, evento.mensaje);
      } else if (evento.tipo === 'error') {
        cambiarEstadoMonitorSerial(false, evento.mensaje);
        agregarSalidaMonitor(`\n[${evento.mensaje}]\n`);
      }
    };
    while (true) {
      const { value, done } = await lector.read();
      buffer += decodificador.decode(value || new Uint8Array(), { stream: !done });
      const lineas = buffer.split('\n');
      buffer = lineas.pop();
      lineas.forEach(procesarEvento);
      if (done) break;
    }
    if (buffer.trim()) procesarEvento(buffer);
    if (controladorMonitorSerial === controlador) {
      cambiarEstadoMonitorSerial(false, "Conexión serial cerrada.");
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      cambiarEstadoMonitorSerial(false, `No se pudo abrir el monitor: ${error.message}`);
      agregarSalidaMonitor(`\n[${error.message}]\n`);
    } else {
      cambiarEstadoMonitorSerial(false, "Desconectado");
    }
  } finally {
    if (controladorMonitorSerial === controlador) controladorMonitorSerial = null;
  }
}

function desconectarMonitorSerial() {
  if (controladorMonitorSerial) controladorMonitorSerial.abort();
  controladorMonitorSerial = null;
  cambiarEstadoMonitorSerial(false, "Desconectado");
}

// Catálogo de Ejemplos
const EJEMPLOS_WEB = {
  hola: `// Primer programa: abre el Monitor Serie para ver el mensaje.
velocidad serie 115200

al iniciar
escribe Hola, Integrated esta funcionando

repetir siempre
escribe El programa sigue activo
esperar 2000`,

  semaforo: `// Conecta LED verde al pin 10, amarillo al 11 y rojo al 12.
// Usa una resistencia en serie con cada LED.
velocidad serie 115200

al iniciar
configurar pin 10, salida
configurar pin 11, salida
configurar pin 12, salida

repetir siempre
hacer que pin 10, encendido
hacer que pin 11, apagado
hacer que pin 12, apagado
esperar 3000
hacer que pin 10, apagado
hacer que pin 11, encendido
esperar 1000
hacer que pin 11, apagado
hacer que pin 12, encendido
esperar 3000`,

  sensorLuz: `// Conecta un LDR con una resistencia como divisor de voltaje a A0.
// Si el nivel baja del umbral, enciende un LED conectado al pin 13.
variable entero nivel
velocidad serie 115200

al iniciar
configurar pin 13, salida

repetir siempre
leer pin analógico A0 en nivel
escribe Nivel de luz , nivel
si nivel es menor a 500
  hacer que pin 13, encendido
si no
  hacer que pin 13, apagado
fin si
esperar 500`,

  hotspot: `// ESP32 S2 Mini: Genera su propia red WiFi (Hotspot) y crea una
// página web que puedes personalizar editando el HTML y CSS de abajo.
// Conecta el celular a ESP32_Panel (clave: 12345678) y abre 192.168.4.1.
velocidad serie 115200

al iniciar
configurar pin 15, salida
hacer que pin 15, apagado
wifi crear punto de acceso "ESP32_Panel" "12345678"
servidor iniciar 80
servidor al recibir "/encender" encender pin 15 y redirigir "/"
servidor al recibir "/apagar" apagar pin 15 y redirigir "/"
servidor al recibir "/alternar" alternar pin 15 y redirigir "/"

// Personaliza el título, los colores y el texto de los botones en este HTML.
contenido html "/":
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mi casa inteligente</title>
  <style>
    body { background: #eef2ff; color: #172554; font-family: Arial, sans-serif; text-align: center; padding: 24px; }
    main { background: white; border-radius: 18px; padding: 24px; max-width: 380px; margin: auto; box-shadow: 0 8px 24px #17255422; }
    h1 { color: #4338ca; }
    a { display: block; padding: 14px; margin: 12px 0; border-radius: 10px; color: white; text-decoration: none; font-weight: bold; }
    .on { background: #16a34a; }
    .off { background: #dc2626; }
    .toggle { background: #4f46e5; }
  </style>
</head>
<body>
  <main>
    <h1>Mi casa inteligente</h1>
    <p>Controla la luz conectada al GPIO 15.</p>
    <a class="on" href="/encender">Encender luz</a>
    <a class="off" href="/apagar">Apagar luz</a>
    <a class="toggle" href="/alternar">Cambiar estado</a>
  </main>
</body>
</html>
fin contenido html

repetir siempre
servidor atender`,

  riego: `// Riego sencillo: sensor de humedad en A0 y modulo de rele en pin 8.
// Usa un modulo de rele; no conectes una bomba directamente al GPIO.
// Ajusta 2500 despues de revisar lecturas de tierra seca y humeda por Monitor Serie.
variable entero humedad
velocidad serie 9600

al iniciar
configurar pin 8, salida
hacer que pin 8, apagado
escribe Riego automatico listo

repetir siempre
leer pin analógico A0 en humedad
escribe Lectura del sensor , humedad
si humedad es mayor a 2500
  hacer que pin 8, encendido
  escribe Suelo seco: bomba encendida
si no
  hacer que pin 8, apagado
  escribe Suelo humedo: bomba apagada
fin si
esperar 1000`,

  funciones: `// Define una accion una vez y reutilizala con "llamar".
// Boton en pin 2 entre GPIO y GND; LED/relay en pin 13.
velocidad serie 9600

funcion encenderLuz
  hacer que pin 13, encendido
fin funcion

funcion apagarLuz
  hacer que pin 13, apagado
fin funcion

al iniciar
configurar pin 2, entrada con resistencia
configurar pin 13, salida
llamar apagarLuz

repetir siempre
si pin 2 esta en bajo
  llamar encenderLuz
  esperar 250
  llamar apagarLuz
  esperar 250
fin si`,

  toggle: `// Control de luz o relé con un pulsador (Toggle)
// Botón en pin 2 (con resistencia interna), Relé o LED en pin 13
velocidad serie 115200

al iniciar
configurar pin 2, entrada con resistencia
configurar pin 13, salida
hacer que pin 13, apagado
escribe Sistema de control con pulsador listo

repetir siempre
si pin 2 esta en bajo
  alternar pin 13
  escribe Estado de relé cambiado
  esperar 250
fin si
esperar 50`,

dimmer: `// Controla el brillo con un potenciometro en A0 y un LED en pin 9.
// En Arduino Uno cambia 4095 por 1023. Usa una resistencia con el LED.
variable entero lectura
variable entero brillo
velocidad serie 115200

al iniciar
configurar pin 9, salida
escribe Regulador PWM listo

repetir siempre
leer pin analógico A0 en lectura
mapear lectura de 0 a 4095 hacia 0 a 255 en brillo
limitar brillo entre 0 y 255
escribir pwm pin 9 con brillo
esperar 30`,

  blink: `// Parpadeo de LED básico
velocidad serie 115200

al iniciar
configurar pin 13, salida

repetir siempre
hacer que pin 13, encendido
esperar 500
hacer que pin 13, apagado
esperar 500`
};

// Comandos para la biblioteca modal
const COMANDOS_MODAL = [
  { nombre: "al iniciar", cat: "Estructura", sin: "al iniciar", desc: "Se ejecuta una sola vez al encender o reiniciar la placa.", ej: "al iniciar\nconfigurar pin 13, salida" },
  { nombre: "repetir siempre", cat: "Estructura", sin: "repetir siempre", desc: "Bucle principal que se ejecuta continuamente.", ej: "repetir siempre\nhacer que pin 13, encendido\nesperar 500" },
  { nombre: "funcion", cat: "Funciones", sin: "funcion miAccion\n  ...\nfin funcion\n\nllamar miAccion", desc: "Agrupa instrucciones con un nombre para reutilizarlas desde al iniciar o repetir siempre.", ej: "funcion encenderLuz\n  hacer que pin 13, encendido\nfin funcion\n\nal iniciar\nllamar encenderLuz" },
  { nombre: "llamar", cat: "Funciones", sin: "llamar nombreDeFuncion", desc: "Ejecuta una función definida en el mismo programa.", ej: "llamar encenderLuz" },
  { nombre: "configurar pin", cat: "Pines digitales", sin: "configurar pin N, salida", desc: "Define si un pin es salida o entrada.", ej: "configurar pin 15, salida" },
  { nombre: "hacer que pin", cat: "Pines digitales", sin: "hacer que pin N, encendido", desc: "Enciende (3.3V/5V) o apaga (0V) un pin.", ej: "hacer que pin 15, encendido\nesperar 500\nhacer que pin 15, apagado" },
  { nombre: "alternar pin", cat: "Pines digitales", sin: "alternar pin N", desc: "Invierte el estado del pin (de on a off, o de off a on).", ej: "si pin 2 esta en bajo\n  alternar pin 13\nfin si" },
  { nombre: "leer pin analógico", cat: "Pines analógicos", sin: "leer pin analógico A0 en variable", desc: "Lee el voltaje analógico del pin (0 a 1023 o 4095).", ej: "leer pin analógico A0 en valor" },
  { nombre: "escribir pwm", cat: "Pines analógicos", sin: "escribir pwm pin N con valor", desc: "Modula la salida en un pin PWM (0-255).", ej: "escribir pwm pin 9 con 128" },
  { nombre: "esperar", cat: "Temporización", sin: "esperar N", desc: "Pausa el programa durante N milisegundos o segundos.", ej: "esperar 500\nesperar 2 segundos" },
  { nombre: "si / si no", cat: "Condicionales", sin: "si condicion\n  ...\nsi no\n  ...\nfin si", desc: "Ejecuta bloques de código según una condición.", ej: "si sensor es mayor a 100\n  hacer que pin 13, encendido\nfin si" },
  { nombre: "sumar / restar", cat: "Matemáticas", sin: "sumar cantidad a variable\nrestar cantidad a variable", desc: "Actualiza contadores y valores durante el programa.", ej: "sumar 1 a contador\nrestar 2 a contador" },
  { nombre: "incrementar / decrementar", cat: "Matemáticas", sin: "incrementar variable\ndecrementar variable", desc: "Aumenta o reduce una variable en una unidad.", ej: "incrementar contador" },
  { nombre: "limitar", cat: "Matemáticas", sin: "limitar variable entre minimo y maximo", desc: "Mantiene una lectura o salida dentro de un rango.", ej: "limitar brillo entre 0 y 255" },
  { nombre: "aleatorio", cat: "Matemáticas", sin: "aleatorio entre minimo y maximo en variable", desc: "Genera un número entero en el rango indicado, incluyendo ambos extremos.", ej: "aleatorio entre 1 y 6 en dado" },
  { nombre: "wifi crear punto de acceso", cat: "WiFi / ESP32", sin: 'wifi crear punto de acceso "Nombre" "Clave"', desc: "Crea una red WiFi propia generada por el ESP32 (Hotspot).", ej: 'wifi crear punto de acceso "MiRed" "12345678"' },
  { nombre: "servidor iniciar", cat: "Servidor Web", sin: "servidor iniciar 80", desc: "Inicia el servidor HTTP en el puerto indicado.", ej: "servidor iniciar 80" },
  { nombre: "servidor al recibir", cat: "Servidor Web", sin: 'servidor al recibir "/ruta" encender pin N y redirigir "/"', desc: "Ejecuta acciones de hardware desde enlaces o botones web.", ej: 'servidor al recibir "/encender" encender pin 15 y redirigir "/"' },
  { nombre: "servidor html", cat: "Servidor Web", sin: 'servidor html "/":\n...HTML...\nfin html', desc: "Define una página web HTML completa y estilizada.", ej: 'servidor html "/":\n<h1>Hola mundo</h1>\nfin html' },
  { nombre: "contenido html", cat: "Servidor Web", sin: 'contenido html "/":\n<!doctype html>\n<html>...</html>\nfin contenido html', desc: "Abre un bloque para pegar HTML, CSS y JavaScript como contenido de una ruta web del ESP32. El HTML dentro del bloque se copia literalmente.", ej: 'contenido html "/":\n<!doctype html>\n<html lang="es"><body><h1>Hola desde el ESP32</h1></body></html>\nfin contenido html' },
  { nombre: "servidor atender", cat: "Servidor Web", sin: "servidor atender", desc: "Procesa las peticiones web en repetir siempre.", ej: "repetir siempre\nservidor atender" }
];

const SUGERENCIAS_CODIGO = [
  "al iniciar", "repetir siempre", "fin si", "si ", "si no", "fin mientras",
  "funcion ", "fin funcion", "llamar ", "repetir 10 veces", "romper", "continuar",
  "variable entero ", "variable decimal ", "variable texto ", "variable verdadero o falso ",
  "asignar ", "sumar ", "restar ", "incrementar ", "decrementar ",
  "configurar pin ", "configurar pin 13, salida", "configurar pin 2, entrada con resistencia",
  "hacer que pin ", "hacer que pin 13, encendido", "hacer que pin 13, apagado",
  "alternar pin ", "leer pin digital ", "leer pin analógico ", "escribir pwm pin ",
  "esperar ", "esperar 1000", "mapear ", "limitar ", "aleatorio ",
  "escribe ", "escribir sin salto ", "velocidad serie 115200",
  'wifi crear punto de acceso "MiRed" "12345678"', 'wifi conectar "MiRed" "clave"',
  "wifi mostrar ip", "servidor iniciar 80", 'servidor html "/":', 'contenido html "/":', "fin html", "fin contenido html", "servidor atender",
  "configurar ultrasonido trig 12 echo 13", "medir distancia en distancia",
  "configurar servo pin 9", "girar servo a 90",
  "leer humedad suelo A0 en humedad", "leer temperatura lm35 A0 en temperatura",
  "tono pin 8 frecuencia 1000 duracion 200", "silencio pin 8"
];

let indiceSugerenciaActiva = -1;
let consultandoPuertos = false;
let actualizacionPuertosPendiente = null;

function ocultarAutocompletado() {
  listaAutocompletado.hidden = true;
  listaAutocompletado.replaceChildren();
  indiceSugerenciaActiva = -1;
}

function actualizarAutocompletado() {
  const cursor = editorEspanol.selectionStart;
  if (cursor !== editorEspanol.selectionEnd) {
    ocultarAutocompletado();
    return;
  }
  const inicioLinea = editorEspanol.value.lastIndexOf('\n', Math.max(0, cursor - 1)) + 1;
  const prefijoLinea = editorEspanol.value.slice(inicioLinea, cursor);
  const prefijo = prefijoLinea.trimStart();
  if (!prefijo || prefijo.startsWith('//')) {
    ocultarAutocompletado();
    return;
  }
  const htmlInicio = editorEspanol.value.toLowerCase().lastIndexOf('servidor html', cursor);
  const htmlFin = editorEspanol.value.toLowerCase().lastIndexOf('fin html', cursor);
  if (htmlInicio > htmlFin) {
    ocultarAutocompletado();
    return;
  }
  const clave = prefijo.toLocaleLowerCase('es');
  const coincidencias = SUGERENCIAS_CODIGO
    .filter(comando => comando.toLocaleLowerCase('es').startsWith(clave) && comando !== prefijo)
    .slice(0, 8);
  if (coincidencias.length === 0) {
    ocultarAutocompletado();
    return;
  }
  listaAutocompletado.replaceChildren();
  coincidencias.forEach((comando, indice) => {
    const opcion = document.createElement('button');
    opcion.type = 'button';
    opcion.className = 'opcion-autocompletado';
    opcion.setAttribute('role', 'option');
    opcion.setAttribute('aria-selected', indice === 0 ? 'true' : 'false');
    opcion.textContent = comando;
    opcion.addEventListener('mousedown', evento => evento.preventDefault());
    opcion.addEventListener('click', () => aceptarSugerencia(comando, inicioLinea, cursor));
    listaAutocompletado.appendChild(opcion);
  });
  listaAutocompletado.hidden = false;
  indiceSugerenciaActiva = 0;
}

function aceptarSugerencia(comando, inicioLinea, cursor = editorEspanol.selectionStart) {
  const linea = editorEspanol.value.slice(inicioLinea, cursor);
  const indentacion = linea.match(/^\s*/)?.[0] || '';
  editorEspanol.setRangeText(
    indentacion + comando,
    inicioLinea,
    cursor,
    'end'
  );
  guardarEnEsteDispositivo();
  actualizarTraduccion();
  ocultarAutocompletado();
  editorEspanol.focus();
}

editorEspanol.addEventListener('input', actualizarAutocompletado);
editorEspanol.addEventListener('click', actualizarAutocompletado);
editorEspanol.addEventListener('keyup', evento => {
  if (!['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(evento.key)) {
    actualizarAutocompletado();
  }
});
editorEspanol.addEventListener('keydown', evento => {
  if (listaAutocompletado.hidden) return;
  const opciones = [...listaAutocompletado.querySelectorAll('.opcion-autocompletado')];
  if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
    evento.preventDefault();
    const direccion = evento.key === 'ArrowDown' ? 1 : -1;
    indiceSugerenciaActiva = (indiceSugerenciaActiva + direccion + opciones.length) % opciones.length;
    opciones.forEach((opcion, indice) => opcion.setAttribute('aria-selected', indice === indiceSugerenciaActiva ? 'true' : 'false'));
  } else if (evento.key === 'Enter' || evento.key === 'Tab') {
    evento.preventDefault();
    if (opciones[indiceSugerenciaActiva]) opciones[indiceSugerenciaActiva].click();
  } else if (evento.key === 'Escape') {
    ocultarAutocompletado();
  }
});

// Función de traducción
function actualizarTraduccion() {
  const codigo = editorEspanol.value;
  const placa = comboPlacas.value;
  const baud = placa.includes("ESP") ? 115200 : 9600;
  
  const cpp = traducirCodigoWeb(codigo, placa, baud);
  cppSalida.value = cpp;
  badgeEstado.textContent = "Sincronizado (" + new Date().toLocaleTimeString() + ")";
  lblEstado.textContent = "Traducción completada para " + placa;
}

const CLAVE_PROYECTO_LOCAL = 'integrated-proyecto-actual';

function guardarEnEsteDispositivo() {
  try {
    localStorage.setItem(CLAVE_PROYECTO_LOCAL, editorEspanol.value);
  } catch (error) {
    lblEstado.textContent = "No se pudo guardar automáticamente: " + error.message;
  }
}

function descargarArchivo(nombre, contenido, tipo) {
  const enlace = document.createElement('a');
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Eventos
editorEspanol.addEventListener('input', () => {
  guardarEnEsteDispositivo();
  actualizarTraduccion();
});

btnTraducir.addEventListener('click', actualizarTraduccion);
comboPlacas.addEventListener('change', actualizarTraduccion);
btnActualizarPuertos.addEventListener('click', actualizarPuertos);

function actualizarSelectorPuertos(puertos, puertoAnterior) {
  const firmaActual = [...comboPuerto.options]
    .map(opcion => `${opcion.value}\0${opcion.textContent}\0${opcion.dataset.vid || ''}\0${opcion.dataset.pid || ''}`)
    .join('\n');
  const firmaNueva = puertos
    .map(puerto => `${puerto.device}\0${puerto.label}\0${puerto.vid}\0${puerto.pid}`)
    .join('\n');
  if (firmaActual === firmaNueva) return;

  const fragmento = document.createDocumentFragment();
  if (puertos.length === 0) {
    fragmento.appendChild(new Option('No se detectaron placas', ''));
  } else {
    puertos.forEach(puerto => {
      const opcion = new Option(puerto.label, puerto.device);
      opcion.dataset.vid = puerto.vid;
      opcion.dataset.pid = puerto.pid;
      fragmento.appendChild(opcion);
    });
  }
  comboPuerto.replaceChildren(fragmento);
  if (puertos.some(puerto => puerto.device === puertoAnterior)) {
    comboPuerto.value = puertoAnterior;
  }
}

comboPuerto.addEventListener('blur', () => {
  if (!actualizacionPuertosPendiente) return;
  const { puertos, puertoAnterior } = actualizacionPuertosPendiente;
  actualizacionPuertosPendiente = null;
  actualizarSelectorPuertos(puertos, puertoAnterior);
});

async function actualizarPuertos(silencioso = false) {
  if (location.protocol === 'file:') {
    if (comboPuerto.options.length !== 1 || comboPuerto.options[0].textContent !== 'Iniciador local requerido') {
      comboPuerto.replaceChildren(new Option('Iniciador local requerido', ''));
    }
    textoDiagnosticoPuertos.textContent = "Estás usando file://. Cierra esta página y abre «Iniciar Integrated Web.bat»; la detección USB necesita que la web se sirva desde localhost.";
    if (!silencioso) lblEstado.textContent = "Abre «Iniciar Integrated Web.bat» para detectar puertos COM y cargar programas.";
    return;
  }
  if (!nombresHostLocal.includes(location.hostname)) {
    if (comboPuerto.options[0]?.textContent !== 'Disponible en Integrated para Windows') {
      comboPuerto.replaceChildren(new Option('Disponible en Integrated para Windows', ''));
    }
    if (!silencioso) {
      lblEstado.textContent = "La versión Simulador no se conecta a placas. Descarga Integrated para Windows para cargar programas.";
    }
    return;
  }
  if (consultandoPuertos) return;
  consultandoPuertos = true;
  const puertoAnterior = comboPuerto.value;
  if (!silencioso) btnActualizarPuertos.disabled = true;
  try {
    const respuesta = await fetch(urlApiLocal('ports'), { cache: 'no-store' });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.ayuda ? `${datos.error} ${datos.ayuda}` : (datos.error || `HTTP ${respuesta.status}`));
    const nuevosPuertos = datos.puertos.map(puerto => {
      const descripcion = [puerto.description, puerto.manufacturer, puerto.vid && puerto.pid
        ? `USB ${puerto.vid.toString(16).toUpperCase()}:${puerto.pid.toString(16).toUpperCase()}`
        : ''].filter(Boolean).join(' · ');
      return {
        device: puerto.device,
        label: `${puerto.device} — ${descripcion}`,
        vid: puerto.vid == null ? '' : String(puerto.vid),
        pid: puerto.pid == null ? '' : String(puerto.pid)
      };
    });
    if (document.activeElement === comboPuerto) {
      actualizacionPuertosPendiente = { puertos: nuevosPuertos, puertoAnterior };
    } else {
      actualizarSelectorPuertos(nuevosPuertos, puertoAnterior);
    }

    if (datos.puertos.length === 0) {
      textoDiagnosticoPuertos.textContent = datos.diagnostico || "Windows no reportó puertos COM. Revisa el cable USB, los controladores y el Administrador de dispositivos.";
      if (!silencioso) lblEstado.textContent = "No se detectaron puertos COM. Pulsa «¿No aparece?» para revisar causas habituales.";
    } else {
      textoDiagnosticoPuertos.textContent = "Puertos encontrados. Selecciona el puerto que corresponda a tu placa y revisa que coincidan la placa y el cable.";
      if (!silencioso) lblEstado.textContent = `${datos.puertos.length} puerto(s) COM detectado(s).`;
    }
    if (!datos.compilador && datos.puertos.length > 0) {
      if (!silencioso) lblEstado.textContent = "Se detectaron puertos, pero falta Arduino CLI o PlatformIO para compilar.";
    }
  } catch (error) {
    if (!comboPuerto.value && document.activeElement !== comboPuerto &&
        comboPuerto.options[0]?.textContent !== 'Iniciador local no disponible') {
      comboPuerto.replaceChildren(new Option('Iniciador local no disponible', ''));
    }
    textoDiagnosticoPuertos.textContent = location.protocol === 'file:'
      ? "Estás usando file://. Cierra esta página y abre «Iniciar Integrated Web.bat»; la detección USB necesita que la web se sirva desde localhost."
      : `No se pudo contactar el iniciador local en ${origenIniciador}. Inicia «Iniciar Integrated Web.bat» en la computadora conectada a la placa y vuelve a pulsar «Puertos». Si el navegador pregunta, permite el acceso a la red local. Detalle: ${error.message}`;
    if (!silencioso) {
      lblEstado.textContent = location.protocol === 'file:'
        ? "Abre «Iniciar Integrated Web.bat»; una página file:// no puede detectar puertos COM."
        : `Inicia el iniciador local en esta computadora y permite el acceso a la red local del navegador.`;
    }
  } finally {
    consultandoPuertos = false;
    if (!silencioso) btnActualizarPuertos.disabled = false;
  }
}

btnCargarPlaca.addEventListener('click', async () => {
  const puerto = comboPuerto.value;
  if (controladorMonitorSerial) {
    lblEstado.textContent = "Cierra el monitor serial antes de cargar código a la placa.";
    return;
  }
  if (!puerto) {
    lblEstado.textContent = "Conecta la placa y pulsa «Puertos» antes de cargar.";
    return;
  }
  btnCargarPlaca.disabled = true;
  progresoCarga.hidden = false;
  estadoCarga.textContent = "Conectando con el iniciador local…";
  porcentajeCarga.textContent = "En espera";
  barraProgresoCarga.removeAttribute('value');
  salidaCarga.textContent = '';
  detalleSalidaCarga.open = false;
  lblEstado.textContent = `Compilando para ${comboPlacas.value} en ${puerto}...`;
  try {
    const respuesta = await fetch(urlApiLocal('upload'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        codigo: cppSalida.value,
        placa: comboPlacas.value,
        puerto
      })
    });
    if (!respuesta.ok) {
      const datos = await respuesta.json();
      throw new Error(datos.error || `HTTP ${respuesta.status}`);
    }
    if (!respuesta.body) throw new Error("El navegador no permite leer el progreso de carga.");

    const lector = respuesta.body.getReader();
    const decodificador = new TextDecoder();
    let buffer = '';
    let resultado = null;
    const procesarEvento = linea => {
      if (!linea.trim()) return;
      const evento = JSON.parse(linea);
      if (evento.tipo === 'fase') {
        estadoCarga.textContent = evento.mensaje;
        barraProgresoCarga.removeAttribute('value');
        porcentajeCarga.textContent = "En curso";
      } else if (evento.tipo === 'progreso') {
        const porcentaje = Math.max(0, Math.min(100, Math.round(evento.porcentaje)));
        barraProgresoCarga.value = porcentaje;
        porcentajeCarga.textContent = `${porcentaje}%`;
      } else if (evento.tipo === 'salida') {
        salidaCarga.textContent = (salidaCarga.textContent + evento.texto).slice(-20000);
        salidaCarga.scrollTop = salidaCarga.scrollHeight;
      } else if (evento.tipo === 'resultado') {
        resultado = evento;
      }
    };

    while (true) {
      const { value, done } = await lector.read();
      buffer += decodificador.decode(value || new Uint8Array(), { stream: !done });
      const lineas = buffer.split('\n');
      buffer = lineas.pop();
      lineas.forEach(procesarEvento);
      if (done) break;
    }
    if (buffer.trim()) procesarEvento(buffer);
    if (!resultado) throw new Error("El iniciador local cerró la conexión sin informar el resultado.");
    if (!resultado.ok) throw new Error(resultado.error || "Falló la compilación o la carga.");

    barraProgresoCarga.value = 100;
    porcentajeCarga.textContent = "100%";
    estadoCarga.textContent = resultado.mensaje;
    lblEstado.textContent = resultado.mensaje;
  } catch (error) {
    const mensajeError = `No se pudo cargar: ${error.message}`;
    estadoCarga.textContent = mensajeError;
    lblEstado.textContent = mensajeError;
    salidaCarga.textContent = `${salidaCarga.textContent}\n${mensajeError}`.trim();
    detalleSalidaCarga.open = true;
  } finally {
    btnCargarPlaca.disabled = false;
  }
});

btnMonitorSerial.addEventListener('click', () => {
  panelMonitorSerial.hidden = !panelMonitorSerial.hidden;
  if (!panelMonitorSerial.hidden) {
    estadoMonitorSerial.textContent = location.protocol === 'file:'
      ? "El monitor requiere abrir Integrated desde el iniciador local."
      : "Selecciona un puerto y pulsa Conectar.";
    entradaMonitorSerial.focus();
  } else {
    desconectarMonitorSerial();
  }
});

btnIniciadorSegundoPlano.addEventListener('click', async () => {
  btnIniciadorSegundoPlano.disabled = true;
  lblEstado.textContent = "Enviando el iniciador local al segundo plano…";
  try {
    const respuesta = await fetch(urlApiLocal('launcher/background'), { method: 'POST' });
    const datos = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) throw new Error(datos.error || `HTTP ${respuesta.status}`);
    lblEstado.textContent = datos.mensaje;
  } catch (error) {
    lblEstado.textContent = "El iniciador local no está disponible. Ejecuta «Iniciar Integrated Web.bat» y vuelve a intentarlo.";
    console.warn("No se pudo contactar el iniciador local:", error);
  } finally {
    btnIniciadorSegundoPlano.disabled = false;
  }
});

btnConectarMonitor.addEventListener('click', conectarMonitorSerial);
btnLimpiarMonitor.addEventListener('click', () => {
  salidaMonitorSerial.textContent = '';
});
btnCerrarMonitor.addEventListener('click', () => {
  desconectarMonitorSerial();
  panelMonitorSerial.hidden = true;
});

formEnviarSerie.addEventListener('submit', async evento => {
  evento.preventDefault();
  if (!controladorMonitorSerial) return;
  const texto = entradaMonitorSerial.value;
  if (!texto) return;
  const finalLinea = comboFinLinea.value === 'newline'
    ? '\n'
    : comboFinLinea.value === 'both'
      ? '\r\n'
      : '';
  btnEnviarSerie.disabled = true;
  try {
    const respuesta = await fetch(urlApiLocal('serial/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: texto + finalLinea })
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error || `HTTP ${respuesta.status}`);
    agregarSalidaMonitor(`> ${texto}\n`);
    entradaMonitorSerial.value = '';
  } catch (error) {
    estadoMonitorSerial.textContent = `No se pudo enviar: ${error.message}`;
  } finally {
    btnEnviarSerie.disabled = !controladorMonitorSerial;
  }
});

btnElegirUsb.hidden = !nombresHostLocal.includes(location.hostname) || !('serial' in navigator) || location.protocol === 'file:';
btnElegirUsb.addEventListener('click', async () => {
  try {
    const dispositivo = await navigator.serial.requestPort();
    const info = dispositivo.getInfo();
    const coincidencia = [...comboPuerto.options].find(opcion =>
      opcion.dataset.vid === String(info.usbVendorId || '') &&
      opcion.dataset.pid === String(info.usbProductId || '')
    );
    if (coincidencia) {
      comboPuerto.value = coincidencia.value;
      lblEstado.textContent = `Placa identificada en ${coincidencia.value}.`;
    } else {
      textoDiagnosticoPuertos.textContent = info.usbVendorId
        ? `El navegador autorizó el dispositivo USB ${info.usbVendorId.toString(16).toUpperCase()}:${info.usbProductId.toString(16).toUpperCase()}, pero Windows no lo expone como puerto COM. Instala el controlador de la placa o revisa el Administrador de dispositivos.`
        : "El navegador autorizó el USB, pero el dispositivo no publicó identificadores. Revisa el cable, el controlador y el puerto COM en Windows.";
      modalPuertos.style.display = 'flex';
    }
    await actualizarPuertos(true);
  } catch (error) {
    if (error.name !== 'NotFoundError') {
      lblEstado.textContent = `No se pudo solicitar acceso USB: ${error.message}`;
    }
  }
});

btnAyudaPuertos.addEventListener('click', () => {
  modalPuertos.style.display = 'flex';
});

btnCerrarPuertos.addEventListener('click', () => {
  modalPuertos.style.display = 'none';
});

btnAbrirLocalhost.addEventListener('click', () => {
  window.location.assign('http://127.0.0.1:8765/');
});

actualizarPuertos();

window.addEventListener('keydown', (e) => {
  const tecla = e.key.toLowerCase();
  if ((e.ctrlKey || e.metaKey) && tecla === 's') {
    e.preventDefault();
    if (e.shiftKey) {
      btnDescargarIno.click();
    } else {
      btnGuardarProyecto.click();
    }
    return;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    actualizarTraduccion();
    return;
  }
  if (e.key === 'F5') {
    e.preventDefault();
    actualizarTraduccion();
  }
});

// Cargar ejemplos
comboEjemplos.addEventListener('change', () => {
  const sel = comboEjemplos.value;
  if (sel && EJEMPLOS_WEB[sel]) {
    editorEspanol.value = EJEMPLOS_WEB[sel];
    guardarEnEsteDispositivo();
    actualizarTraduccion();
    lblEstado.textContent = "Ejemplo cargado: " + comboEjemplos.options[comboEjemplos.selectedIndex].text;
  }
});

// Copiar C++
btnCopiarCpp.addEventListener('click', () => {
  navigator.clipboard.writeText(cppSalida.value).then(() => {
    lblEstado.textContent = "¡Código C++ copiado al portapapeles!";
    alert("¡Código C++ copiado al portapapeles!");
  });
});

// Descargar .ino
btnDescargarIno.addEventListener('click', () => {
  descargarArchivo("sketch_integrated.ino", cppSalida.value, "text/plain;charset=utf-8");
  lblEstado.textContent = "Descargando sketch_integrated.ino...";
});

btnGuardarProyecto.addEventListener('click', () => {
  descargarArchivo("mi_proyecto.int_esp", editorEspanol.value, "text/plain;charset=utf-8");
  lblEstado.textContent = "Proyecto .int_esp descargado.";
});

btnAbrirProyecto.addEventListener('click', () => archivoProyecto.click());

archivoProyecto.addEventListener('change', async () => {
  const archivo = archivoProyecto.files && archivoProyecto.files[0];
  if (!archivo) return;
  try {
    editorEspanol.value = await archivo.text();
    guardarEnEsteDispositivo();
    actualizarTraduccion();
    lblEstado.textContent = "Proyecto abierto: " + archivo.name;
  } catch (error) {
    lblEstado.textContent = "No se pudo abrir el proyecto: " + error.message;
  } finally {
    archivoProyecto.value = '';
  }
});

// Manejo de Modal de Biblioteca
btnBiblioteca.addEventListener('click', () => {
  modalBiblioteca.style.display = 'flex';
  renderizarListaComandos(COMANDOS_MODAL);
});

btnCerrarModal.addEventListener('click', () => {
  modalBiblioteca.style.display = 'none';
});

btnExpandirBiblioteca.addEventListener('click', () => {
  const ampliado = modalBiblioteca.querySelector('.modal-content').classList.toggle('ampliado');
  btnExpandirBiblioteca.setAttribute('aria-pressed', String(ampliado));
  btnExpandirBiblioteca.textContent = ampliado ? '⛶ Reducir' : '⛶ Agrandar';
});

function renderizarListaComandos(lista) {
  listaComandos.innerHTML = '';
  lista.forEach((cmd, idx) => {
    const item = document.createElement('div');
    item.className = 'cmd-item' + (idx === 0 ? ' activo' : '');
    item.textContent = cmd.nombre;
    item.addEventListener('click', () => {
      document.querySelectorAll('.cmd-item').forEach(el => el.classList.remove('activo'));
      item.classList.add('activo');
      mostrarDetalleComando(cmd);
    });
    listaComandos.appendChild(item);
  });
  if (lista.length > 0) mostrarDetalleComando(lista[0]);
}

function escaparHTML(texto) {
  return texto.replace(/[&<>"']/g, caracter => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[caracter]);
}

function mostrarDetalleComando(cmd) {
  detalleComando.innerHTML = `
    <h2 style="color:var(--acento-2); margin-bottom:8px;">${escaparHTML(cmd.nombre)}</h2>
    <div class="badge">${escaparHTML(cmd.cat)}</div>
    <div style="font-weight:700; margin-top:10px; color:var(--fg-muted);">SINTAXIS:</div>
    <div class="codigo-caja">${escaparHTML(cmd.sin)}</div>
    <div style="font-weight:700; margin-top:10px; color:var(--fg-muted);">DESCRIPCIÓN:</div>
    <p style="margin:8px 0 16px 0; line-height:1.5;">${escaparHTML(cmd.desc)}</p>
    <div style="font-weight:700; margin-top:10px; color:var(--fg-muted);">EJEMPLO:</div>
    <div class="codigo-caja" style="color:#00ff66;">${escaparHTML(cmd.ej)}</div>
    <button id="btnInsertarCmd" class="btn-accion" style="margin-top:10px;">➕ Insertar en el código</button>
  `;
  document.getElementById('btnInsertarCmd').addEventListener('click', () => {
    editorEspanol.value += "\n" + cmd.sin + "\n";
    guardarEnEsteDispositivo();
    modalBiblioteca.style.display = 'none';
    actualizarTraduccion();
  });
}

buscCmd.addEventListener('input', () => {
  const term = buscCmd.value.toLowerCase().trim();
  const filtrados = COMANDOS_MODAL.filter(c => c.nombre.toLowerCase().includes(term) || c.desc.toLowerCase().includes(term));
  renderizarListaComandos(filtrados);
});

// Recupera el último proyecto editado, incluso después de cerrar la app offline.
try {
  editorEspanol.value = localStorage.getItem(CLAVE_PROYECTO_LOCAL) || EJEMPLOS_WEB.funciones;
} catch (error) {
  editorEspanol.value = EJEMPLOS_WEB.funciones;
  lblEstado.textContent = "El almacenamiento local no está disponible: " + error.message;
}
actualizarTraduccion();
if (location.protocol === 'file:') {
  avisoArchivoLocal.hidden = false;
  lblEstado.textContent = "Para instalar, trabajar offline y usar los puertos, abre «Iniciar Integrated Web.bat» (http://127.0.0.1:8765).";
} else {
  avisoArchivoLocal.hidden = true;
}
