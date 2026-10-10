/**
 * Motor de traducción client-side (Español -> C++/Arduino) para Integrated Web / PWA.
 * Funciona 100% en local sin internet.
 */

function traducirCodigoWeb(codigoEspanol, placa = "ESP32 S2 Mini", baudDefault = 115200) {
  const lineas = codigoEspanol.split("\n");
  const esESP = placa.toLowerCase().includes("esp");
  const esAVR = !esESP;

  let baudPersonalizado = null;
  const variablesGlobales = [];
  const variablesTipos = {};
  const extrasGlobales = [];
  const includes = ["#include <Arduino.h>"];
  const cppSetup = [
    "void setup() {",
    `  Serial.begin(${baudDefault});`,
    "  delay(250);",
    esAVR ? '  Serial.println(F("Integrated iniciado"));' : '  Serial.println("Integrated iniciado");',
  ];
  const cppLoop = ["void loop() {"];
  const cppFunciones = [];
  const errores = [];

  let seccionActual = "global";
  let seccionAnteriorFuncion = "global";
  let funcionActual = null;
  const pilaBloques = [];
  let usaServo = false;
  let usaWifi = false;
  let usaServidor = false;
  let ultraTrig = null;
  let ultraEcho = null;
  const rutasServidor = [];

  function nivelActual() {
    return 1 + pilaBloques.length;
  }

  function indent(n) {
    return "  ".repeat(Math.max(n, 1));
  }

  function strLit(txt) {
    const esc = txt.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    return esAVR ? `F("${esc}")` : `"${esc}"`;
  }

  function textoCpp(txt) {
    return txt.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "").replace(/\n/g, "\\n");
  }

  function asegurarVariable(nombre, tipoCpp = "int", valIni = "0") {
    nombre = nombre.trim();
    if (!nombre || !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nombre)) return;
    const nLow = nombre.toLowerCase();
    if (["high", "low", "input", "output", "input_pullup", "true", "false", "led_builtin"].includes(nLow)) return;
    if (!variablesTipos[nombre] && !variablesTipos[nLow]) {
      variablesTipos[nombre] = tipoCpp;
      variablesTipos[nLow] = tipoCpp;
      variablesGlobales.push(`${tipoCpp} ${nombre} = ${valIni};`);
    }
  }

  function agregar(cod) {
    if (seccionActual === "funcion" && funcionActual) {
      funcionActual.push(`${indent(nivelActual())}${cod}`);
      if (cod.startsWith("delay(") && esESP) {
        funcionActual.push(`${indent(nivelActual())}yield();`);
      }
    } else if (seccionActual === "loop") {
      cppLoop.push(`${indent(nivelActual())}${cod}`);
      if (cod.startsWith("delay(") && esESP) {
        cppLoop.push(`${indent(nivelActual())}yield();`);
      }
    } else if (seccionActual === "setup") {
      cppSetup.push(`${indent(nivelActual())}${cod}`);
    } else {
      errores.push(`Comando fuera de sección: ${cod}`);
    }
  }

  function cerrarBloque() {
    if (pilaBloques.length > 0) {
      pilaBloques.pop();
      const ind = indent(nivelActual());
      const target = seccionActual === "funcion" && funcionActual
        ? funcionActual
        : seccionActual === "loop" ? cppLoop : cppSetup;
      target.push(`${ind}}`);
    }
  }

  function cerrarTodosLosBloques() {
    while (pilaBloques.length > 0) {
      cerrarBloque();
    }
  }

  function reemplazarOperadores(cond) {
    cond = cond.trim();
    if (cond.endsWith(":")) cond = cond.slice(0, -1).trim();

    const reglas = [
      [/\bes\s+mayor\s+o\s+igual\s+(?:a|que)\b/gi, " >= "],
      [/\bmayor\s+o\s+igual\s+(?:a|que)\b/gi, " >= "],
      [/\bes\s+menor\s+o\s+igual\s+(?:a|que)\b/gi, " <= "],
      [/\bmenor\s+o\s+igual\s+(?:a|que)\b/gi, " <= "],
      [/\bno\s+es\s+igual\s+(?:a|que)\b/gi, " != "],
      [/\bes\s+diferente\s+(?:a|de)\b/gi, " != "],
      [/\bes\s+distinto\s+(?:a|de)\b/gi, " != "],
      [/\bes\s+mayor\s+(?:a|que)\b/gi, " > "],
      [/\bmayor\s+(?:a|que)\b/gi, " > "],
      [/\bes\s+menor\s+(?:a|que)\b/gi, " < "],
      [/\bmenor\s+(?:a|que)\b/gi, " < "],
      [/\bes\s+igual\s+(?:a|que)\b/gi, " == "],
      [/\bigual\s+(?:a|que)\b/gi, " == "],
      [/\by\b/gi, " && "],
      [/\bo\b/gi, " || "],
      [/\bno\b/gi, " !"],
      [/\bpin\s+([a-zA-Z0-9_]+)\s+est[aá]\s+(?:en\s+alto|encendido|presionado|activo)\b/gi, "digitalRead($1) == HIGH"],
      [/\bpin\s+([a-zA-Z0-9_]+)\s+est[aá]\s+(?:en\s+bajo|apagado|desactivado)\b/gi, "digitalRead($1) == LOW"],
      [/\bencendido\b/gi, "HIGH"],
      [/\bapagado\b/gi, "LOW"],
      [/\balto\b/gi, "HIGH"],
      [/\bbajo\b/gi, "LOW"],
      [/\bverdadero\b/gi, "true"],
      [/\bfalso\b/gi, "false"]
    ];

    for (const [re, rep] of reglas) {
      cond = cond.replace(re, rep);
    }
    return cond.replace(/\s+/g, " ").trim();
  }

  let bloqueHtmlRuta = null;
  let bloqueHtmlLineas = [];

  for (let num = 1; num <= lineas.length; num++) {
    const linea = lineas[num - 1];
    const l = linea.trim();
    const lLow = l.toLowerCase();

    if (bloqueHtmlRuta !== null) {
      if (["fin html", "fin html:", "fin contenido html", "fin contenido html:"].includes(lLow)) {
        rutasServidor.push([bloqueHtmlRuta, textoCpp(bloqueHtmlLineas.join("\n"))]);
        bloqueHtmlRuta = null;
        bloqueHtmlLineas = [];
      } else {
        bloqueHtmlLineas.push(linea);
      }
      continue;
    }

    if (!l || lLow.startsWith("//") || lLow.startsWith("#")) continue;

    const lSinDosPuntos = (lLow.endsWith(":") && !lLow.startsWith("servidor html") &&
      !lLow.startsWith("contenido html")) ? l.slice(0, -1).trim() : l;
    const lLowSin = lSinDosPuntos.toLowerCase();

    const mFuncion = lSinDosPuntos.match(/^funcion\s+([a-zA-Z_][a-zA-Z0-9_]*)$/i);
    if (mFuncion) {
      cerrarTodosLosBloques();
      seccionAnteriorFuncion = seccionActual;
      funcionActual = [`void ${mFuncion[1]}() {`];
      cppFunciones.push(funcionActual);
      seccionActual = "funcion";
      continue;
    }

    if (["fin funcion", "terminar funcion"].includes(lLowSin)) {
      if (seccionActual === "funcion" && funcionActual) {
        cerrarTodosLosBloques();
        funcionActual.push("}");
        funcionActual = null;
        seccionActual = seccionAnteriorFuncion;
      } else {
        errores.push(`Línea ${num}: 'fin funcion' sin una función abierta`);
      }
      continue;
    }

    // Secciones
    if (["al iniciar", "iniciar", "configuracion", "setup"].includes(lLowSin)) {
      cerrarTodosLosBloques();
      seccionActual = "setup";
      continue;
    }

    if (["repetir siempre", "bucle principal", "bucle", "loop"].includes(lLowSin)) {
      cerrarTodosLosBloques();
      seccionActual = "loop";
      continue;
    }

    if (["fin si", "terminar si", "cerrar si", "fin de si"].includes(lLowSin)) {
      cerrarBloque();
      continue;
    }

    if (["fin mientras", "fin repetir", "fin bucle"].includes(lLowSin)) {
      cerrarBloque();
      continue;
    }

    const mLlamar = lSinDosPuntos.match(/^llamar\s+([a-zA-Z_][a-zA-Z0-9_]*)$/i);
    if (mLlamar) {
      agregar(`${mLlamar[1]}();`);
      continue;
    }

    // Velocidad serie
    const mVel = lLow.match(/velocidad\s+serie\s*(\d+)/);
    if (mVel) {
      baudPersonalizado = parseInt(mVel[1], 10);
      continue;
    }

    // WiFi y servidor web
    if (lLow.startsWith("wifi ") || lLow.startsWith("servidor ") || lLow.startsWith("contenido html ")) {
      usaWifi = true;
      if (esAVR) {
        errores.push(`Línea ${num}: WiFi y Servidor requieren placa ESP32 o ESP8266`);
        continue;
      }
      if (lLow.startsWith("wifi crear punto de acceso")) {
        const mAp = linea.match(/wifi\s+crear\s+punto\s+de\s+acceso\s+["“]([^"”]+)["”]\s+["“]([^"”]+)["”]/i);
        if (mAp) {
          if (!includes.includes("#include <WiFi.h>")) includes.push("#include <WiFi.h>");
          cppSetup.push("  delay(1000);");
          cppSetup.push("  WiFi.mode(WIFI_AP);");
          cppSetup.push(`  bool __apCreado = WiFi.softAP("${textoCpp(mAp[1])}", "${textoCpp(mAp[2])}");`);
          cppSetup.push(`  if (__apCreado) { Serial.print("Punto de acceso listo: http://"); Serial.println(WiFi.softAPIP()); }`);
          cppSetup.push(`  else { Serial.println("Error: no se pudo crear el punto de acceso WiFi"); }`);
        }
        continue;
      }

      if (lLow.startsWith("wifi conectar")) {
        const mCon = linea.match(/wifi\s+conectar\s+(\S+)\s+(\S+)/i);
        if (mCon) {
          if (!includes.includes("#include <WiFi.h>")) includes.push("#include <WiFi.h>");
          cppSetup.push("  WiFi.mode(WIFI_STA);");
          cppSetup.push(`  WiFi.begin("${textoCpp(mCon[1].replace(/"/g, ""))}", "${textoCpp(mCon[2].replace(/"/g, ""))}");`);
        }
        continue;
      }

      if (lLow.startsWith("servidor iniciar")) {
        usaServidor = true;
        if (!includes.includes("#include <WebServer.h>")) includes.push("#include <WebServer.h>");
        if (!extrasGlobales.includes("WebServer __servidorIntegrated(80);")) extrasGlobales.push("WebServer __servidorIntegrated(80);");
        continue;
      }

      if (lLow.startsWith("servidor al recibir")) {
        usaServidor = true;
        if (!includes.includes("#include <WebServer.h>")) includes.push("#include <WebServer.h>");
        if (!extrasGlobales.includes("WebServer __servidorIntegrated(80);")) extrasGlobales.push("WebServer __servidorIntegrated(80);");

        const mAcc = linea.match(/servidor\s+al\s+recibir\s+["“]([^"”]+)["”]\s+(encender|apagar|alternar)\s+pin\s+([a-zA-Z0-9_]+)(?:\s+y\s+(?:responder\s+["“]([^"”]+)["”]|redirigir\s+["“]([^"”]+)["”]))?/i);
        if (mAcc) {
          const ruta = mAcc[1];
          const act = mAcc[2].toLowerCase();
          const p = mAcc[3];
          let actCod = act === "encender" ? `digitalWrite(${p}, HIGH);` : act === "apagar" ? `digitalWrite(${p}, LOW);` : `digitalWrite(${p}, !digitalRead(${p}));`;
          let respCod = mAcc[5] ? `__servidorIntegrated.sendHeader("Location", "${mAcc[5]}"); __servidorIntegrated.send(303);` : `__servidorIntegrated.sendHeader("Location", "/"); __servidorIntegrated.send(303);`;
          cppSetup.push(`  __servidorIntegrated.on("${ruta}", []() { ${actCod} ${respCod} });`);
          continue;
        }

        const mResp = linea.match(/servidor\s+al\s+recibir\s+["“]([^"”]+)["”]\s+responder\s+["“]([^"”]+)["”]/i);
        if (mResp) {
          cppSetup.push(`  __servidorIntegrated.on("${mResp[1]}", []() { __servidorIntegrated.send(200, "text/plain", "${textoCpp(mResp[2])}"); });`);
          continue;
        }
      }

      if (lLow.startsWith("servidor html") || lLow.startsWith("contenido html")) {
        usaServidor = true;
        if (!includes.includes("#include <WebServer.h>")) includes.push("#include <WebServer.h>");
        if (!extrasGlobales.includes("WebServer __servidorIntegrated(80);")) extrasGlobales.push("WebServer __servidorIntegrated(80);");

        const mBlk = linea.match(/(?:servidor|contenido)\s+html\s+["“]([^"”]+)["”]\s*:\s*$/i);
        if (mBlk) {
          bloqueHtmlRuta = mBlk[1];
          bloqueHtmlLineas = [];
          continue;
        }
        const mHtml = linea.match(/(?:servidor|contenido)\s+html\s+["“]([^"”]+)["”]\s+["“]([^"”]*)["”]/i);
        if (mHtml) {
          rutasServidor.push([mHtml[1], textoCpp(mHtml[2])]);
          continue;
        }
      }

      if (lLowSin === "servidor atender") {
        usaServidor = true;
        agregar("__servidorIntegrated.handleClient();");
        continue;
      }
    }

    // Declaración de variable
    const mVar = linea.match(/(?:variable\s+)?(entero|decimal|texto|verdadero\s+o\s+falso|booleano)\s+(?:=\s*([a-zA-Z0-9_]+)|([a-zA-Z0-9_]+)(?:\s*=\s*(.+))?)/i);
    if (mVar) {
      const tip = mVar[1].toLowerCase();
      const nVar = mVar[2] || mVar[3];
      const val = mVar[4];
      let tCpp = "int", defVal = "0";
      if (tip === "decimal") { tCpp = "float"; defVal = "0.0"; }
      else if (tip === "texto") { tCpp = "String"; defVal = '""'; }
      else if (tip.includes("falso") || tip === "booleano") { tCpp = "bool"; defVal = "false"; }

      asegurarVariable(nVar, tCpp, val !== undefined ? val.trim() : defVal);
      continue;
    }

    // Configurar pin
    const mPin = lLow.match(/(?:configurar\s+pin|pin)\s+([a-zA-Z0-9_]+)\s*(?:,|\s+como|\s+para|\s+)?\s*(salida|entrada\s+con\s+resistencia|entrada\s+pullup|entrada)/);
    if (mPin) {
      const p = mPin[1].toUpperCase().startsWith("A") ? mPin[1].toUpperCase() : mPin[1];
      const modo = mPin[2] === "salida" ? "OUTPUT" : mPin[2].includes("resistencia") || mPin[2].includes("pullup") ? "INPUT_PULLUP" : "INPUT";
      if (seccionActual === "loop") {
        if (modo === "OUTPUT") agregar(`digitalWrite(${p}, LOW);`);
        agregar(`pinMode(${p}, ${modo});`);
      } else {
        if (modo === "OUTPUT") cppSetup.push(`  digitalWrite(${p}, LOW);`);
        cppSetup.push(`  pinMode(${p}, ${modo});`);
      }
      continue;
    }

    // Acciones de pin
    const mDig = lLow.match(/(?:hacer\s+que\s+pin|digital|poner\s+pin)\s+([a-zA-Z0-9_]+)\s*(?:,|\s+en|\s+=\s*|\s+)?\s*(encendido|apagado|alto|bajo|high|low|1|0)/);
    if (mDig) {
      const p = mDig[1];
      const st = ["encendido", "alto", "high", "1"].includes(mDig[2]) ? "HIGH" : "LOW";
      agregar(`digitalWrite(${p}, ${st});`);
      continue;
    }

    const mEnc = lLow.match(/(?:encender|activar)\s+pin\s+([a-zA-Z0-9_]+)/);
    if (mEnc) {
      agregar(`digitalWrite(${mEnc[1]}, HIGH);`);
      continue;
    }

    const mApa = lLow.match(/(?:apagar|desactivar)\s+pin\s+([a-zA-Z0-9_]+)/);
    if (mApa) {
      agregar(`digitalWrite(${mApa[1]}, LOW);`);
      continue;
    }

    const mAlt = lLow.match(/(?:alternar|cambiar\s+estado|toggle)\s+pin\s+([a-zA-Z0-9_]+)/);
    if (mAlt) {
      agregar(`digitalWrite(${mAlt[1]}, !digitalRead(${mAlt[1]}));`);
      continue;
    }

    // Serial Escribe
    if (lLow.startsWith("escribe ")) {
      const msg = linea.trim().slice(8).trim();
      if (msg.includes(",")) {
        const partes = msg.split(",", 2);
        const tf = partes[0].trim().replace(/^"|"$/g, "");
        const vv = partes[1].trim();
        if (tf) agregar(`Serial.print(${strLit(tf + " ")});`);
        if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(vv)) asegurarVariable(vv, "int", "0");
        agregar(`Serial.println(${vv});`);
      } else if (variablesTipos[msg] || variablesTipos[msg.toLowerCase()]) {
        agregar(`Serial.println(${msg});`);
      } else if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(msg)) {
        asegurarVariable(msg, "int", "0");
        agregar(`Serial.println(${msg});`);
      } else {
        agregar(`Serial.println(${strLit(msg.replace(/^"|"$/g, ""))});`);
      }
      continue;
    }

    // Lecturas
    const mLa = linea.match(/(?:leer\s+pin\s+anal[oó]gico|leer\s+pin\s+analogico)\s+([a-zA-Z0-9_]+)\s*(?:en|para)?\s*([a-zA-Z0-9_]+)?/i);
    if (mLa) {
      const p = mLa[1].toUpperCase().startsWith("A") ? mLa[1].toUpperCase() : mLa[1];
      const dest = mLa[2];
      if (dest) {
        asegurarVariable(dest, "int", "0");
        agregar(`${dest} = analogRead(${p});`);
      } else {
        agregar(`analogRead(${p});`);
      }
      continue;
    }

    const mLd = linea.match(/leer\s+pin\s+digital\s+([a-zA-Z0-9_]+)\s+(?:en|para)\s+([a-zA-Z0-9_]+)/i);
    if (mLd) {
      const dest = mLd[2];
      asegurarVariable(dest, "int", "0");
      agregar(`${dest} = digitalRead(${mLd[1]});`);
      continue;
    }

    // Temporización
    const mEsp = lLow.match(/esperar\s+(\d+)\s*(?:segundos|segundo|s|ms|milisegundos)?\b/);
    if (mEsp) {
      let ms = parseInt(mEsp[1], 10);
      if (lLow.includes("segund") || lLow.endsWith("s")) ms *= 1000;
      agregar(`delay(${ms});`);
      continue;
    }

    // Condicionales
    if (lLow.startsWith("si no") || lLow.startsWith("sino")) {
      if (pilaBloques.length > 0) {
        pilaBloques.pop();
        const ind = indent(nivelActual());
        const target = seccionActual === "funcion" && funcionActual
          ? funcionActual
          : seccionActual === "loop" ? cppLoop : cppSetup;
        target.push(`${ind}} else {`);
        pilaBloques.push("sino");
      } else {
        agregar("else {");
        pilaBloques.push("sino");
      }
      continue;
    }

    if (lLow.startsWith("si ")) {
      const cond = reemplazarOperadores(lSinDosPuntos.slice(3).trim());
      agregar(`if (${cond}) {`);
      pilaBloques.push("si");
      continue;
    }

    // Bucles
    const mRep = lLow.match(/repetir\s+(\d+)\s+veces/);
    if (mRep) {
      const v = `__i_${pilaBloques.length}`;
      agregar(`for (int ${v} = 0; ${v} < ${mRep[1]}; ${v}++) {`);
      pilaBloques.push("repetir");
      continue;
    }

    if (lLow.startsWith("mientras ")) {
      const cond = reemplazarOperadores(lSinDosPuntos.slice(8).trim());
      agregar(`while (${cond}) {`);
      pilaBloques.push("mientras");
      continue;
    }

    // Asignación directa
    const mAsig = linea.match(/(?:asignar\s+)?([a-zA-Z0-9_]+)\s*=\s*(.+)/i);
    if (mAsig && !lLow.startsWith("variable ")) {
      const vName = mAsig[1];
      const expr = reemplazarOperadores(mAsig[2].trim());
      asegurarVariable(vName, "int", "0");
      agregar(`${vName} = ${expr};`);
      continue;
    }

    const mSumar = l.match(/(?:sumar|agregar)\s+(.+)\s+a\s+([a-zA-Z_][a-zA-Z0-9_]*)/i);
    if (mSumar) {
      const cantidad = reemplazarOperadores(mSumar[1]);
      const destino = mSumar[2];
      asegurarVariable(destino, "int", "0");
      agregar(`${destino} += ${cantidad};`);
      continue;
    }

    const mRestar = l.match(/restar\s+(.+)\s+a\s+([a-zA-Z_][a-zA-Z0-9_]*)/i);
    if (mRestar) {
      const cantidad = reemplazarOperadores(mRestar[1]);
      const destino = mRestar[2];
      asegurarVariable(destino, "int", "0");
      agregar(`${destino} -= ${cantidad};`);
      continue;
    }

    const mMultiplicar = l.match(/multiplicar\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+por\s+(.+)/i);
    if (mMultiplicar) {
      agregar(`${mMultiplicar[1]} *= ${reemplazarOperadores(mMultiplicar[2])};`);
      continue;
    }

    const mDividir = l.match(/dividir\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:por|entre)\s+(.+)/i);
    if (mDividir) {
      agregar(`${mDividir[1]} /= ${reemplazarOperadores(mDividir[2])};`);
      continue;
    }

    const mIncrementar = l.match(/incrementar\s+([a-zA-Z_][a-zA-Z0-9_]*)/i);
    if (mIncrementar) {
      asegurarVariable(mIncrementar[1], "int", "0");
      agregar(`${mIncrementar[1]}++;`);
      continue;
    }

    const mDecrementar = l.match(/decrementar\s+([a-zA-Z_][a-zA-Z0-9_]*)/i);
    if (mDecrementar) {
      asegurarVariable(mDecrementar[1], "int", "0");
      agregar(`${mDecrementar[1]}--;`);
      continue;
    }

    // Mapear
    const mMap = lLow.match(/mapear\s+([a-zA-Z0-9_]+)\s+de\s+([a-zA-Z0-9_]+)\s+a\s+([a-zA-Z0-9_]+)\s+hacia\s+([a-zA-Z0-9_]+)\s+a\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)/);
    if (mMap) {
      asegurarVariable(mMap[6], "int", "0");
      agregar(`${mMap[6]} = map(${mMap[1]}, ${mMap[2]}, ${mMap[3]}, ${mMap[4]}, ${mMap[5]});`);
      continue;
    }

    const mLimitar = l.match(/limitar\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+entre\s+([a-zA-Z_][a-zA-Z0-9_]*|-?\d+)\s+y\s+([a-zA-Z_][a-zA-Z0-9_]*|-?\d+)/i);
    if (mLimitar) {
      agregar(`${mLimitar[1]} = constrain(${mLimitar[1]}, ${mLimitar[2]}, ${mLimitar[3]});`);
      continue;
    }

    const mAleatorio = l.match(/aleatorio\s+entre\s+([a-zA-Z_][a-zA-Z0-9_]*|-?\d+)\s+y\s+([a-zA-Z_][a-zA-Z0-9_]*|-?\d+)\s+en\s+([a-zA-Z_][a-zA-Z0-9_]*)/i);
    if (mAleatorio) {
      asegurarVariable(mAleatorio[3], "int", "0");
      agregar(`${mAleatorio[3]} = random(${mAleatorio[1]}, ${mAleatorio[2]} + 1);`);
      continue;
    }

    // PWM
    const mPwm = lLow.match(/(?:escribir\s+pwm|pwm)\s*(?:pin\s*)?([a-zA-Z0-9_]+)\s*(?:con|a|=)\s*([a-zA-Z0-9_]+)/);
    if (mPwm) {
      agregar(`analogWrite(${mPwm[1]}, ${mPwm[2]});`);
      continue;
    }

    errores.push(`Línea ${num}: no se reconoció → ${l}`);
  }

  cerrarTodosLosBloques();

  if (baudPersonalizado !== null) {
    cppSetup[1] = `  Serial.begin(${baudPersonalizado});`;
  }

  if (usaServidor) {
    for (const [ruta, cont] of rutasServidor) {
      cppSetup.push(`  __servidorIntegrated.on("${ruta}", []() { __servidorIntegrated.send(200, "text/html", "${cont}"); });`);
    }
    cppSetup.push(`  __servidorIntegrated.begin(80);`);
  }

  cppSetup.push("}");
  cppLoop.push("}");
  if (usaServidor && !cppLoop.some(linea => linea.includes("handleClient"))) {
    cppLoop.splice(1, 0, "  __servidorIntegrated.handleClient();");
  }

  const partes = [...includes, "", ...extrasGlobales, ...variablesGlobales, ""];
  cppFunciones.forEach(funcion => partes.push(...funcion, ""));
  partes.push(...cppSetup, "", ...cppLoop);
  if (errores.length > 0) {
    partes.unshift(errores.map(e => `// AVISO: ${e}`).join("\n"), "");
  }

  return partes.join("\n");
}
